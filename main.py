from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aigc_trace.evaluation import optimize_lineage_threshold, parse_ground_truth
from aigc_trace.metadata import load_image_metadata
from aigc_trace.storage import ensure_dir, load_json, save_csv, save_json
from aigc_trace.version_tracker import VersionTracker
from aigc_trace.visualization import draw_version_graph


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AIGC 新闻图片区块链可信溯源与内容演化治理原型系统"
    )
    parser.add_argument("--input_dir", default="data/news_images", help="待检测图片目录")
    parser.add_argument("--output_dir", default="results", help="结果输出目录")
    parser.add_argument("--config", default="config.json", help="配置文件路径")
    parser.add_argument(
        "--metadata",
        default="data/image_metadata.json",
        help="AIGC 来源与编辑元数据文件；文件不存在时仍可运行",
    )
    parser.add_argument(
        "--ground_truth",
        default="data/ground_truth.json",
        help="阈值自动寻优使用的真实标签文件",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="手动指定同源阈值；指定后优先于自动寻优和 config.json",
    )
    auto_group = parser.add_mutually_exclusive_group()
    auto_group.add_argument(
        "--auto-threshold",
        action="store_true",
        help="根据 ground_truth.json 自动搜索最佳融合阈值",
    )
    auto_group.add_argument(
        "--no-auto-threshold",
        action="store_true",
        help="关闭自动寻优，直接使用 config.json 中的阈值",
    )
    parser.add_argument("--uploader", default="news_editor_001", help="上传者或来源标识")
    return parser.parse_args()


def resolve_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else PROJECT_ROOT / path


def build_tracker(
    threshold: float,
    config: Dict[str, Any],
    uploader: str,
    metadata_by_file: Dict[str, Dict[str, Any]],
) -> VersionTracker:
    return VersionTracker(
        threshold=threshold,
        weights=config.get("weights"),
        uploader=uploader,
        metadata_by_file=metadata_by_file,
    )


def main() -> None:
    args = parse_args()
    config_path = resolve_path(args.config)
    config = load_json(config_path)

    input_dir = resolve_path(args.input_dir)
    output_dir = resolve_path(args.output_dir)
    metadata_path = resolve_path(args.metadata)
    ground_truth_path = resolve_path(args.ground_truth)
    ensure_dir(output_dir)

    configured_threshold = float(config.get("similarity_threshold", 0.70))
    metadata_by_file = load_image_metadata(metadata_path)

    auto_config = config.get("auto_threshold", {})
    auto_enabled_by_config = bool(auto_config.get("enabled", True))
    if args.threshold is not None:
        auto_enabled = False
        threshold = float(args.threshold)
        threshold_source = "命令行手动指定"
    else:
        if args.auto_threshold:
            auto_enabled = True
        elif args.no_auto_threshold:
            auto_enabled = False
        else:
            auto_enabled = auto_enabled_by_config
        threshold = configured_threshold
        threshold_source = "config.json 默认阈值"

    threshold_optimization = None
    if auto_enabled:
        if not ground_truth_path.exists():
            print(f"提示：未找到真实标签文件 {ground_truth_path}，自动寻优已跳过。")
        else:
            # 先进行一次预运行，提取每张图片相对历史版本的最高融合相似度。
            preliminary_tracker = build_tracker(
                threshold=configured_threshold,
                config=config,
                uploader=args.uploader,
                metadata_by_file=metadata_by_file,
            )
            preliminary_result = preliminary_tracker.process_directory(
                input_dir,
                supported_ext=config["supported_ext"],
            )
            ground_truth = parse_ground_truth(load_json(ground_truth_path))
            threshold_optimization = optimize_lineage_threshold(
                preliminary_result["records"],
                ground_truth,
                start=float(auto_config.get("start", 0.30)),
                end=float(auto_config.get("end", 0.90)),
                step=float(auto_config.get("step", 0.01)),
            )
            threshold = float(threshold_optimization["threshold"])
            threshold_source = "ground_truth 自动寻优"

            curve = threshold_optimization.pop("curve", [])
            save_json(
                {
                    **threshold_optimization,
                    "ground_truth_file": str(ground_truth_path),
                    "configured_threshold": configured_threshold,
                    "note": "课程实验中使用当前标注集自动选阈值；正式研究建议另设独立验证集。",
                },
                output_dir / "threshold_optimization.json",
            )
            save_csv(curve, output_dir / "threshold_optimization_curve.csv")

    tracker = build_tracker(
        threshold=threshold,
        config=config,
        uploader=args.uploader,
        metadata_by_file=metadata_by_file,
    )
    result = tracker.process_directory(input_dir, supported_ext=config["supported_ext"])
    version_graph = tracker.build_version_graph()

    save_json(result["records"], output_dir / "trace_records.json")
    save_json(result["blockchain"], output_dir / "blockchain_records.json")
    save_json(version_graph, output_dir / "version_graph.json")
    save_csv(result["records"], output_dir / "experiment_result.csv")
    save_csv(result["similarity_matrix"], output_dir / "similarity_matrix.csv")
    draw_version_graph(version_graph, output_dir / "version_graph.png")

    generated_files = [
        "trace_records.json",
        "blockchain_records.json",
        "version_graph.json",
        "version_graph.png",
        "experiment_result.csv",
        "similarity_matrix.csv",
        "summary.json",
    ]
    if threshold_optimization is not None:
        generated_files.extend(
            ["threshold_optimization.json", "threshold_optimization_curve.csv"]
        )

    summary = {
        "project_name": config.get("project_name"),
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "metadata_file": str(metadata_path),
        "ground_truth_file": str(ground_truth_path),
        "configured_threshold": configured_threshold,
        "selected_threshold": threshold,
        "threshold_source": threshold_source,
        "auto_threshold_enabled": auto_enabled,
        "weights": tracker.similarity.weights,
        "image_count": len(result["records"]),
        "metadata_match_count": int(result["metadata_match_count"]),
        "block_count": len(result["blockchain"]),
        "chain_valid": result["chain_valid"],
        "generated_files": generated_files,
    }
    save_json(summary, output_dir / "summary.json")

    print("\n====== AIGC 新闻图片区块链可信溯源系统运行完成 ======")
    print(f"输入目录：{input_dir}")
    print(f"输出目录：{output_dir}")
    print(f"同源阈值：{threshold:.3f}（{threshold_source}）")
    if threshold_optimization is not None:
        interval = threshold_optimization.get("best_threshold_interval", [])
        print(
            f"自动寻优：F1={threshold_optimization['f1']:.3f}，"
            f"Accuracy={threshold_optimization['accuracy']:.3f}，"
            f"最佳区间={interval}"
        )
    print(f"处理图片数：{summary['image_count']}")
    print(f"元数据匹配：{summary['metadata_match_count']}/{summary['image_count']}")
    print(f"区块数：{summary['block_count']}")
    print(f"区块链校验：{'通过' if summary['chain_valid'] else '失败'}")

    print("\n版本识别结果：")
    for record in result["records"]:
        parent = record["parent_id"] if record["parent_id"] else "None"
        print(
            f"{record['version_id']} | {record['file_name']} | parent={parent} "
            f"| fusion={record['best_similarity']:.3f} "
            f"| ORB={record['orb_similarity']:.3f} | {record['governance_label']}"
        )


if __name__ == "__main__":
    main()

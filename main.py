from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 允许直接运行：python main.py
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

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
    parser.add_argument("--threshold", type=float, default=None, help="同源版本识别阈值，默认读取 config.json")
    parser.add_argument("--uploader", default="news_editor_001", help="上传者或来源标识")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_path = PROJECT_ROOT / args.config if not Path(args.config).is_absolute() else Path(args.config)
    config = load_json(config_path)

    threshold = args.threshold if args.threshold is not None else float(config["similarity_threshold"])
    input_dir = PROJECT_ROOT / args.input_dir if not Path(args.input_dir).is_absolute() else Path(args.input_dir)
    output_dir = PROJECT_ROOT / args.output_dir if not Path(args.output_dir).is_absolute() else Path(args.output_dir)
    ensure_dir(output_dir)

    tracker = VersionTracker(
        threshold=threshold,
        weights=config.get("weights"),
        uploader=args.uploader,
    )
    result = tracker.process_directory(input_dir, supported_ext=config["supported_ext"])
    version_graph = tracker.build_version_graph()

    save_json(result["records"], output_dir / "trace_records.json")
    save_json(result["blockchain"], output_dir / "blockchain_records.json")
    save_json(version_graph, output_dir / "version_graph.json")
    save_csv(result["records"], output_dir / "experiment_result.csv")
    save_csv(result["similarity_matrix"], output_dir / "similarity_matrix.csv")
    draw_version_graph(version_graph, output_dir / "version_graph.png")

    summary = {
        "project_name": config.get("project_name"),
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "threshold": threshold,
        "image_count": len(result["records"]),
        "block_count": len(result["blockchain"]),
        "chain_valid": result["chain_valid"],
        "generated_files": [
            "trace_records.json",
            "blockchain_records.json",
            "version_graph.json",
            "version_graph.png",
            "experiment_result.csv",
            "similarity_matrix.csv",
            "summary.json",
        ],
    }
    save_json(summary, output_dir / "summary.json")

    print("\n====== AIGC 新闻图片区块链可信溯源系统运行完成 ======")
    print(f"输入目录：{input_dir}")
    print(f"输出目录：{output_dir}")
    print(f"同源阈值：{threshold}")
    print(f"处理图片数：{summary['image_count']}")
    print(f"区块数：{summary['block_count']}")
    print(f"区块链校验：{'通过' if summary['chain_valid'] else '失败'}")
    print("\n版本识别结果：")
    for record in result["records"]:
        parent = record["parent_id"] if record["parent_id"] else "None"
        print(
            f"{record['version_id']} | {record['file_name']} | parent={parent} "
            f"| similarity={record['best_similarity']:.3f} | {record['governance_label']}"
        )
    print("\n结果文件已生成")


if __name__ == "__main__":
    main()

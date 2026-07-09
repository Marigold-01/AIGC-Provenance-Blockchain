from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aigc_trace.evaluation import (
    compare_similarity_methods,
    evaluate_lineage,
    optimize_lineage_threshold,
    optimize_similarity_thresholds,
    parse_ground_truth,
)
from aigc_trace.storage import ensure_dir, load_json, save_csv, save_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="计算同源识别、父版本识别和方法对比指标")
    parser.add_argument("--results_dir", default="results", help="主程序结果目录")
    parser.add_argument("--ground_truth", default="data/ground_truth.json", help="真实标签文件")
    parser.add_argument("--config", default="config.json", help="配置文件")
    return parser.parse_args()


def resolve_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else PROJECT_ROOT / path


def main() -> None:
    args = parse_args()
    results_dir = resolve_path(args.results_dir)
    ground_truth_path = resolve_path(args.ground_truth)
    config_path = resolve_path(args.config)
    ensure_dir(results_dir)

    records_path = results_dir / "trace_records.json"
    matrix_path = results_dir / "similarity_matrix.csv"
    if not records_path.exists() or not matrix_path.exists():
        raise FileNotFoundError(
            "请先运行 python main.py 生成 trace_records.json 和 similarity_matrix.csv。"
        )
    if not ground_truth_path.exists():
        raise FileNotFoundError(f"真实标签文件不存在：{ground_truth_path}")

    records = load_json(records_path)
    ground_truth = parse_ground_truth(load_json(ground_truth_path))
    config = load_json(config_path)
    similarity_rows = pd.read_csv(matrix_path).to_dict(orient="records")

    auto_config = config.get("auto_threshold", {})
    search_start = float(auto_config.get("start", 0.30))
    search_end = float(auto_config.get("end", 0.90))
    search_step = float(auto_config.get("step", 0.01))

    lineage_result = evaluate_lineage(records, ground_truth)
    current_method_comparison = compare_similarity_methods(
        similarity_rows,
        ground_truth,
        config.get("evaluation_thresholds", {}),
    )
    optimized_methods = optimize_similarity_thresholds(
        similarity_rows,
        ground_truth,
        start=search_start,
        end=search_end,
        step=search_step,
    )
    optimized_lineage = optimize_lineage_threshold(
        records,
        ground_truth,
        start=search_start,
        end=search_end,
        step=search_step,
    )
    optimized_lineage_curve = optimized_lineage.pop("curve", [])

    report = {
        "lineage_evaluation": lineage_result["metrics"],
        "optimized_lineage_threshold": optimized_lineage,
        "current_threshold_method_comparison": current_method_comparison,
        "optimized_method_thresholds": optimized_methods,
        "ground_truth_file": str(ground_truth_path),
        "note": "自动寻优用于当前课程实验。正式研究建议在独立验证集上选择阈值，再在测试集上报告最终指标。",
    }
    save_json(report, results_dir / "evaluation_report.json")
    save_csv(lineage_result["details"], results_dir / "evaluation_details.csv")
    save_csv(current_method_comparison, results_dir / "method_comparison.csv")
    save_csv(optimized_methods, results_dir / "optimized_method_thresholds.csv")
    save_csv(optimized_lineage_curve, results_dir / "optimized_lineage_threshold_curve.csv")

    metrics = lineage_result["metrics"]
    print("\n====== 实验评价结果 ======")
    print(f"有效样本数：{metrics['sample_count']}")
    print(f"Accuracy：{metrics['accuracy']:.3f}")
    print(f"Precision：{metrics['precision']:.3f}")
    print(f"Recall：{metrics['recall']:.3f}")
    print(f"F1：{metrics['f1']:.3f}")
    print(f"父版本准确率：{metrics['exact_parent_accuracy']:.3f}")
    if metrics["missing_result_files"]:
        print("未在运行结果中找到的标注图片：" + ", ".join(metrics["missing_result_files"]))

    print("\n当前配置阈值下的方法对比：")
    for row in current_method_comparison:
        print(
            f"{row['method']} | threshold={row['threshold']:.2f} "
            f"| Accuracy={row['accuracy']:.3f} | F1={row['f1']:.3f}"
        )

    print("\n自动寻优结果：")
    print(
        f"推荐主阈值：{optimized_lineage['threshold']:.2f} "
        f"| Accuracy={optimized_lineage['accuracy']:.3f} "
        f"| F1={optimized_lineage['f1']:.3f} "
        f"| 最佳区间={optimized_lineage.get('best_threshold_interval')}"
    )
    for row in optimized_methods:
        print(
            f"{row['method']} 最优阈值={row['threshold']:.2f} "
            f"| Accuracy={row['accuracy']:.3f} | F1={row['f1']:.3f}"
        )


if __name__ == "__main__":
    main()

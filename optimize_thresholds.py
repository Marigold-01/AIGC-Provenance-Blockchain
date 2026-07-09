from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aigc_trace.evaluation import optimize_lineage_threshold, parse_ground_truth
from aigc_trace.storage import load_json, save_csv, save_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="根据当前实验结果自动搜索最佳同源阈值")
    parser.add_argument("--results_dir", default="results", help="主程序结果目录")
    parser.add_argument("--ground_truth", default="data/ground_truth.json", help="真实标签文件")
    parser.add_argument("--config", default="config.json", help="配置文件")
    parser.add_argument("--apply", action="store_true", help="把推荐阈值写回 config.json")
    return parser.parse_args()


def resolve_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else PROJECT_ROOT / path


def main() -> None:
    args = parse_args()
    results_dir = resolve_path(args.results_dir)
    records_path = results_dir / "trace_records.json"
    ground_truth_path = resolve_path(args.ground_truth)
    config_path = resolve_path(args.config)

    if not records_path.exists():
        raise FileNotFoundError("请先运行 python main.py 生成 results/trace_records.json。")
    if not ground_truth_path.exists():
        raise FileNotFoundError(f"真实标签文件不存在：{ground_truth_path}")

    records = load_json(records_path)
    ground_truth = parse_ground_truth(load_json(ground_truth_path))
    config = load_json(config_path)
    auto_config = config.get("auto_threshold", {})

    optimized = optimize_lineage_threshold(
        records,
        ground_truth,
        start=float(auto_config.get("start", 0.30)),
        end=float(auto_config.get("end", 0.90)),
        step=float(auto_config.get("step", 0.01)),
    )
    curve = optimized.pop("curve", [])
    save_json(optimized, results_dir / "threshold_optimization_manual.json")
    save_csv(curve, results_dir / "threshold_optimization_manual_curve.csv")

    if args.apply:
        config["similarity_threshold"] = float(optimized["threshold"])
        save_json(config, config_path)

    print("\n====== 阈值自动寻优 ======")
    print(f"推荐阈值：{optimized['threshold']:.3f}")
    print(f"最佳阈值区间：{optimized.get('best_threshold_interval')}")
    print(f"Accuracy：{optimized['accuracy']:.3f}")
    print(f"F1：{optimized['f1']:.3f}")
    print(f"正样本最低分：{optimized.get('positive_min_score')}")
    print(f"负样本最高分：{optimized.get('negative_max_score')}")
    if args.apply:
        print(f"已写回配置文件：{config_path}")
        print("请重新运行 python main.py --no-auto-threshold，使新阈值应用于父版本识别。")


if __name__ == "__main__":
    main()

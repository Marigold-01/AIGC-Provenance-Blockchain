from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


METHOD_COLUMNS = {
    "SHA256": "sha256_score",
    "pHash": "phash_score",
    "dHash": "dhash_score",
    "颜色直方图": "histogram_score",
    "ORB局部特征": "orb_score",
    "多特征融合": "fusion_score",
}


def safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def binary_metrics(y_true: Sequence[bool], y_pred: Sequence[bool]) -> Dict[str, Any]:
    if len(y_true) != len(y_pred):
        raise ValueError("真实标签与预测标签长度不一致。")

    tp = sum(bool(t) and bool(p) for t, p in zip(y_true, y_pred))
    tn = sum((not bool(t)) and (not bool(p)) for t, p in zip(y_true, y_pred))
    fp = sum((not bool(t)) and bool(p) for t, p in zip(y_true, y_pred))
    fn = sum(bool(t) and (not bool(p)) for t, p in zip(y_true, y_pred))
    total = len(y_true)

    accuracy = safe_div(tp + tn, total)
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    specificity = safe_div(tn, tn + fp)
    balanced_accuracy = (recall + specificity) / 2 if total else 0.0
    f1 = safe_div(2 * precision * recall, precision + recall)

    return {
        "sample_count": total,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "accuracy": round(accuracy, 6),
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "specificity": round(specificity, 6),
        "balanced_accuracy": round(balanced_accuracy, 6),
        "f1": round(f1, 6),
    }


def parse_ground_truth(raw: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    samples = raw.get("samples", raw)
    if not isinstance(samples, dict):
        raise ValueError("ground_truth.json 必须包含 samples 对象。")
    return {
        str(file_name): dict(item)
        for file_name, item in samples.items()
        if isinstance(item, dict)
    }


def evaluate_lineage(
    records: Iterable[Mapping[str, Any]],
    ground_truth: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    records_by_file = {str(row.get("file_name")): row for row in records}
    y_true: List[bool] = []
    y_pred: List[bool] = []
    details: List[Dict[str, Any]] = []
    exact_parent_correct = 0
    exact_parent_total = 0
    missing_result_files: List[str] = []

    for file_name, label in ground_truth.items():
        record = records_by_file.get(file_name)
        if record is None:
            missing_result_files.append(file_name)
            continue

        expected_parent = label.get("expected_parent_file")
        expected_same = label.get("expected_same_source")
        if not isinstance(expected_same, bool):
            expected_same = expected_parent is not None

        predicted_parent = record.get("parent_file")
        predicted_same = predicted_parent is not None and str(predicted_parent).strip() != ""

        y_true.append(bool(expected_same))
        y_pred.append(bool(predicted_same))

        parent_correct = predicted_parent == expected_parent
        exact_parent_total += 1
        exact_parent_correct += int(parent_correct)

        details.append(
            {
                "file_name": file_name,
                "expected_same_source": bool(expected_same),
                "predicted_same_source": bool(predicted_same),
                "expected_parent_file": expected_parent,
                "predicted_parent_file": predicted_parent,
                "parent_correct": parent_correct,
                "best_similarity": record.get("best_similarity", 0.0),
                "phash_similarity": record.get("phash_similarity", 0.0),
                "dhash_similarity": record.get("dhash_similarity", 0.0),
                "histogram_similarity": record.get("histogram_similarity", 0.0),
                "orb_similarity": record.get("orb_similarity", 0.0),
                "governance_label": record.get("governance_label", ""),
            }
        )

    metrics = binary_metrics(y_true, y_pred)
    metrics["exact_parent_accuracy"] = round(
        safe_div(exact_parent_correct, exact_parent_total), 6
    )
    metrics["exact_parent_correct"] = exact_parent_correct
    metrics["exact_parent_total"] = exact_parent_total
    metrics["missing_result_files"] = missing_result_files

    return {"metrics": metrics, "details": details}


def threshold_grid(start: float, end: float, step: float) -> List[float]:
    if step <= 0:
        raise ValueError("阈值步长必须大于 0。")
    if end < start:
        raise ValueError("阈值搜索上限不能小于下限。")

    values: List[float] = []
    current = start
    while current <= end + 1e-12:
        values.append(round(current, 6))
        current += step
    return values


def optimize_threshold_from_scores(
    y_true: Sequence[bool],
    scores: Sequence[float],
    start: float = 0.30,
    end: float = 0.90,
    step: float = 0.01,
) -> Dict[str, Any]:
    """根据 F1、平衡准确率和 Accuracy 自动选择阈值。

    若多个阈值达到相同最佳指标，则选择最佳区间的中点，避免选择贴近正负样本
    边界的极端阈值。该功能用于课程实验；正式研究应在独立验证集上选阈值。
    """
    if len(y_true) != len(scores):
        raise ValueError("真实标签与相似度数量不一致。")
    if not y_true:
        return {
            "threshold": 0.70,
            "selection_rule": "无有效样本，使用默认阈值",
            "curve": [],
            **binary_metrics([], []),
        }

    curve: List[Dict[str, Any]] = []
    for threshold in threshold_grid(start, end, step):
        predictions = [float(score) >= threshold for score in scores]
        metrics = binary_metrics(y_true, predictions)
        curve.append({"threshold": threshold, **metrics})

    best_key = max(
        (row["f1"], row["balanced_accuracy"], row["accuracy"])
        for row in curve
    )
    best_rows = [
        row
        for row in curve
        if (row["f1"], row["balanced_accuracy"], row["accuracy"]) == best_key
    ]
    low = min(float(row["threshold"]) for row in best_rows)
    high = max(float(row["threshold"]) for row in best_rows)
    midpoint = (low + high) / 2
    selected = min(best_rows, key=lambda row: abs(float(row["threshold"]) - midpoint))

    positive_scores = [float(score) for truth, score in zip(y_true, scores) if truth]
    negative_scores = [float(score) for truth, score in zip(y_true, scores) if not truth]
    positive_min = min(positive_scores) if positive_scores else None
    negative_max = max(negative_scores) if negative_scores else None
    separation_margin = (
        positive_min - negative_max
        if positive_min is not None and negative_max is not None
        else None
    )

    return {
        **selected,
        "best_threshold_interval": [round(low, 6), round(high, 6)],
        "positive_min_score": None if positive_min is None else round(positive_min, 6),
        "negative_max_score": None if negative_max is None else round(negative_max, 6),
        "separation_margin": None if separation_margin is None else round(separation_margin, 6),
        "selection_rule": "最大F1 → 最大平衡准确率 → 最大Accuracy；并取并列最佳阈值区间中点",
        "curve": curve,
    }


def optimize_lineage_threshold(
    records: Iterable[Mapping[str, Any]],
    ground_truth: Mapping[str, Mapping[str, Any]],
    start: float = 0.30,
    end: float = 0.90,
    step: float = 0.01,
) -> Dict[str, Any]:
    records_by_file = {str(row.get("file_name")): row for row in records}
    y_true: List[bool] = []
    scores: List[float] = []
    missing_result_files: List[str] = []

    for file_name, label in ground_truth.items():
        record = records_by_file.get(file_name)
        if record is None:
            missing_result_files.append(file_name)
            continue
        expected_same = label.get("expected_same_source")
        if not isinstance(expected_same, bool):
            expected_same = label.get("expected_parent_file") is not None
        y_true.append(bool(expected_same))
        scores.append(float(record.get("best_similarity", 0.0)))

    result = optimize_threshold_from_scores(y_true, scores, start, end, step)
    result["missing_result_files"] = missing_result_files
    return result


def _collect_similarity_pairs(
    similarity_rows: Iterable[Mapping[str, Any]],
    ground_truth: Mapping[str, Mapping[str, Any]],
) -> List[Tuple[bool, Dict[str, Any]]]:
    pairs: List[Tuple[bool, Dict[str, Any]]] = []
    for row in similarity_rows:
        source_file = str(row.get("source_file", ""))
        target_file = str(row.get("target_file", ""))
        source_label = ground_truth.get(source_file)
        target_label = ground_truth.get(target_file)
        if source_label is None or target_label is None:
            continue

        source_group = source_label.get("source_group")
        target_group = target_label.get("source_group")
        if source_group is None or target_group is None:
            continue

        pairs.append((source_group == target_group, dict(row)))
    return pairs


def compare_similarity_methods(
    similarity_rows: Iterable[Mapping[str, Any]],
    ground_truth: Mapping[str, Mapping[str, Any]],
    thresholds: Mapping[str, float],
) -> List[Dict[str, Any]]:
    pairs = _collect_similarity_pairs(similarity_rows, ground_truth)
    comparison: List[Dict[str, Any]] = []

    for method_name, column in METHOD_COLUMNS.items():
        threshold = float(thresholds.get(column, 0.70))
        y_true: List[bool] = []
        y_pred: List[bool] = []
        for is_same, row in pairs:
            score = row.get(column)
            if score is None:
                continue
            y_true.append(bool(is_same))
            y_pred.append(float(score) >= threshold)

        comparison.append(
            {
                "method": method_name,
                "score_column": column,
                "threshold": threshold,
                **binary_metrics(y_true, y_pred),
            }
        )

    return comparison


def optimize_similarity_thresholds(
    similarity_rows: Iterable[Mapping[str, Any]],
    ground_truth: Mapping[str, Mapping[str, Any]],
    start: float = 0.30,
    end: float = 0.90,
    step: float = 0.01,
) -> List[Dict[str, Any]]:
    pairs = _collect_similarity_pairs(similarity_rows, ground_truth)
    results: List[Dict[str, Any]] = []

    for method_name, column in METHOD_COLUMNS.items():
        y_true: List[bool] = []
        scores: List[float] = []
        for is_same, row in pairs:
            score = row.get(column)
            if score is None:
                continue
            y_true.append(bool(is_same))
            scores.append(float(score))

        optimized = optimize_threshold_from_scores(y_true, scores, start, end, step)
        optimized.pop("curve", None)
        results.append(
            {
                "method": method_name,
                "score_column": column,
                **optimized,
            }
        )

    return results

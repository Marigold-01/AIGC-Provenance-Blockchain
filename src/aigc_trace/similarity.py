from __future__ import annotations

from typing import Dict

import numpy as np

from .models import ImageFeature, SimilarityResult


DEFAULT_WEIGHTS: Dict[str, float] = {
    "sha256": 0.20,
    "phash": 0.35,
    "dhash": 0.35,
    "histogram": 0.10,
}


def hamming_distance(hash_a: str, hash_b: str) -> int:
    if len(hash_a) != len(hash_b):
        raise ValueError("两个哈希值长度不同，无法计算汉明距离。")
    return sum(ch1 != ch2 for ch1, ch2 in zip(hash_a, hash_b))


def hash_similarity(hash_a: str, hash_b: str) -> float:
    """把汉明距离转换为 0~1 之间的相似度。"""
    if not hash_a and not hash_b:
        return 1.0
    if len(hash_a) != len(hash_b):
        return 0.0
    return max(0.0, 1.0 - hamming_distance(hash_a, hash_b) / len(hash_a))


def cosine_similarity(vec_a, vec_b) -> float:
    arr_a = np.asarray(vec_a, dtype=np.float32)
    arr_b = np.asarray(vec_b, dtype=np.float32)
    denominator = float(np.linalg.norm(arr_a) * np.linalg.norm(arr_b))
    if denominator == 0:
        return 0.0
    score = float(np.dot(arr_a, arr_b) / denominator)
    return max(0.0, min(1.0, score))


class SimilarityCalculator:
    """多特征融合相似度计算。

    论文对应：多特征融合相似度计算模块。
    """

    def __init__(self, weights: Dict[str, float] | None = None) -> None:
        self.weights = weights or DEFAULT_WEIGHTS.copy()
        self._normalize_weights()

    def compare(self, source: ImageFeature, target: ImageFeature) -> SimilarityResult:
        sha_equal = source.sha256 == target.sha256
        sha_score = 1.0 if sha_equal else 0.0
        phash_score = hash_similarity(source.phash, target.phash)
        dhash_score = hash_similarity(source.dhash, target.dhash)
        hist_score = cosine_similarity(source.histogram, target.histogram)
        fusion = (
            self.weights["sha256"] * sha_score
            + self.weights["phash"] * phash_score
            + self.weights["dhash"] * dhash_score
            + self.weights["histogram"] * hist_score
        )
        return SimilarityResult(
            source_id=source.image_id,
            target_id=target.image_id,
            sha256_equal=sha_equal,
            sha256_score=round(sha_score, 6),
            phash_score=round(phash_score, 6),
            dhash_score=round(dhash_score, 6),
            histogram_score=round(hist_score, 6),
            fusion_score=round(float(fusion), 6),
        )

    def _normalize_weights(self) -> None:
        required = {"sha256", "phash", "dhash", "histogram"}
        missing = required - set(self.weights)
        if missing:
            raise ValueError(f"权重缺少字段：{missing}")
        total = sum(float(self.weights[key]) for key in required)
        if total <= 0:
            raise ValueError("权重总和必须大于 0。")
        for key in required:
            self.weights[key] = float(self.weights[key]) / total

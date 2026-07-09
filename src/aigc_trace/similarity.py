from __future__ import annotations

from typing import Dict, Optional

import numpy as np

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None

from .models import ImageFeature, SimilarityResult


DEFAULT_WEIGHTS: Dict[str, float] = {
    "sha256": 0.05,
    "phash": 0.22,
    "dhash": 0.18,
    "histogram": 0.15,
    "orb": 0.40,
}


def hamming_distance(hash_a: str, hash_b: str) -> int:
    if len(hash_a) != len(hash_b):
        raise ValueError("两个哈希值长度不同，无法计算汉明距离。")
    return sum(ch1 != ch2 for ch1, ch2 in zip(hash_a, hash_b))


def hash_similarity(hash_a: str, hash_b: str) -> float:
    """把哈希汉明距离转换为 0~1 相似度。"""
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


def orb_similarity(
    keypoints_a: Optional[np.ndarray],
    descriptors_a: Optional[np.ndarray],
    keypoints_b: Optional[np.ndarray],
    descriptors_b: Optional[np.ndarray],
) -> float:
    """计算 ORB 局部特征相似度。

    先使用 KNN + Lowe 比率检验筛选可靠匹配，再使用 RANSAC 单应性估计检验
    匹配点的几何一致性。最终分数同时考虑可靠匹配覆盖率和几何内点比例，
    因而比单纯统计匹配数量更能区分“裁剪/局部编辑”和“完全不同图片”。
    """
    if cv2 is None:
        return 0.0
    if (
        keypoints_a is None
        or keypoints_b is None
        or descriptors_a is None
        or descriptors_b is None
        or len(descriptors_a) == 0
        or len(descriptors_b) == 0
    ):
        return 0.0

    try:
        matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        knn_matches = matcher.knnMatch(descriptors_a, descriptors_b, k=2)
        good_matches = []
        for pair in knn_matches:
            if len(pair) < 2:
                continue
            first, second = pair
            if first.distance < 0.78 * second.distance:
                good_matches.append(first)

        if not good_matches:
            return 0.0

        min_feature_count = max(1, min(len(descriptors_a), len(descriptors_b)))
        # 约 8% 的局部特征形成可靠匹配即可视为较充分覆盖，同时设置最少 12 个匹配基准。
        coverage_base = max(12.0, 0.08 * min_feature_count)
        coverage_score = min(1.0, len(good_matches) / coverage_base)

        if len(good_matches) < 4:
            # 匹配点不足以估计单应性，只保留较低的覆盖分。
            return round(min(0.30, 0.30 * coverage_score), 6)

        source_points = np.float32(
            [keypoints_a[match.queryIdx] for match in good_matches]
        ).reshape(-1, 1, 2)
        target_points = np.float32(
            [keypoints_b[match.trainIdx] for match in good_matches]
        ).reshape(-1, 1, 2)

        _homography, inlier_mask = cv2.findHomography(
            source_points,
            target_points,
            cv2.RANSAC,
            5.0,
        )
        if inlier_mask is None:
            return round(0.35 * coverage_score, 6)

        inlier_count = int(inlier_mask.ravel().sum())
        inlier_ratio = inlier_count / max(1, len(good_matches))

        # 距离越小，描述子质量越高。ORB 汉明距离理论最大值为 256。
        mean_distance = float(np.mean([match.distance for match in good_matches]))
        descriptor_quality = max(0.0, min(1.0, 1.0 - mean_distance / 256.0))

        score = (
            0.45 * coverage_score
            + 0.40 * inlier_ratio
            + 0.15 * descriptor_quality
        )
        if inlier_count < 4:
            score *= 0.55
        return round(max(0.0, min(1.0, score)), 6)
    except Exception:
        return 0.0


class SimilarityCalculator:
    """多特征融合相似度计算模块。"""

    def __init__(self, weights: Dict[str, float] | None = None) -> None:
        self.weights = weights or DEFAULT_WEIGHTS.copy()
        self._normalize_weights()

    def compare(self, source: ImageFeature, target: ImageFeature) -> SimilarityResult:
        sha_equal = source.sha256 == target.sha256
        sha_score = 1.0 if sha_equal else 0.0
        phash_score = hash_similarity(source.phash, target.phash)
        dhash_score = hash_similarity(source.dhash, target.dhash)
        hist_score = cosine_similarity(source.histogram, target.histogram)
        orb_score = orb_similarity(
            source.orb_keypoints,
            source.orb_descriptors,
            target.orb_keypoints,
            target.orb_descriptors,
        )

        fusion = (
            self.weights.get("sha256", 0.0) * sha_score
            + self.weights.get("phash", 0.0) * phash_score
            + self.weights.get("dhash", 0.0) * dhash_score
            + self.weights.get("histogram", 0.0) * hist_score
            + self.weights.get("orb", 0.0) * orb_score
        )

        return SimilarityResult(
            source_id=source.image_id,
            target_id=target.image_id,
            sha256_equal=sha_equal,
            sha256_score=round(sha_score, 6),
            phash_score=round(phash_score, 6),
            dhash_score=round(dhash_score, 6),
            histogram_score=round(hist_score, 6),
            orb_score=round(orb_score, 6),
            fusion_score=round(float(fusion), 6),
        )

    def _normalize_weights(self) -> None:
        valid_keys = ("sha256", "phash", "dhash", "histogram", "orb")
        normalized_input = {
            key: max(0.0, float(self.weights.get(key, 0.0)))
            for key in valid_keys
        }
        total = sum(normalized_input.values())
        if total <= 0:
            normalized_input = DEFAULT_WEIGHTS.copy()
            total = sum(normalized_input.values())
        self.weights = {key: value / total for key, value in normalized_input.items()}

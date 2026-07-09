from __future__ import annotations

import hashlib
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image, ImageOps

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None

from .models import ImageFeature


class FeatureExtractor:
    """负责提取图片多维特征。

    论文对应：图片特征提取模块。
    - SHA256：判断文件内容是否完全一致；
    - pHash：识别压缩、亮度变化等全局视觉近似；
    - dHash：反映图像边缘和梯度结构；
    - RGB 颜色直方图：补充整体颜色分布信息；
    - ORB 局部特征：增强裁剪、局部增加/删除、AIGC 局部编辑场景的识别能力。
    """

    def __init__(
        self,
        hash_size: int = 8,
        phash_resize: int = 32,
        hist_bins: int = 16,
        orb_nfeatures: int = 1200,
    ) -> None:
        self.hash_size = hash_size
        self.phash_resize = phash_resize
        self.hist_bins = hist_bins
        self.orb_nfeatures = orb_nfeatures
        self._dct_matrix_cache: dict[int, np.ndarray] = {}

    def extract(self, image_path: str | Path, image_id: str) -> ImageFeature:
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"图片不存在：{path}")

        with Image.open(path) as img:
            img = ImageOps.exif_transpose(img)
            width, height = img.size
            rgb_img = img.convert("RGB")
            gray_img = img.convert("L")
            orb_keypoints, orb_descriptors = self.extract_orb_features(gray_img)
            keypoint_count = 0 if orb_keypoints is None else int(len(orb_keypoints))

            return ImageFeature(
                image_id=image_id,
                file_name=path.name,
                file_path=str(path),
                sha256=self.sha256_file(path),
                phash=self.phash(gray_img),
                dhash=self.dhash(gray_img),
                histogram=self.rgb_histogram(rgb_img),
                width=width,
                height=height,
                orb_keypoint_count=keypoint_count,
                orb_keypoints=orb_keypoints,
                orb_descriptors=orb_descriptors,
            )

    @staticmethod
    def sha256_file(path: str | Path) -> str:
        digest = hashlib.sha256()
        with open(path, "rb") as file:
            for chunk in iter(lambda: file.read(8192), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def phash(self, gray_img: Image.Image) -> str:
        size = self.phash_resize
        small = gray_img.resize((size, size), Image.Resampling.LANCZOS)
        pixels = np.asarray(small, dtype=np.float32)
        dct_matrix = self._dct_matrix(size)
        dct_result = dct_matrix @ pixels @ dct_matrix.T
        low_freq = dct_result[: self.hash_size, : self.hash_size].copy()
        values = low_freq.flatten()
        # 排除 DC 分量，减弱整体亮度变化的影响。
        median = np.median(values[1:])
        bits = values > median
        return "".join("1" if bit else "0" for bit in bits)

    def dhash(self, gray_img: Image.Image) -> str:
        resized = gray_img.resize(
            (self.hash_size + 1, self.hash_size),
            Image.Resampling.LANCZOS,
        )
        pixels = np.asarray(resized, dtype=np.int16)
        diff = pixels[:, 1:] > pixels[:, :-1]
        return "".join("1" if bit else "0" for bit in diff.flatten())

    def rgb_histogram(self, rgb_img: Image.Image) -> List[float]:
        arr = np.asarray(
            rgb_img.resize((256, 256), Image.Resampling.LANCZOS),
            dtype=np.uint8,
        )
        hist_parts = []
        for channel in range(3):
            hist, _ = np.histogram(
                arr[:, :, channel],
                bins=self.hist_bins,
                range=(0, 256),
            )
            hist_parts.append(hist.astype(np.float32))
        hist_vec = np.concatenate(hist_parts)
        total = float(hist_vec.sum())
        if total <= 0:
            return hist_vec.tolist()
        return (hist_vec / total).tolist()

    def extract_orb_features(
        self,
        gray_img: Image.Image,
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """提取 ORB 关键点坐标与二进制描述子。

        关键点坐标用于后续 RANSAC 几何一致性校验；描述子用于汉明距离匹配。
        """
        if cv2 is None:
            return None, None

        arr = np.asarray(gray_img, dtype=np.uint8)
        orb = cv2.ORB_create(
            nfeatures=self.orb_nfeatures,
            scaleFactor=1.2,
            nlevels=8,
            edgeThreshold=19,
            fastThreshold=12,
        )
        keypoints, descriptors = orb.detectAndCompute(arr, None)
        if not keypoints or descriptors is None or len(descriptors) == 0:
            return None, None

        coordinates = np.asarray([kp.pt for kp in keypoints], dtype=np.float32)
        return coordinates, descriptors

    def _dct_matrix(self, n: int) -> np.ndarray:
        if n in self._dct_matrix_cache:
            return self._dct_matrix_cache[n]

        matrix = np.zeros((n, n), dtype=np.float32)
        factor = np.pi / (2 * n)
        scale0 = np.sqrt(1 / n)
        scale = np.sqrt(2 / n)
        for k in range(n):
            for i in range(n):
                alpha = scale0 if k == 0 else scale
                matrix[k, i] = alpha * np.cos((2 * i + 1) * k * factor)
        self._dct_matrix_cache[n] = matrix
        return matrix

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import List

import numpy as np
from PIL import Image, ImageOps

from .models import ImageFeature


class FeatureExtractor:
    """负责提取图片多维特征。

    论文对应：图片特征提取模块。
    - SHA256：用于判断文件级别是否完全一致。
    - pHash：用于识别压缩、轻微亮度变化等视觉近似图片。
    - dHash：用于识别结构和边缘变化较小的图片。
    - RGB 颜色直方图：作为辅助视觉特征，提高融合判断的稳定性。
    """

    def __init__(self, hash_size: int = 8, phash_resize: int = 32, hist_bins: int = 16) -> None:
        self.hash_size = hash_size
        self.phash_resize = phash_resize
        self.hist_bins = hist_bins
        self._dct_matrix_cache = {}

    def extract(self, image_path: str | Path, image_id: str) -> ImageFeature:
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"图片不存在：{path}")

        with Image.open(path) as img:
            img = ImageOps.exif_transpose(img)
            width, height = img.size
            rgb_img = img.convert("RGB")
            gray_img = img.convert("L")
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
            )

    @staticmethod
    def sha256_file(path: str | Path) -> str:
        """计算文件 SHA256 摘要。"""
        digest = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def phash(self, gray_img: Image.Image) -> str:
        """计算感知哈希 pHash。

        这里不依赖 OpenCV 或 scipy，直接用 numpy 构造 DCT 变换矩阵，方便老师在普通
        Python 环境中查看和运行。
        """
        size = self.phash_resize
        small = gray_img.resize((size, size), Image.Resampling.LANCZOS)
        pixels = np.asarray(small, dtype=np.float32)
        dct_matrix = self._dct_matrix(size)
        dct_result = dct_matrix @ pixels @ dct_matrix.T
        low_freq = dct_result[: self.hash_size, : self.hash_size].copy()
        values = low_freq.flatten()
        # 排除 DC 分量，减少整体亮度对哈希的影响。
        median = np.median(values[1:])
        bits = values > median
        return "".join("1" if bit else "0" for bit in bits)

    def dhash(self, gray_img: Image.Image) -> str:
        """计算差异哈希 dHash。"""
        resized = gray_img.resize((self.hash_size + 1, self.hash_size), Image.Resampling.LANCZOS)
        pixels = np.asarray(resized, dtype=np.int16)
        diff = pixels[:, 1:] > pixels[:, :-1]
        return "".join("1" if bit else "0" for bit in diff.flatten())

    def rgb_histogram(self, rgb_img: Image.Image) -> List[float]:
        """计算 RGB 颜色直方图，并进行归一化。"""
        arr = np.asarray(rgb_img.resize((256, 256), Image.Resampling.LANCZOS), dtype=np.uint8)
        hist_parts = []
        for channel in range(3):
            hist, _ = np.histogram(arr[:, :, channel], bins=self.hist_bins, range=(0, 256))
            hist_parts.append(hist.astype(np.float32))
        hist_vec = np.concatenate(hist_parts)
        total = hist_vec.sum()
        if total <= 0:
            return hist_vec.tolist()
        return (hist_vec / total).tolist()

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

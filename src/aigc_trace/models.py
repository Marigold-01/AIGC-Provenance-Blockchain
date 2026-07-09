from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass
class ImageFeature:
    """图片特征数据结构。"""

    image_id: str
    file_name: str
    file_path: str
    sha256: str
    phash: str
    dhash: str
    histogram: List[float]
    width: int
    height: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SimilarityResult:
    """两张图片的相似度结果。"""

    source_id: str
    target_id: str
    sha256_equal: bool
    sha256_score: float
    phash_score: float
    dhash_score: float
    histogram_score: float
    fusion_score: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TraceRecord:
    """一次图片上传或传播产生的可信溯源记录。"""

    version_id: str
    file_name: str
    file_path: str
    parent_id: Optional[str]
    parent_file: Optional[str]
    uploader: str
    timestamp: str
    sha256: str
    phash: str
    dhash: str
    width: int
    height: int
    best_similarity: float
    phash_similarity: float
    dhash_similarity: float
    histogram_similarity: float
    governance_label: str
    governance_reason: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Block:
    """模拟区块结构。"""

    index: int
    timestamp: str
    previous_hash: str
    nonce: int
    record: Dict[str, Any]
    block_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

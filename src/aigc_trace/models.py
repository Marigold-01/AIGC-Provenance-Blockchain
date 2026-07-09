from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ImageFeature:
    """图片特征数据结构。ORB 原始特征仅保存在内存中，不直接写入结果文件。"""

    image_id: str
    file_name: str
    file_path: str
    sha256: str
    phash: str
    dhash: str
    histogram: List[float]
    width: int
    height: int
    orb_keypoint_count: int = 0
    orb_keypoints: Any = field(default=None, repr=False, compare=False)
    orb_descriptors: Any = field(default=None, repr=False, compare=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "image_id": self.image_id,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "sha256": self.sha256,
            "phash": self.phash,
            "dhash": self.dhash,
            "histogram": self.histogram,
            "width": self.width,
            "height": self.height,
            "orb_keypoint_count": self.orb_keypoint_count,
        }


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
    orb_score: float
    fusion_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "sha256_equal": self.sha256_equal,
            "sha256_score": self.sha256_score,
            "phash_score": self.phash_score,
            "dhash_score": self.dhash_score,
            "histogram_score": self.histogram_score,
            "orb_score": self.orb_score,
            "fusion_score": self.fusion_score,
        }


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

    # 图片内容摘要与视觉特征
    sha256: str
    phash: str
    dhash: str
    width: int
    height: int
    orb_keypoint_count: int

    # 同源识别结果
    best_similarity: float
    phash_similarity: float
    dhash_similarity: float
    histogram_similarity: float
    orb_similarity: float

    # AIGC 来源与演化元数据。这里记录的是上传方声明/实验标注，
    # 不等同于系统自动鉴定图片由某个模型生成。
    declared_aigc: Optional[bool]
    content_origin: str
    generation_model: str
    generation_prompt_hash: str
    edit_type: str
    source_name: str
    source_platform: str
    declared_parent_file: Optional[str]
    metadata_status: str
    metadata_notes: str

    # 治理输出
    governance_label: str
    governance_reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version_id": self.version_id,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "parent_id": self.parent_id,
            "parent_file": self.parent_file,
            "uploader": self.uploader,
            "timestamp": self.timestamp,
            "sha256": self.sha256,
            "phash": self.phash,
            "dhash": self.dhash,
            "width": self.width,
            "height": self.height,
            "orb_keypoint_count": self.orb_keypoint_count,
            "best_similarity": self.best_similarity,
            "phash_similarity": self.phash_similarity,
            "dhash_similarity": self.dhash_similarity,
            "histogram_similarity": self.histogram_similarity,
            "orb_similarity": self.orb_similarity,
            "declared_aigc": self.declared_aigc,
            "content_origin": self.content_origin,
            "generation_model": self.generation_model,
            "generation_prompt_hash": self.generation_prompt_hash,
            "edit_type": self.edit_type,
            "source_name": self.source_name,
            "source_platform": self.source_platform,
            "declared_parent_file": self.declared_parent_file,
            "metadata_status": self.metadata_status,
            "metadata_notes": self.metadata_notes,
            "governance_label": self.governance_label,
            "governance_reason": self.governance_reason,
        }


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
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "record": self.record,
            "block_hash": self.block_hash,
        }

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, Mapping

from .storage import load_json


DEFAULT_METADATA: Dict[str, Any] = {
    "declared_aigc": None,
    "content_origin": "未声明",
    "generation_model": "未声明",
    "generation_prompt_hash": "",
    "edit_type": "未声明",
    "source_name": "未声明",
    "source_platform": "未声明",
    "declared_parent_file": None,
    "metadata_status": "未提供",
    "metadata_notes": "",
}


def hash_prompt(prompt: str) -> str:
    """对生成提示词计算 SHA256，仅保存摘要，不把原始提示词写入链上。"""
    text = prompt.strip()
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_image_metadata(path: str | Path) -> Dict[str, Dict[str, Any]]:
    """读取按文件名索引的图片元数据。

    支持两种 JSON 结构：
    1. {"01_original.jpg": {...}}
    2. {"images": {"01_original.jpg": {...}}}
    """
    metadata_path = Path(path)
    if not metadata_path.exists():
        return {}

    raw = load_json(metadata_path)
    if "images" in raw and isinstance(raw["images"], dict):
        raw = raw["images"]
    if not isinstance(raw, dict):
        raise ValueError("图片元数据文件必须是以图片文件名为键的 JSON 对象。")

    result: Dict[str, Dict[str, Any]] = {}
    for file_name, item in raw.items():
        if isinstance(item, dict):
            result[str(file_name)] = item
    return result


def normalize_metadata(
    file_name: str,
    metadata_by_file: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    """取出并规范化单张图片的元数据。文件名支持不区分大小写匹配。"""
    item = metadata_by_file.get(file_name)
    if item is None:
        lower_map = {str(key).lower(): value for key, value in metadata_by_file.items()}
        item = lower_map.get(file_name.lower())

    if item is None:
        return DEFAULT_METADATA.copy()

    normalized = DEFAULT_METADATA.copy()
    normalized["metadata_status"] = "已提供"

    declared_aigc = item.get("declared_aigc")
    if isinstance(declared_aigc, bool):
        normalized["declared_aigc"] = declared_aigc

    for key in (
        "content_origin",
        "generation_model",
        "edit_type",
        "source_name",
        "source_platform",
        "metadata_notes",
    ):
        value = item.get(key)
        if value is not None and str(value).strip():
            normalized[key] = str(value).strip()

    declared_parent = item.get("declared_parent_file")
    if declared_parent is not None and str(declared_parent).strip():
        normalized["declared_parent_file"] = str(declared_parent).strip()

    prompt_hash = str(item.get("generation_prompt_hash", "")).strip()
    prompt_text = str(item.get("generation_prompt", "")).strip()
    normalized["generation_prompt_hash"] = prompt_hash or hash_prompt(prompt_text)

    return normalized

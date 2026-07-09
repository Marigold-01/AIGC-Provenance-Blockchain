from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Sequence, Tuple

from .models import Block, TraceRecord


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class SimpleBlockchain:
    """轻量级模拟区块链。

    论文对应：区块链可信存证模块。
    设计目标：体现“链式结构、前后哈希关联、时间戳、不可篡改校验”的核心思想。
    """

    def __init__(self) -> None:
        self.chain: List[Block] = []
        self._create_genesis_block()

    def _create_genesis_block(self) -> None:
        genesis_record = {
            "type": "genesis",
            "description": "AIGC 新闻图片可信溯源系统创世区块",
        }
        block = self._build_block(index=0, previous_hash="0" * 64, record=genesis_record)
        self.chain.append(block)

    def add_record(self, record: TraceRecord) -> Block:
        previous = self.chain[-1]
        block = self._build_block(
            index=len(self.chain),
            previous_hash=previous.block_hash,
            record=record.to_dict(),
        )
        self.chain.append(block)
        return block

    def validate_chain(self) -> bool:
        """校验内存中的链上数据是否被篡改。"""
        valid, _ = self.validate_exported_chain(self.to_list())
        return valid

    def to_list(self) -> List[Dict[str, Any]]:
        return [block.to_dict() for block in self.chain]

    def _build_block(self, index: int, previous_hash: str, record: Dict[str, Any]) -> Block:
        timestamp = utc_now()
        nonce = 0
        block_hash = self.calculate_hash(index, timestamp, previous_hash, nonce, record)
        return Block(
            index=index,
            timestamp=timestamp,
            previous_hash=previous_hash,
            nonce=nonce,
            record=record,
            block_hash=block_hash,
        )

    @staticmethod
    def calculate_hash(index: int, timestamp: str, previous_hash: str, nonce: int, record: Dict[str, Any]) -> str:
        block_content = {
            "index": index,
            "timestamp": timestamp,
            "previous_hash": previous_hash,
            "nonce": nonce,
            "record": record,
        }
        encoded = json.dumps(block_content, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @classmethod
    def validate_exported_chain(cls, blocks: Sequence[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """校验从 JSON 文件读取的区块链记录。

        返回：
            (是否通过, 错误信息列表)
        """
        errors: List[str] = []
        if not isinstance(blocks, Sequence) or isinstance(blocks, (str, bytes)):
            return False, ["区块链数据必须是 JSON 数组。"]
        if len(blocks) == 0:
            return False, ["区块链数据为空。"]

        required_fields = {
            "index",
            "timestamp",
            "previous_hash",
            "nonce",
            "record",
            "block_hash",
        }

        for position, block in enumerate(blocks):
            if not isinstance(block, dict):
                errors.append(f"位置 {position} 的区块不是 JSON 对象。")
                continue

            missing = required_fields - set(block)
            if missing:
                errors.append(f"区块 {position} 缺少字段：{sorted(missing)}。")
                continue

            if block["index"] != position:
                errors.append(
                    f"区块 {position} 的 index 为 {block['index']}，与所在位置不一致。"
                )

            recalculated = cls.calculate_hash(
                index=block["index"],
                timestamp=block["timestamp"],
                previous_hash=block["previous_hash"],
                nonce=block["nonce"],
                record=block["record"],
            )
            if recalculated != block["block_hash"]:
                errors.append(f"区块 {position} 的 block_hash 校验失败，记录可能已被修改。")

            if position == 0:
                if block["previous_hash"] != "0" * 64:
                    errors.append("创世区块的 previous_hash 不正确。")
            else:
                previous = blocks[position - 1]
                if isinstance(previous, dict) and "block_hash" in previous:
                    if block["previous_hash"] != previous["block_hash"]:
                        errors.append(
                            f"区块 {position} 的 previous_hash 与前一区块 block_hash 不一致。"
                        )

        return len(errors) == 0, errors

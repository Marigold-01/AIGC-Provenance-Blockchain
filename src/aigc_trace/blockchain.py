from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List

from .models import Block, TraceRecord


def utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


class SimpleBlockchain:
    """轻量级模拟区块链。

    论文对应：区块链可信存证模块。
    设计目标：体现区块链“链式结构、前后哈希关联、时间戳、不可篡改校验”的核心思想。
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
        """校验链上数据是否被篡改。"""
        for i, block in enumerate(self.chain):
            recalculated = self.calculate_hash(
                index=block.index,
                timestamp=block.timestamp,
                previous_hash=block.previous_hash,
                nonce=block.nonce,
                record=block.record,
            )
            if recalculated != block.block_hash:
                return False
            if i > 0 and block.previous_hash != self.chain[i - 1].block_hash:
                return False
        return True

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

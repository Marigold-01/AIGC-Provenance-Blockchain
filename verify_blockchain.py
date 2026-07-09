from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aigc_trace.blockchain import SimpleBlockchain
from aigc_trace.storage import load_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="独立校验已导出的区块链存证记录")
    parser.add_argument(
        "--file",
        default="results/blockchain_records.json",
        help="待校验的区块链 JSON 文件",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    file_path = Path(args.file)
    if not file_path.is_absolute():
        file_path = PROJECT_ROOT / file_path

    if not file_path.exists():
        raise FileNotFoundError(f"区块链记录文件不存在：{file_path}")

    blocks = load_json(file_path)
    valid, errors = SimpleBlockchain.validate_exported_chain(blocks)

    print("\n====== 区块链独立完整性校验 ======")
    print(f"校验文件：{file_path}")
    print(f"区块数量：{len(blocks) if isinstance(blocks, list) else 0}")
    if valid:
        print("校验结果：通过，未发现链上记录被修改。")
        return

    print("校验结果：失败。")
    for index, error in enumerate(errors, start=1):
        print(f"{index}. {error}")
    raise SystemExit(1)


if __name__ == "__main__":
    main()

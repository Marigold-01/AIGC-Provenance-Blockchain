from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from aigc_trace.similarity import hash_similarity
from aigc_trace.blockchain import SimpleBlockchain


def test_hash_similarity_same():
    assert hash_similarity("1010", "1010") == 1.0


def test_hash_similarity_half():
    assert hash_similarity("1111", "1100") == 0.5


def test_blockchain_genesis_valid():
    chain = SimpleBlockchain()
    assert chain.validate_chain() is True
    assert len(chain.chain) == 1

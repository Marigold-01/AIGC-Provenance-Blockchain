from copy import deepcopy
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from aigc_trace.blockchain import SimpleBlockchain
from aigc_trace.evaluation import binary_metrics, optimize_threshold_from_scores
from aigc_trace.feature_extractor import FeatureExtractor
from aigc_trace.metadata import hash_prompt, normalize_metadata
from aigc_trace.similarity import SimilarityCalculator, hash_similarity


def test_hash_similarity_same():
    assert hash_similarity("1010", "1010") == 1.0


def test_hash_similarity_half():
    assert hash_similarity("1111", "1100") == 0.5


def test_blockchain_genesis_valid():
    chain = SimpleBlockchain()
    assert chain.validate_chain() is True
    assert len(chain.chain) == 1


def test_exported_chain_detects_tampering():
    chain = SimpleBlockchain()
    exported = chain.to_list()
    valid, errors = SimpleBlockchain.validate_exported_chain(exported)
    assert valid is True
    assert errors == []

    tampered = deepcopy(exported)
    tampered[0]["record"]["description"] = "被修改"
    valid, errors = SimpleBlockchain.validate_exported_chain(tampered)
    assert valid is False
    assert errors


def test_prompt_is_hashed():
    assert len(hash_prompt("一段生成提示词")) == 64
    assert hash_prompt("") == ""


def test_metadata_normalization():
    result = normalize_metadata(
        "a.jpg",
        {
            "a.jpg": {
                "declared_aigc": True,
                "content_origin": "AIGC生成",
                "generation_prompt": "test prompt",
            }
        },
    )
    assert result["metadata_status"] == "已提供"
    assert result["declared_aigc"] is True
    assert len(result["generation_prompt_hash"]) == 64


def test_binary_metrics():
    metrics = binary_metrics([True, True, False, False], [True, False, True, False])
    assert metrics["tp"] == 1
    assert metrics["tn"] == 1
    assert metrics["fp"] == 1
    assert metrics["fn"] == 1
    assert metrics["accuracy"] == 0.5
    assert metrics["balanced_accuracy"] == 0.5


def test_threshold_optimizer_finds_separating_interval():
    result = optimize_threshold_from_scores(
        [True, True, True, False, False],
        [0.82, 0.68, 0.61, 0.42, 0.31],
        start=0.30,
        end=0.90,
        step=0.01,
    )
    assert result["f1"] == 1.0
    assert 0.42 < result["threshold"] <= 0.61
    assert result["separation_margin"] == 0.19


def test_orb_improves_local_edit_similarity(tmp_path):
    original = Image.new("RGB", (500, 360), "white")
    draw = ImageDraw.Draw(original)
    # 生成包含角点和纹理的测试图，便于 ORB 提取稳定特征。
    for x in range(30, 470, 40):
        for y in range(30, 330, 40):
            draw.rectangle((x, y, x + 18, y + 18), outline="black", width=3)
    draw.ellipse((160, 90, 340, 270), outline="black", width=8)
    draw.line((60, 300, 440, 50), fill="black", width=6)
    original_path = tmp_path / "original.jpg"
    original.save(original_path, quality=95)

    edited = original.copy()
    edited_draw = ImageDraw.Draw(edited)
    edited_draw.rectangle((0, 0, 130, 90), fill="gray")
    edited_path = tmp_path / "edited.jpg"
    edited.save(edited_path, quality=90)

    extractor = FeatureExtractor()
    feature_a = extractor.extract(original_path, "A")
    feature_b = extractor.extract(edited_path, "B")
    result = SimilarityCalculator().compare(feature_a, feature_b)

    assert feature_a.orb_keypoint_count > 0
    assert feature_b.orb_keypoint_count > 0
    assert 0.0 <= result.orb_score <= 1.0
    assert result.orb_score > 0.30
    assert 0.0 <= result.fusion_score <= 1.0


def test_eight_image_metadata_and_ground_truth_are_aligned():
    import json

    metadata = json.loads((ROOT / "data" / "image_metadata.json").read_text(encoding="utf-8"))["images"]
    ground_truth = json.loads((ROOT / "data" / "ground_truth.json").read_text(encoding="utf-8"))["samples"]
    expected = {
        "01_original.jpg",
        "02_compressed.jpg",
        "03_add_caption.jpg",
        "04_cropped.jpg",
        "05_aigc_edited.jpg",
        "06_brightness.jpg",
        "07_blur.jpg",
        "08_different.jpg",
    }
    assert set(metadata) == expected
    assert set(ground_truth) == expected

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pandas as pd


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_json(data: Any, path: str | Path) -> None:
    p = Path(path)
    ensure_dir(p.parent)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json(path: str | Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_csv(rows: Iterable[Dict[str, Any]], path: str | Path) -> None:
    p = Path(path)
    ensure_dir(p.parent)
    df = pd.DataFrame(list(rows))
    df.to_csv(p, index=False, encoding="utf-8-sig")


def list_images(input_dir: str | Path, supported_ext: List[str]) -> List[Path]:
    root = Path(input_dir)
    if not root.exists():
        raise FileNotFoundError(f"输入目录不存在：{root}")
    supported = {ext.lower() for ext in supported_ext}
    images = [p for p in root.iterdir() if p.is_file() and p.suffix.lower() in supported]
    return sorted(images, key=lambda p: p.name.lower())

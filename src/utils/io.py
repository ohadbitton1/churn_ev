# src/utils/io.py
from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_json(obj: Any, path: str | Path) -> Path:
    p = Path(path)
    ensure_dir(p.parent)
    if is_dataclass(obj):
        obj = asdict(obj)
    with p.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    return p


def load_json(path: str | Path) -> Any:
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# api/metrics_routes.py
from __future__ import annotations

import csv
import math
from pathlib import Path

from fastapi import APIRouter, HTTPException

BASE_DIR = Path(__file__).resolve().parents[1]
METRICS_CSV = BASE_DIR / "monitoring" / "metrics.csv"

router = APIRouter(prefix="/metrics", tags=["metrics"])


def _read_rows(limit: int = 10000) -> list[dict[str, str]]:
    if not METRICS_CSV.exists():
        return []
    rows: list[dict[str, str]] = []
    with METRICS_CSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            rows.append(row)
            if i >= limit:
                break
    return rows


def _p95(values: list[float]) -> float:
    if not values:
        return float("nan")
    values = sorted(values)
    # nearest-rank-ish index
    k = max(0, min(len(values) - 1, math.floor(0.95 * (len(values) - 1))))
    return float(values[k])


@router.get("/summary", summary="Basic counts and p95 latency per route")
def metrics_summary():
    rows = _read_rows()
    if not rows:
        raise HTTPException(
            status_code=404, detail="No metrics yet. Hit a few endpoints and retry."
        )

    by_path: dict[str, dict[str, list[float] | int]] = {}
    for r in rows:
        path = r.get("path", "")
        status = int(r.get("status", "0") or 0)
        dur = float(r.get("duration_ms", "0") or 0.0)
        bucket = by_path.setdefault(path, {"count": 0, "errors": 0, "durations": []})
        bucket["count"] = int(bucket["count"]) + 1
        if status >= 500:
            bucket["errors"] = int(bucket["errors"]) + 1
        bucket["durations"].append(dur)

    out = []
    for path, agg in by_path.items():
        durations = agg["durations"]  # type: ignore
        out.append(
            {
                "path": path,
                "count": int(agg["count"]),  # type: ignore
                "errors": int(agg["errors"]),  # type: ignore
                "p95_ms": round(_p95([float(x) for x in durations]), 2),
            }
        )

    out.sort(key=lambda x: (-x["count"], x["path"]))
    return {"items": out, "source": str(METRICS_CSV)}

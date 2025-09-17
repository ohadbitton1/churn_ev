#!/usr/bin/env python
"""
Generate an Evidently drift HTML report comparing a reference CSV to a current CSV.

Usage (from repo root):
  # simplest (uses data/reference.csv and data/current.csv)
  python monitoring/run_drift.py

  # explicit paths
  python monitoring/run_drift.py --reference data/reference.csv --current data/current.csv

Outputs:
  monitoring/reports/<timestamp>-drift.html

Notes:
- If a model artifact exists (models/best_pipeline.pkl), we add a 'prediction'
  probability column to both datasets (best-effort; failure is non-fatal).
- Works with evidently>=0.7.x.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd
from evidently.metric_preset import DataDriftPreset
from evidently.metrics import ColumnDriftMetric
from evidently.report import Report

# ---------- Paths ----------
REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = REPO_ROOT / "models"
REPORTS_DIR = REPO_ROOT / "monitoring" / "reports"
DEFAULT_REF = REPO_ROOT / "data" / "reference.csv"
DEFAULT_CUR = REPO_ROOT / "data" / "current.csv"
MODEL_PATH = MODELS_DIR / "best_pipeline.pkl"  # <- FIX: always a Path (no dicts)


# ---------- Helpers ----------
def _ensure_sys_path() -> None:
    """Make sure custom transformers are importable during joblib.load()."""
    import sys as _sys

    for p in (REPO_ROOT, REPO_ROOT / "src"):
        sp = str(p)
        if sp not in _sys.path:
            _sys.path.append(sp)


def load_pipeline() -> object | None:
    """Load the training pipeline if available; return None on failure."""
    try:
        _ensure_sys_path()
        if MODEL_PATH.exists():
            return joblib.load(MODEL_PATH)
    except Exception:
        return None
    return None


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    return pd.read_csv(path, low_memory=False)


def maybe_add_prediction(
    df_ref: pd.DataFrame, df_cur: pd.DataFrame, pipe: object | None
) -> tuple[pd.DataFrame, pd.DataFrame, bool]:
    """
    If a model is available and has predict_proba, add 'prediction' column (p(churn)).
    Returns (df_ref, df_cur, added_flag).
    """
    if pipe is None or not hasattr(pipe, "predict_proba"):
        return df_ref, df_cur, False
    try:
        ref = df_ref.copy()
        cur = df_cur.copy()
        ref["prediction"] = pipe.predict_proba(ref)[:, 1]
        cur["prediction"] = pipe.predict_proba(cur)[:, 1]
        return ref, cur, True
    except Exception:
        # Non-fatal: just skip prediction column if it fails
        return df_ref, df_cur, False


def build_report(df_ref: pd.DataFrame, df_cur: pd.DataFrame, include_pred_metric: bool) -> Report:
    """Create an Evidently report with data drift + optional prediction drift."""
    metrics = [DataDriftPreset()]
    if include_pred_metric and "prediction" in df_ref.columns and "prediction" in df_cur.columns:
        metrics.append(ColumnDriftMetric(column_name="prediction"))
    rep = Report(metrics=metrics)
    rep.run(reference_data=df_ref, current_data=df_cur)
    return rep


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate Evidently drift HTML report.")
    p.add_argument(
        "--reference",
        type=Path,
        default=DEFAULT_REF,
        help="Reference CSV (default: data/reference.csv)",
    )
    p.add_argument(
        "--current", type=Path, default=DEFAULT_CUR, help="Current CSV (default: data/current.csv)"
    )
    p.add_argument(
        "--outdir",
        type=Path,
        default=REPORTS_DIR,
        help="Output directory (default: monitoring/reports)",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    df_ref = read_csv(args.reference)
    df_cur = read_csv(args.current)

    pipe = load_pipeline()
    df_ref, df_cur, added_pred = maybe_add_prediction(df_ref, df_cur, pipe)

    report = build_report(df_ref, df_cur, include_pred_metric=added_pred)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = args.outdir / f"{ts}-drift.html"
    report.save_html(str(out_path))

    # Print absolute path so automation/scripts can capture it
    print(str(out_path.resolve()))


if __name__ == "__main__":
    main()

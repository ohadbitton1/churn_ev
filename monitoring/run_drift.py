# monitoring/run_drift.py
"""
Generate Evidently drift report between a reference and a current CSV.

Usage (from repo root):
  python monitoring/run_drift.py --reference data/reference.csv --current data/current.csv

Prints the absolute path of the created HTML report on success.
Works with evidently>=0.7.x.
"""
from __future__ import annotations

import argparse
import json
import sys
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

MODEL_PATH = Path(
    sys.argv and {}  # placeholder for env passthrough if desired
)  # will fall back below if empty
if not MODEL_PATH:
    MODEL_PATH = MODELS_DIR / "best_pipeline.pkl"

METADATA_PATH = MODELS_DIR / "metadata.json"


# ---------- Helpers ----------
def _ensure_sys_path() -> None:
    # Make sure our custom transformers are importable during joblib.load
    root = REPO_ROOT
    src = REPO_ROOT / "src"
    for p in (root, src):
        sp = str(p)
        if sp not in sys.path:
            sys.path.append(sp)


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
    return pd.read_csv(path, low_memory=False)


def get_threshold() -> float:
    """Read threshold from metadata.json if present; else default to 0.5."""
    try:
        if METADATA_PATH.exists():
            meta = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
            for k in ("threshold", "decision_threshold", "production_threshold"):
                if k in meta and isinstance(meta[k], int | float):
                    return float(meta[k])
    except Exception:
        pass
    return 0.5


def maybe_add_prediction(
    df_ref: pd.DataFrame, df_cur: pd.DataFrame, pipe: object | None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """If a model is available, add 'prediction' prob column to both frames."""
    if pipe is None:
        return df_ref, df_cur
    try:
        if hasattr(pipe, "predict_proba"):
            df_ref = df_ref.copy()
            df_cur = df_cur.copy()
            df_ref["prediction"] = pipe.predict_proba(df_ref)[:, 1]
            df_cur["prediction"] = pipe.predict_proba(df_cur)[:, 1]
    except Exception:
        # Non-fatal: just skip prediction column if it fails
        return df_ref, df_cur
    return df_ref, df_cur


def build_report(df_ref: pd.DataFrame, df_cur: pd.DataFrame, with_pred_metric: bool) -> Report:
    metrics = [DataDriftPreset()]
    if with_pred_metric and "prediction" in df_ref.columns and "prediction" in df_cur.columns:
        metrics.append(ColumnDriftMetric(column_name="prediction"))
    rep = Report(metrics=metrics)
    rep.run(reference_data=df_ref, current_data=df_cur)
    return rep


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Evidently drift HTML report.")
    parser.add_argument("--reference", type=Path, required=True, help="Reference CSV.")
    parser.add_argument("--current", type=Path, required=True, help="Current CSV.")
    parser.add_argument(
        "--outdir",
        type=Path,
        default=REPORTS_DIR,
        help="Directory to write HTML reports.",
    )
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)

    df_ref = read_csv(args.reference)
    df_cur = read_csv(args.current)

    pipe = load_pipeline()
    df_ref, df_cur = maybe_add_prediction(df_ref, df_cur, pipe)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    outfile = args.outdir / f"{ts}-drift.html"

    report = build_report(df_ref, df_cur, with_pred_metric=True)
    report.save_html(str(outfile))

    # Print absolute path so automation can capture it
    print(str(outfile.resolve()))


if __name__ == "__main__":
    main()

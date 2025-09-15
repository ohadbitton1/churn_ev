# scripts/run_threshold_sweep.py
"""
CLI example:
python -m scripts.run_threshold_sweep --ytrue data/val_y_true.csv --yprob data/val_y_prob.csv --outdir artifacts/decisions
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.decision.costs import CostConfig, save_costs
from src.decision.report import export_curve_csv, plot_decision_curve
from src.decision.thresholds import choose_optimal_threshold, sweep_thresholds
from src.utils.io import ensure_dir, save_json, utcnow_iso


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ytrue", required=True, help="CSV with column y_true or a 1-col CSV.")
    ap.add_argument("--yprob", required=True, help="CSV with column y_prob or a 1-col CSV.")
    ap.add_argument("--step", type=float, default=0.005)
    ap.add_argument("--outdir", default="artifacts/decisions")
    ap.add_argument("--model_version", default="v1")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    ensure_dir(outdir)

    # Load arrays
    def load_vec(path: str, colname: str) -> np.ndarray:
        df = pd.read_csv(path)
        if colname in df.columns:
            return df[colname].to_numpy()
        # otherwise, assume first column
        return df.iloc[:, 0].to_numpy()

    y_true = load_vec(args.ytrue, "y_true").astype(int)
    y_prob = load_vec(args.yprob, "y_prob").astype(float)

    costs = CostConfig()  # defaults; adjust if needed

    df_curve = sweep_thresholds(y_true, y_prob, costs=costs, step=args.step)
    summary = choose_optimal_threshold(df_curve)

    png_path = outdir / "decision_curve.png"
    csv_path = outdir / "decision_curve.csv"
    config_path = outdir / "config.json"
    costs_path = outdir / "costs.json"

    plot_decision_curve(df_curve, png_path)
    export_curve_csv(df_curve, csv_path)

    config = {
        "model_version": args.model_version,
        "generated_at": utcnow_iso(),
        "costs": {
            "FN_cost": costs.FN_cost,
            "FP_cost": costs.FP_cost,
            "TP_intervention_cost": costs.TP_intervention_cost,
            "TN_cost": costs.TN_cost,
        },
        "decision": summary,
    }
    save_json(config, config_path)
    save_costs(costs, costs_path)

    print("Best threshold:", summary["threshold"])
    print("Expected value:", summary["expected_value"])
    print("Saved:", png_path, csv_path, config_path, costs_path)


if __name__ == "__main__":
    main()

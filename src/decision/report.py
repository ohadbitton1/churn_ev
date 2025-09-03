# src/decision/report.py
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def plot_decision_curve(df_curve: pd.DataFrame, out_path_png: str | Path) -> str:
    """Save EV vs Threshold plot and return the output path as str."""
    out = Path(out_path_png)
    out.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(7, 4))
    plt.plot(df_curve["threshold"], df_curve["expected_value"])
    plt.xlabel("Threshold")
    plt.ylabel("Expected Value (–Total Cost)")
    plt.title("Decision Curve – Expected Value vs Threshold")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out, dpi=160)
    plt.close()
    return str(out)


def export_curve_csv(df_curve: pd.DataFrame, out_path_csv: str | Path) -> str:
    out = Path(out_path_csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    df_curve.to_csv(out, index=False)
    return str(out)

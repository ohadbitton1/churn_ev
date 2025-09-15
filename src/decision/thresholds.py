# src/decision/thresholds.py
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix

from .costs import CostConfig


@dataclass(frozen=True)
class ThresholdResult:
    threshold: float
    expected_value: float
    tn: int
    fp: int
    fn: int
    tp: int


def expected_value_for_threshold(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    thr: float,
    costs: CostConfig,
) -> tuple[float, tuple[int, int, int, int]]:
    """Return (EV, (tn, fp, fn, tp)) for a given threshold."""
    y_pred = (y_prob >= thr).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()

    total_cost = (
        tp * costs.TP_intervention_cost
        + fp * costs.FP_cost
        + fn * costs.FN_cost
        + tn * costs.TN_cost
    )
    ev = -float(total_cost)  # higher is better
    return ev, (tn, fp, fn, tp)


def sweep_thresholds(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    costs: CostConfig,
    step: float = 0.005,
) -> pd.DataFrame:
    """Scan thresholds [0,1] and return a DataFrame with EV and counts."""
    thrs = np.arange(0.0, 1.0 + step, step)
    rows = []
    for t in thrs:
        ev, (tn, fp, fn, tp) = expected_value_for_threshold(y_true, y_prob, t, costs)
        rows.append(
            {
                "threshold": float(t),
                "expected_value": float(ev),
                "tn": int(tn),
                "fp": int(fp),
                "fn": int(fn),
                "tp": int(tp),
            }
        )
    return pd.DataFrame(rows)


def choose_optimal_threshold(df_curve: pd.DataFrame) -> dict[str, float]:
    """Pick the threshold with maximum EV; return a small summary dict."""
    if df_curve.empty:
        raise ValueError("df_curve is empty")
    idx = df_curve["expected_value"].idxmax()
    row = df_curve.loc[idx]
    return {
        "threshold": float(row["threshold"]),
        "expected_value": float(row["expected_value"]),
        "tn": int(row["tn"]),
        "fp": int(row["fp"]),
        "fn": int(row["fn"]),
        "tp": int(row["tp"]),
    }

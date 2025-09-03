# tests/test_decision_layer.py
import numpy as np
import pandas as pd

from src.decision.costs import CostConfig
from src.decision.policy import apply_decision_batch, decide_single_threshold
from src.decision.thresholds import (
    choose_optimal_threshold,
    expected_value_for_threshold,
    sweep_thresholds,
)


def test_expected_value_shapes():
    y_true = np.array([0, 0, 1, 1])
    y_prob = np.array([0.1, 0.2, 0.8, 0.9])
    costs = CostConfig(FN_cost=5, FP_cost=1, TP_intervention_cost=0.5, TN_cost=0)

    ev, (tn, fp, fn, tp) = expected_value_for_threshold(
        y_true, y_prob, thr=0.5, costs=costs
    )
    # With thr=0.5 -> preds = [0,0,1,1] so cm: tn=2, fp=0, fn=0, tp=2
    assert (tn, fp, fn, tp) == (2, 0, 0, 2)
    # Total cost = tp*0.5 = 1.0, EV = -1.0
    assert ev == -1.0


def test_sweep_and_pick():
    y_true = np.array([0, 0, 1, 1])
    y_prob = np.array([0.49, 0.51, 0.49, 0.99])
    costs = CostConfig(FN_cost=5, FP_cost=1, TP_intervention_cost=0.5, TN_cost=0)

    df = sweep_thresholds(y_true, y_prob, costs, step=0.5)
    assert isinstance(df, pd.DataFrame)
    summary = choose_optimal_threshold(df)
    assert "threshold" in summary and "expected_value" in summary


def test_policy_single_and_batch():
    costs = CostConfig()
    s = decide_single_threshold(0.7, thr=0.6, costs=costs)
    assert s["action"] == "intervene"

    s2 = decide_single_threshold(0.2, thr=0.6, costs=costs)
    assert s2["action"] == "no_action"

    out = apply_decision_batch([0.1, 0.7], thr=0.5, costs=costs)
    assert list(out["action"]) == ["no_action", "intervene"]

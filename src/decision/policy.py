# src/decision/policy.py
from __future__ import annotations

from typing import Dict, Iterable, Literal

import numpy as np
import pandas as pd

from .costs import CostConfig

Action = Literal["intervene", "no_action"]
TierAction = Literal["expensive_intervention", "cheap_intervention", "no_action"]


def _unit_expected_value_intervene(costs: CostConfig) -> float:
    # If we intervene, on average we pay the intervention cost.
    # The "benefit" of preventing churn isn't modeled here (kept conservative).
    return -costs.TP_intervention_cost


def _unit_expected_value_no_action() -> float:
    return 0.0


def decide_single_threshold(
    p: float, thr: float, costs: CostConfig
) -> Dict[str, float | str]:
    """
    Simple policy: intervene if p >= thr, else no action.
    Returns dict with action and EV for this single sample.
    """
    if p >= thr:
        action: Action = "intervene"
        ev = _unit_expected_value_intervene(costs)
    else:
        action = "no_action"
        ev = _unit_expected_value_no_action()
    return {"action": action, "ev": float(ev)}


def decide_tiered(
    p: float,
    t_low: float,
    t_high: float,
    costs_low: CostConfig,
    costs_high: CostConfig,
) -> Dict[str, float | str]:
    """
    Tiered policy:
      p >= t_high -> expensive_intervention
      t_low <= p < t_high -> cheap_intervention
      p < t_low -> no_action
    """
    if p >= t_high:
        action: TierAction = "expensive_intervention"
        ev = _unit_expected_value_intervene(costs_high)
    elif p >= t_low:
        action = "cheap_intervention"
        ev = _unit_expected_value_intervene(costs_low)
    else:
        action = "no_action"
        ev = _unit_expected_value_no_action()
    return {"action": action, "ev": float(ev)}


def apply_decision_batch(
    probs: Iterable[float],
    thr: float,
    costs: CostConfig,
) -> pd.DataFrame:
    """
    Vectorized single-threshold policy over a batch of probabilities.
    Returns DataFrame with columns: prob, action, ev.
    """
    probs = np.asarray(list(probs), dtype=float)
    actions = np.where(probs >= thr, "intervene", "no_action")
    ev_if_intervene = -costs.TP_intervention_cost
    evs = np.where(probs >= thr, ev_if_intervene, 0.0)

    return pd.DataFrame({"prob": probs, "action": actions, "ev": evs})

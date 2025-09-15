# src/decision/costs.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..utils.io import load_json, save_json


@dataclass(frozen=True)
class CostConfig:
    """Business cost matrix for churn decisions."""

    FN_cost: float = 5.0  # missed churner (false negative)
    FP_cost: float = 1.0  # unnecessary intervention (false positive)
    TP_intervention_cost: float = 0.5  # cost when we do intervene on a true churner
    TN_cost: float = 0.0  # usually zero

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CostConfig:
        return cls(
            FN_cost=float(d.get("FN_cost", 5.0)),
            FP_cost=float(d.get("FP_cost", 1.0)),
            TP_intervention_cost=float(d.get("TP_intervention_cost", 0.5)),
            TN_cost=float(d.get("TN_cost", 0.0)),
        )


def save_costs(cfg: CostConfig, path: str | Path) -> Path:
    return save_json(cfg, path)


def load_costs(path: str | Path) -> CostConfig:
    d = load_json(path)
    return CostConfig.from_dict(d)

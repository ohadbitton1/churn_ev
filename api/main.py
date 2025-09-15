# api/main.py
import json
import os
import sys
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, status  # removed Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

# ---------- Paths & ENV ----------
BASE_DIR = Path(__file__).resolve().parents[1]

MODEL_PATH = Path(os.getenv("MODEL_PATH", BASE_DIR / "models" / "best_pipeline.pkl"))
META_PATH = Path(os.getenv("META_PATH", BASE_DIR / "models" / "metadata.json"))
FEATIMP_PATH = Path(os.getenv("FEATIMP_PATH", BASE_DIR / "models" / "feature_importance_top.csv"))

API_KEY = os.getenv("API_KEY", "dev-key-change-me")
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")

# ---------- Ensure custom transformers resolvable ----------
ROOT = Path(__file__).resolve().parents[1]
sys.path.extend([str(ROOT), str(ROOT / "src")])

# Support both "features.*" and "src.features.*" import styles
try:
    from features.build_features import AddFeatures  # noqa: F401
except ModuleNotFoundError:
    from src.features.build_features import AddFeatures  # noqa: F401

# ---------- Load artifacts ----------
model = None
metadata: dict[str, Any] = {}
top_features: list[str] = []


def _load_model():
    global model
    try:
        if MODEL_PATH.exists():
            model = joblib.load(MODEL_PATH)
        else:
            print(f"⚠️ MODEL not found at: {MODEL_PATH}")
    except Exception as e:
        print(f"⚠️ Failed to load model: {e}")


def _load_metadata():
    global metadata
    try:
        if META_PATH.exists():
            with open(META_PATH, encoding="utf-8") as f:
                metadata = json.load(f)
        else:
            print(f"⚠️ META not found at: {META_PATH}")
    except Exception as e:
        print(f"⚠️ Failed to load metadata: {e}")


def _load_top_features():
    global top_features
    try:
        if FEATIMP_PATH.exists():
            df = pd.read_csv(FEATIMP_PATH)
            col = (
                "feature"
                if "feature" in df.columns
                else ("Feature" if "Feature" in df.columns else None)
            )
            if col:
                top_features = df[col].astype(str).head(5).tolist()
    except Exception as e:
        print(f"⚠️ Failed to load top features: {e}")


_load_model()
_load_metadata()
_load_top_features()

service_version = metadata.get("version", APP_VERSION)

# ---------- FastAPI app ----------
app = FastAPI(
    title="Churn Early Warning",
    version=service_version,
    description="Predict churn risk and return a cost-aware decision.",
)

# ---------- Security (proper Swagger 'Authorize' button) ----------
# This is the key change: using FastAPI's HTTPBearer security dependency.
bearer_scheme = HTTPBearer(auto_error=True)


def api_key_guard(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    """
    Accepts 'Authorization: Bearer <token>'.
    Using HTTPBearer here makes Swagger render the green 'Authorize' button.
    """
    token = (credentials.credentials or "").strip()
    if token != API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return True


# ---------- Schemas ----------
class ScoreRequest(BaseModel):
    features: dict[str, Any] = Field(..., description="Feature dictionary of a single customer")


class ScoreResponse(BaseModel):
    probability: float
    decision: str
    expected_value: float
    action: str
    top_features: list[str] = []


# ---------- Decision & EV ----------
def get_threshold() -> float:
    return float(metadata.get("threshold", 0.5))


def get_costs() -> dict[str, float]:
    default_costs = {
        "false_negative": 5.0,
        "false_positive": 1.0,
        "true_positive_intervention": 0.5,
    }
    return {**default_costs, **metadata.get("costs", {})}


def choose_action_and_ev(p: float, threshold: float, costs: dict[str, float]):
    """
    Decision by threshold and expected value.
      - intervene if p >= threshold
      - monitor otherwise
    EV:
      if intervene:      EV = p*(benefit_tp - cost_tp_intervention) + (1-p)*(-cost_fp)
      if monitor (skip): EV = p*(-cost_fn) + (1-p)*0
    benefit_tp approximated as avoided FN cost.
    """
    cost_fn = float(costs.get("false_negative", 5.0))
    cost_fp = float(costs.get("false_positive", 1.0))
    cost_tp_int = float(costs.get("true_positive_intervention", 0.5))
    benefit_tp = cost_fn

    if p >= threshold:
        decision = "intervene"
        ev = p * (benefit_tp - cost_tp_int) + (1 - p) * (-cost_fp)
        action = metadata.get("action_on_intervene", "Send retention offer A")
    else:
        decision = "monitor"
        ev = p * (-cost_fn) + (1 - p) * 0.0
        action = metadata.get("action_on_monitor", "Monitor; no immediate action")

    return decision, ev, action


# ---------- Endpoints ----------
@app.get("/health")
def health():
    return {"status": "ok" if model is not None else "model not loaded"}


@app.get("/version")
def version():
    return {
        "service_version": service_version,
        "model_artifact": str(MODEL_PATH),
        "metadata_path": str(META_PATH),
        "threshold": get_threshold(),
        "has_top_features": bool(top_features),
    }


@app.get("/config")
def get_config():
    return {
        "service_version": service_version,
        "model_artifact": str(MODEL_PATH),
        "metadata_path": str(META_PATH),
        "threshold": get_threshold(),
        "costs": get_costs(),
    }


@app.post("/score", response_model=ScoreResponse, dependencies=[Depends(api_key_guard)])
def score(req: ScoreRequest):
    if model is None:
        raise HTTPException(status_code=500, detail="Model not loaded")

    try:
        X = pd.DataFrame([req.features])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid features format: {e}")

    try:
        if hasattr(model, "predict_proba"):
            proba = float(model.predict_proba(X)[:, 1][0])
        elif hasattr(model, "predict"):
            pred = int(model.predict(X)[0])
            proba = 1.0 if pred == 1 else 0.0
        else:
            raise ValueError("Model has neither predict_proba nor predict")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")

    threshold = get_threshold()
    costs = get_costs()
    decision, ev, action = choose_action_and_ev(proba, threshold, costs)

    return ScoreResponse(
        probability=proba,
        decision=decision,
        expected_value=ev,
        action=action,
        top_features=top_features or [],
    )


class BatchScoreRequest(BaseModel):
    items: list[ScoreRequest]


class BatchScoreResponseItem(ScoreResponse):
    customerID: str | None = None  # echo back if present


@app.post(
    "/score/batch",
    response_model=list[BatchScoreResponseItem],
    dependencies=[Depends(api_key_guard)],
)
def score_batch(req: BatchScoreRequest):
    if model is None:
        raise HTTPException(status_code=500, detail="Model not loaded")

    results: list[BatchScoreResponseItem] = []
    threshold = get_threshold()
    costs = get_costs()

    for item in req.items:
        try:
            X = pd.DataFrame([item.features])
            if hasattr(model, "predict_proba"):
                proba = float(model.predict_proba(X)[:, 1][0])
            elif hasattr(model, "predict"):
                pred = int(model.predict(X)[0])
                proba = 1.0 if pred == 1 else 0.0
            else:
                raise ValueError("Model has neither predict_proba nor predict")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Prediction failed on one item: {e}")

        decision, ev, action = choose_action_and_ev(proba, threshold, costs)
        results.append(
            BatchScoreResponseItem(
                customerID=item.features.get("customerID"),
                probability=proba,
                decision=decision,
                expected_value=ev,
                action=action,
                top_features=top_features or [],
            )
        )

    return results

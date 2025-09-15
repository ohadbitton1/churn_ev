# src/features/build_features.py
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin


class AddFeatures(BaseEstimator, TransformerMixin):
    """
    Add engineered features for the churn model pipeline.
    """

    def __init__(self, service_cols: list[str]):
        self.service_cols = service_cols

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X = X.copy()

        # --- helpers ---
        def _num(s, default=0.0):
            return pd.to_numeric(s, errors="coerce").fillna(default)

        def _get(name, default):
            return X[name] if name in X.columns else pd.Series(default, index=X.index)

        # --- core numeric fields ---
        X["tenure"] = _num(_get("tenure", 0), default=0).astype("float64")
        X["MonthlyCharges"] = _num(_get("MonthlyCharges", 0.0), default=0.0).astype("float64")

        if "TotalCharges_num" in X.columns:
            X["TotalCharges_num"] = _num(X["TotalCharges_num"], default=0.0).astype("float64")
        else:
            X["TotalCharges_num"] = _num(_get("TotalCharges", 0.0), default=0.0).astype("float64")

        # --- service flags → services_count ---
        yes_no_map = {
            "Yes": 1,
            "No": 0,
            "No internet service": 0,
            "No phone service": 0,
            True: 1,
            False: 0,
        }

        svc_df = pd.DataFrame(index=X.index)
        for c in self.service_cols:
            col = _get(c, "No").astype(str).str.strip()
            svc_df[c] = col.map(yes_no_map).fillna(0).astype("int64")

        X["services_count"] = svc_df.sum(axis=1).astype("int64")

        # --- derived features ---
        streaming_tv = _get("StreamingTV", "No").astype(str).str.strip()
        streaming_movies = _get("StreamingMovies", "No").astype(str).str.strip()
        X["has_streaming"] = ((streaming_tv == "Yes") | (streaming_movies == "Yes")).astype("int64")

        internet_service = _get("InternetService", "None").astype(str).str.strip()
        X["has_fiber"] = (internet_service == "Fiber optic").astype("int64")

        payment = _get("PaymentMethod", "").astype(str)
        X["is_electronic_check"] = payment.str.contains(
            "Electronic check", case=False, na=False
        ).astype("int64")
        X["auto_pay"] = payment.str.contains("automatic", case=False, na=False).astype("int64")

        contract = _get("Contract", "Month-to-month").astype(str).str.strip()
        contract_map = {"Month-to-month": 1, "One year": 12, "Two year": 24}
        X["contract_term"] = contract.map(contract_map).fillna(1).astype("int64")

        # --- interactions ---
        X["tenure_years"] = (X["tenure"] / 12.0).astype("float64")
        X["charges_per_tenure"] = (X["TotalCharges_num"] / np.maximum(X["tenure"], 1)).astype(
            "float64"
        )
        X["monthly_x_term"] = (X["MonthlyCharges"] * X["contract_term"]).astype("float64")
        X["tenure_x_services"] = (X["tenure"] * X["services_count"]).astype("float64")

        return X

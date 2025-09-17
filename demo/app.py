import json
from typing import Any

import requests
import streamlit as st

# ---------------------------------------------------------
# UI CONFIG
# ---------------------------------------------------------
st.set_page_config(
    page_title="Churn Risk Demo",
    page_icon="📉",
    layout="centered",
)

st.title("📉 Churn Risk Demo UI")
st.caption(
    "Paste your API token, choose or fill features, then click **Score** "
    "to get risk, decision, expected value, and top features."
)


# ---------------------------------------------------------
# HELPERS: API calls
# ---------------------------------------------------------
def api_get(base_url: str, path: str, timeout: int = 15) -> requests.Response:
    url = f"{base_url.rstrip('/')}{path}"
    return requests.get(url, timeout=timeout)


def api_post_score(
    base_url: str, bearer_token: str, features: dict[str, Any], timeout: int = 30
) -> requests.Response:
    url = f"{base_url.rstrip('/')}/score"
    headers = {"Content-Type": "application/json"}
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"
    payload = {"features": features}
    return requests.post(url, headers=headers, json=payload, timeout=timeout)


def api_get_config(base_url: str, timeout: int = 15) -> tuple[float, dict[str, float]]:
    """
    Returns (threshold, costs) from /config.
    If unreachable or malformed, falls back to defaults that match the backend.
    """
    try:
        r = api_get(base_url, "/config", timeout=timeout)
        if r.status_code == 200:
            data = r.json()
            thr = float(data.get("threshold", 0.5))
            costs = data.get("costs", {})
            # Coerce to float & ensure defaults exist
            out_costs = {
                "false_negative": float(costs.get("false_negative", 5.0)),
                "false_positive": float(costs.get("false_positive", 1.0)),
                "true_positive_intervention": float(costs.get("true_positive_intervention", 0.5)),
            }
            return thr, out_costs
    except Exception:
        pass
    # Fallbacks (must mirror backend defaults)
    return 0.5, {
        "false_negative": 5.0,
        "false_positive": 1.0,
        "true_positive_intervention": 0.5,
    }


def api_ping(base_url: str) -> dict[str, Any]:
    try:
        r = api_get(base_url, "/health", timeout=10)
        if r.status_code == 200:
            return r.json()
        return {"status": f"HTTP {r.status_code}"}
    except requests.RequestException as e:
        return {"status": f"error: {e}"}


# ---------------------------------------------------------
# COST-AWARE EV math (mirror of backend logic)
# ---------------------------------------------------------
def ev_if_intervene(p: float, costs: dict[str, float]) -> float:
    """
    EV when we intervene:
      EV = p*(benefit_tp - cost_tp_intervention) + (1-p)*(-cost_fp)
    where benefit_tp approximated as avoided FN cost.
    """
    cost_fn = float(costs.get("false_negative", 5.0))
    cost_fp = float(costs.get("false_positive", 1.0))
    cost_tp_int = float(costs.get("true_positive_intervention", 0.5))
    benefit_tp = cost_fn
    return p * (benefit_tp - cost_tp_int) + (1 - p) * (-cost_fp)


def ev_if_monitor(p: float, costs: dict[str, float]) -> float:
    """
    EV when we skip intervention (monitor):
      EV = p*(-cost_fn) + (1-p)*0
    """
    cost_fn = float(costs.get("false_negative", 5.0))
    return p * (-cost_fn) + (1 - p) * 0.0


# ---------------------------------------------------------
# SIDEBAR: API SETTINGS & SHORTCUTS
# ---------------------------------------------------------
with st.sidebar:
    st.header("API Settings")
    api_url = st.text_input(
        "API Base URL",
        value="http://127.0.0.1:8080",
        help="Your FastAPI server base URL.",
    )
    token = st.text_input(
        "Bearer Token",
        value="",
        type="password",
        help="Paste the HTTP Bearer token (e.g., dev-key-change-me).",
        placeholder="dev-key-change-me",
    )

    st.divider()
    st.subheader("Quick Links")
    swagger_url = f"{api_url.rstrip('/')}/docs"
    metrics_url = f"{api_url.rstrip('/')}/metrics/summary"
    latest_drift_url = f"{api_url.rstrip('/')}/monitoring/latest"

    st.markdown(f"- [Swagger UI]({swagger_url})")
    st.markdown(f"- [Metrics Summary]({metrics_url})")
    st.markdown(f"- [Latest Drift Report]({latest_drift_url})")

    if st.button("🔌 Ping API"):
        res = api_ping(api_url)
        status_text = str(res.get("status", res))
        if status_text in {"ok", "model not loaded"}:
            st.success(f"API reachable: {res}")
        else:
            st.error(f"API not reachable: {res}")

    st.divider()
    st.subheader("Presets")
    preset = st.selectbox(
        "Choose a preset to pre-fill features",
        options=["None", "Low risk (sample)", "High risk (sample)"],
        index=0,
    )

# ---------------------------------------------------------
# PRESET PAYLOADS (MATCHING YOUR API CONTRACT)
# ---------------------------------------------------------
LOW_RISK: dict[str, Any] = {
    "features": {
        "customerID": "9999-LOWWX",
        "gender": "Female",
        "SeniorCitizen": 0,
        "Partner": "Yes",
        "Dependents": "Yes",
        "tenure": 72,
        "PhoneService": "Yes",
        "MultipleLines": "Yes",
        "InternetService": "DSL",
        "OnlineSecurity": "Yes",
        "OnlineBackup": "Yes",
        "DeviceProtection": "Yes",
        "TechSupport": "Yes",
        "StreamingTV": "No",
        "StreamingMovies": "No",
        "Contract": "Two year",
        "PaperlessBilling": "No",
        "PaymentMethod": "Credit card (automatic)",
        "MonthlyCharges": 45.0,
        "TotalCharges": "3240.0",
        "TotalCharges_num": 3240.0,
    }
}

HIGH_RISK: dict[str, Any] = {
    "features": {
        "customerID": "9999-HIGHX",
        "gender": "Male",
        "SeniorCitizen": 0,
        "Partner": "No",
        "Dependents": "No",
        "tenure": 1,
        "PhoneService": "Yes",
        "MultipleLines": "No",
        "InternetService": "Fiber optic",
        "OnlineSecurity": "No",
        "OnlineBackup": "No",
        "DeviceProtection": "No",
        "TechSupport": "No",
        "StreamingTV": "Yes",
        "StreamingMovies": "Yes",
        "Contract": "Month-to-month",
        "PaperlessBilling": "Yes",
        "PaymentMethod": "Electronic check",
        "MonthlyCharges": 95.5,
        "TotalCharges": "95.5",
        "TotalCharges_num": 95.5,
    }
}


def pick_initial_features(preset_name: str) -> dict[str, Any]:
    if preset_name == "Low risk (sample)":
        return LOW_RISK["features"].copy()
    if preset_name == "High risk (sample)":
        return HIGH_RISK["features"].copy()
    # Sensible defaults
    return {
        "customerID": "",
        "gender": "Female",
        "SeniorCitizen": 0,
        "Partner": "No",
        "Dependents": "No",
        "tenure": 1,
        "PhoneService": "Yes",
        "MultipleLines": "No",
        "InternetService": "DSL",
        "OnlineSecurity": "No",
        "OnlineBackup": "No",
        "DeviceProtection": "No",
        "TechSupport": "No",
        "StreamingTV": "No",
        "StreamingMovies": "No",
        "Contract": "Month-to-month",
        "PaperlessBilling": "Yes",
        "PaymentMethod": "Electronic check",
        "MonthlyCharges": 50.0,
        "TotalCharges": "50.0",
        "TotalCharges_num": 50.0,
    }


features_state = pick_initial_features(preset)

# ---------------------------------------------------------
# INPUT FORM
# ---------------------------------------------------------
with st.form("score_form"):
    st.subheader("Customer Features")

    # HELP: short, simple explanations
    with st.expander("What does each field mean?"):
        st.markdown(
            """
**Customer Features (input)**
- **customerID** – your internal ID for the customer.
- **gender** – Male/Female.
- **SeniorCitizen** – 1 if senior, 0 otherwise.
- **Partner / Dependents** – family status flags (Yes/No).
- **tenure** – months with the company.
- **PhoneService / MultipleLines** – phone plan and extra line (Yes/No).
- **InternetService** – DSL, Fiber optic, or No.
- **OnlineSecurity / OnlineBackup / DeviceProtection / TechSupport** – add-on services (Yes/No).
- **StreamingTV / StreamingMovies** – streaming add-ons (Yes/No).
- **Contract** – Month-to-month / One year / Two year.
- **PaperlessBilling** – Yes/No.
- **PaymentMethod** – how they pay (check/bank/credit).
- **MonthlyCharges** – their monthly bill.
- **TotalCharges / TotalCharges_num** – total paid so far.

**Score (output)**
- **probability** – chance (0–1) the customer will churn.
- **decision** – what to do now: *intervene* (act) or *monitor* (wait).
- **expected_value** – cost/benefit of that decision.
- **action** – the recommended action text.

**Top Features**
- Most influential features that drove the decision (a quick explanation).

**Raw response**
- The exact JSON returned by the API (good for debugging or reuse).
"""
        )

    col_a, col_b = st.columns(2)
    with col_a:
        customer_id = st.text_input("customerID", value=features_state["customerID"])
        gender = st.selectbox(
            "gender",
            options=["Female", "Male"],
            index=0 if features_state["gender"] == "Female" else 1,
        )
        senior = st.selectbox(
            "SeniorCitizen (0/1)", options=[0, 1], index=features_state["SeniorCitizen"]
        )
        partner = st.selectbox(
            "Partner", options=["Yes", "No"], index=0 if features_state["Partner"] == "Yes" else 1
        )
        dependents = st.selectbox(
            "Dependents",
            options=["Yes", "No"],
            index=0 if features_state["Dependents"] == "Yes" else 1,
        )
        tenure = st.number_input(
            "tenure (months)",
            min_value=0,
            max_value=120,
            value=int(features_state["tenure"]),
            step=1,
        )
        phone = st.selectbox(
            "PhoneService",
            options=["Yes", "No"],
            index=0 if features_state["PhoneService"] == "Yes" else 1,
        )
        multiline = st.selectbox(
            "MultipleLines",
            options=["Yes", "No"],
            index=0 if features_state["MultipleLines"] == "Yes" else 1,
        )
        internet = st.selectbox(
            "InternetService",
            options=["DSL", "Fiber optic", "No"],
            index=["DSL", "Fiber optic", "No"].index(features_state["InternetService"]),
        )

    with col_b:
        onsec = st.selectbox(
            "OnlineSecurity",
            options=["Yes", "No"],
            index=0 if features_state["OnlineSecurity"] == "Yes" else 1,
        )
        onbackup = st.selectbox(
            "OnlineBackup",
            options=["Yes", "No"],
            index=0 if features_state["OnlineBackup"] == "Yes" else 1,
        )
        deviceprot = st.selectbox(
            "DeviceProtection",
            options=["Yes", "No"],
            index=0 if features_state["DeviceProtection"] == "Yes" else 1,
        )
        techsup = st.selectbox(
            "TechSupport",
            options=["Yes", "No"],
            index=0 if features_state["TechSupport"] == "Yes" else 1,
        )
        streamtv = st.selectbox(
            "StreamingTV",
            options=["Yes", "No"],
            index=0 if features_state["StreamingTV"] == "Yes" else 1,
        )
        streammv = st.selectbox(
            "StreamingMovies",
            options=["Yes", "No"],
            index=0 if features_state["StreamingMovies"] == "Yes" else 1,
        )
        contract = st.selectbox(
            "Contract",
            options=["Month-to-month", "One year", "Two year"],
            index=["Month-to-month", "One year", "Two year"].index(features_state["Contract"]),
        )
        paperless = st.selectbox(
            "PaperlessBilling",
            options=["Yes", "No"],
            index=0 if features_state["PaperlessBilling"] == "Yes" else 1,
        )
        payment = st.selectbox(
            "PaymentMethod",
            options=[
                "Electronic check",
                "Mailed check",
                "Bank transfer (automatic)",
                "Credit card (automatic)",
            ],
            index=[
                "Electronic check",
                "Mailed check",
                "Bank transfer (automatic)",
                "Credit card (automatic)",
            ].index(features_state["PaymentMethod"]),
        )

    col_c, col_d = st.columns(2)
    with col_c:
        monthly = st.number_input(
            "MonthlyCharges",
            min_value=0.0,
            max_value=1000.0,
            value=float(features_state["MonthlyCharges"]),
            step=0.5,
        )
    with col_d:
        total_num = st.number_input(
            "TotalCharges_num",
            min_value=0.0,
            max_value=100000.0,
            value=float(features_state["TotalCharges_num"]),
            step=1.0,
        )

    total_str = st.text_input("TotalCharges (string)", value=str(total_num))

    submitted = st.form_submit_button("Score 🔮")

st.divider()

# ---------------------------------------------------------
# HANDLE SUBMIT
# ---------------------------------------------------------
if submitted:
    if not token:
        st.error("Please paste your HTTP Bearer token in the sidebar.")
        st.stop()

    features_payload = {
        "customerID": customer_id.strip(),
        "gender": gender,
        "SeniorCitizen": int(senior),
        "Partner": partner,
        "Dependents": dependents,
        "tenure": int(tenure),
        "PhoneService": phone,
        "MultipleLines": multiline,
        "InternetService": internet,
        "OnlineSecurity": onsec,
        "OnlineBackup": onbackup,
        "DeviceProtection": deviceprot,
        "TechSupport": techsup,
        "StreamingTV": streamtv,
        "StreamingMovies": streammv,
        "Contract": contract,
        "PaperlessBilling": paperless,
        "PaymentMethod": payment,
        "MonthlyCharges": float(monthly),
        "TotalCharges": str(total_str),
        "TotalCharges_num": float(total_num),
    }

    with st.spinner("Scoring…"):
        try:
            resp = api_post_score(api_url, token, features_payload)
        except requests.RequestException as e:
            st.error(f"Request failed: {e}")
            st.stop()

    if resp.status_code != 200:
        st.error(f"API returned {resp.status_code}")
        try:
            st.code(resp.json())
        except Exception:
            st.code(resp.text)
        st.stop()

    # Parse response
    try:
        data = resp.json()
    except Exception:
        st.error("Could not parse JSON response.")
        st.code(resp.text)
        st.stop()

    st.success("Scored successfully!")

    # KPIs
    kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
    prob = data.get("probability", None)
    decision = data.get("decision", None)
    expected_value = data.get("expected_value", None)
    action = data.get("action")

    if isinstance(prob, int | float):
        kpi_col1.metric("Probability", f"{prob*100:.1f}%")
    else:
        kpi_col1.metric("Probability", "N/A")

    kpi_col2.metric("Decision", str(decision))
    if isinstance(expected_value, int | float):
        kpi_col3.metric("Expected Value", f"{expected_value:.2f}")
    else:
        kpi_col3.metric("Expected Value", "N/A")

    if action:
        st.info(f"Recommended Action: **{action}**")

    # Top Features (support list[str] or list[dict])
    top_feats: list[dict[str, Any]] | None = data.get("top_features")  # type: ignore
    st.subheader("Top Features")
    if isinstance(top_feats, list) and top_feats:
        if all(isinstance(x, str) for x in top_feats):
            st.dataframe([{"feature": x} for x in top_feats], use_container_width=True)
        else:
            st.dataframe(top_feats, use_container_width=True)
    else:
        st.caption("No top features returned.")

    # EV Comparison (recompute both options using backend /config)
    st.subheader("Expected Value: Intervene vs Monitor")
    thr, costs = api_get_config(api_url)
    if isinstance(prob, int | float):
        ev_intervene = ev_if_intervene(prob, costs)
        ev_monitor = ev_if_monitor(prob, costs)

        # Display numbers and a small chart
        c1, c2 = st.columns(2)
        c1.metric("EV if Intervene", f"{ev_intervene:.2f}")
        c2.metric("EV if Monitor", f"{ev_monitor:.2f}")

        # Bar chart
        st.bar_chart({"EV": {"Intervene": ev_intervene, "Monitor": ev_monitor}})

        # Quick explanation
        st.caption(
            "Positive EV means the decision is beneficial on average. "
            "Values are computed from the churn probability "
            "and the cost settings in `/config`."
        )
    else:
        st.caption("EV comparison unavailable (invalid probability).")

    # Raw JSON
    with st.expander("Raw response (exact API JSON)"):
        st.code(json.dumps(data, indent=2))

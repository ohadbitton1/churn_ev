from fastapi.testclient import TestClient

from api.main import API_KEY, app

client = TestClient(app)


def auth_header():
    return {"Authorization": f"Bearer {API_KEY}"}


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert "status" in resp.json()


def test_version():
    resp = client.get("/version")
    assert resp.status_code == 200
    body = resp.json()
    assert "service_version" in body
    assert "threshold" in body


def test_score_low_stub():
    payload = {
        "features": {
            "customerID": "TEST-123",
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
    resp = client.post("/score", json=payload, headers=auth_header())
    assert resp.status_code == 200
    body = resp.json()
    for key in ["probability", "decision", "expected_value", "action", "top_features"]:
        assert key in body

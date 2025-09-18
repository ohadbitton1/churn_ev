# 📉 Churn Early-Warning System

[![CI](https://github.com/ohadbitton1/churn_ev/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/ohadbitton1/churn_ev/actions/workflows/ci.yml)

End-to-end churn risk predictor with a **cost-aware decision layer**, **FastAPI API**, **monitoring & metrics**, and a **Streamlit demo UI**.

---

## 📦 What’s inside
- **Model & decisions**: churn probability + expected-value logic using a cost matrix.  
- **FastAPI service**: secure scoring endpoints, monitoring routes, metrics summary.  
- **Monitoring**: Evidently drift reports, CSV middleware metrics.  
- **Demo UI**: Streamlit app with EV comparison.  
- **Quality**: tests, pre-commit hooks (black, isort, ruff, mypy).  

---

## ⚙️ Setup (Windows / PowerShell)
```powershell
# (Optional) activate your venv
# .\.venv\Scripts\Activate.ps1

python -m pip install -r requirements.txt
````

---

## 🚀 Run the API (local)

Start the backend:

```powershell
python -m uvicorn api.main:app --reload --port 8080
```

* Swagger UI: [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs)
* Authorization: click **Authorize**, paste token:

  ```
  dev-key-change-me
  ```

  *(no “Bearer ” prefix needed)*

**Core endpoints**

* `GET /health` – service status
* `GET /version` – model metadata
* `GET /config` – threshold + costs
* `POST /score` *(secured)* – single scoring result
* `POST /score/batch` *(secured)* – list of scoring results
* `GET /metrics/summary` – counts, errors, p95 latency

**Monitoring routes**

* `GET /monitoring/list` – all drift reports
* `GET /monitoring/latest` – newest report (JSON)
* `GET /monitoring/latest/redirect` – open newest report HTML

---

## 🐳 Run with Docker

The easiest way to package and run in production.

1. Build image:

```powershell
docker build -t churn-ev:latest .
```

2. Run in one line (maps port 8080):

```powershell
docker run --rm -p 8080:8080 -e API_KEY=dev-key-change-me churn-ev:latest
```

3. (Optional) Persist drift reports to host machine:

```powershell
docker run --rm -p 8080:8080 `
  -e API_KEY=dev-key-change-me `
  -v "${PWD}/monitoring/reports:/app/monitoring/reports" `
  churn-ev:latest
```

Quick checks:

* Swagger: [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs)
* Metrics: [http://127.0.0.1:8080/metrics/summary](http://127.0.0.1:8080/metrics/summary)
* Drift report: [http://127.0.0.1:8080/monitoring/latest/redirect](http://127.0.0.1:8080/monitoring/latest/redirect)

---

## 🖥️ Demo UI (Streamlit)

A small Streamlit app for trying the system interactively.

Run:

```powershell
python -m streamlit run demo/app.py --server.headless true --server.port 8501
```

Open [http://127.0.0.1:8501](http://127.0.0.1:8501) and in the sidebar:

* **API Base URL** → `http://127.0.0.1:8080`
* **Bearer Token** → `dev-key-change-me`
* **Presets** → choose *Low risk* or *High risk*

Click **Score** → you’ll see:

* Probability (risk %)
* Decision (intervene / monitor)
* Expected Value (average benefit of chosen action)
* Recommended Action
* Top Features (most influential features)
* **EV comparison chart**: Intervene vs Monitor

---

## 📊 Monitoring & Metrics

* Generate drift manually:

  ```powershell
  python monitoring/run_drift.py
  ```

* Automated drift (keep 20 reports):

  ```powershell
  python scripts/auto_drift.py --reference data/reference.csv --current data/current.csv --keep 20
  ```

* Quick links while API is running:

  * Metrics: [http://127.0.0.1:8080/metrics/summary](http://127.0.0.1:8080/metrics/summary)
  * Latest drift report: [http://127.0.0.1:8080/monitoring/latest/redirect](http://127.0.0.1:8080/monitoring/latest/redirect)

Every request is logged in `monitoring/metrics.csv` with:

```
timestamp, method, path, status, duration_ms
```

---

## 🧪 Example Payloads

**Low risk**

```json
{ "features": { "customerID": "9999-LOWWX", "tenure": 72, "Contract": "Two year", "MonthlyCharges": 45.0, "TotalCharges_num": 3240.0, "...": "..." } }
```

**High risk**

```json
{ "features": { "customerID": "9999-HIGHX", "tenure": 1, "Contract": "Month-to-month", "MonthlyCharges": 95.5, "TotalCharges_num": 95.5, "...": "..." } }
```

---

## 🧷 Curl examples

**Score one**

```powershell
$TOKEN="dev-key-change-me"
curl -X POST "http://127.0.0.1:8080/score" ^
  -H "Authorization: Bearer $TOKEN" ^
  -H "Content-Type: application/json" ^
  -d "@data\score_high.json"
```

**Batch**

```powershell
$TOKEN="dev-key-change-me"
curl -X POST "http://127.0.0.1:8080/score/batch" ^
  -H "Authorization: Bearer $TOKEN" ^
  -H "Content-Type: application/json" ^
  -d "{\"items\": [$(Get-Content data\score_low.json -Raw), $(Get-Content data\score_high.json -Raw)]}"
```

**Metrics**

```powershell
curl "http://127.0.0.1:8080/metrics/summary"
```

**Open latest drift**

```powershell
start http://127.0.0.1:8080/monitoring/latest/redirect
```

---

## 🧮 Expected Value (EV)

* EV = **“On average, is this decision worth it?”**
* Default costs:

  * False Negative (miss churn): 5.0
  * False Positive (unneeded offer): 1.0
  * Intervention cost (true positive): 0.5
* If **intervene**: `EV = p*(5.0-0.5) + (1-p)*(-1.0)`
* If **monitor**: `EV = p*(-5.0)`

The demo app shows **both EVs** side by side.

---

## 🧪 Tests & Quality

```powershell
pytest
pre-commit run -a
```

---

## 🛠 Troubleshooting

* **UI fails with `streamlit`** → use module form:

  ```powershell
  python -m streamlit run demo/app.py --server.port 8501
  ```

* **401 Unauthorized** → paste token in Swagger + sidebar.

* **API not reachable** → check API log; test `http://127.0.0.1:8080/health`.

* **Model not loaded** → confirm `models/best_pipeline.pkl` exists.

---

## Demo Screenshots

### Main UI
![Main UI](docs/screenshot_ui.png)

### Example result (Low-risk customer)
![Low Risk Result](docs/screenshot_low.png)

### Monitoring Drift Report
![Drift Report](docs/screenshot_drift.png)

### Decision Curve
![Decision Curve](artifacts/decisions/decision_curve.png)


import os

from fastapi import FastAPI

app = FastAPI(title="Churn Early Warning", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/version")
def version():
    return {"version": os.getenv("APP_VERSION", "0.1.0")}

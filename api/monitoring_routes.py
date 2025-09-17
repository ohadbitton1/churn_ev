# api/monitoring_routes.py
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

# Folder that holds the HTML drift reports
BASE_DIR = Path(__file__).resolve().parents[1]
REPORTS_DIR = BASE_DIR / "monitoring" / "reports"

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


def _list_reports() -> list[Path]:
    """List HTML reports in reports dir, newest first."""
    if not REPORTS_DIR.exists():
        return []
    # Prefer drift-named files; if none, fall back to any HTML
    drift = sorted(REPORTS_DIR.glob("*-drift.html"), key=lambda p: p.stat().st_mtime, reverse=True)
    if drift:
        return drift
    any_html = sorted(REPORTS_DIR.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True)
    return any_html


def _latest_report() -> Path | None:
    reports = _list_reports()
    return reports[0] if reports else None


@router.get("/list", summary="List available monitoring HTML reports (newest first)")
def list_reports():
    files = _list_reports()
    return {
        "reports_dir": str(REPORTS_DIR),
        "count": len(files),
        "files": [f.name for f in files],
        "urls": [f"/monitoring/reports/{f.name}" for f in files],
    }


@router.get("/latest", summary="Get latest drift report file name")
def get_latest_report():
    """
    Returns JSON with the latest report relative URL and absolute path.
    Falls back to any *.html if no '*-drift.html' is present.
    """
    path = _latest_report()
    if path is None:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "No reports found.",
                "reports_dir": str(REPORTS_DIR),
                "hint": "Generate one with: python monitoring/run_drift.py",
            },
        )
    relative_url = f"/monitoring/reports/{path.name}"  # under the StaticFiles mount in main.py
    return {"relative_url": relative_url, "abs_path": str(path)}


@router.get("/latest/redirect", summary="Redirect to latest drift report (HTML)")
def redirect_to_latest():
    """
    HTTP redirect to the latest report so you can open it in the browser directly.
    """
    path = _latest_report()
    if path is None:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "No reports found.",
                "reports_dir": str(REPORTS_DIR),
                "hint": "Generate one with: python monitoring/run_drift.py",
            },
        )
    return RedirectResponse(url=f"/monitoring/reports/{path.name}")

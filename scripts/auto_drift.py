# scripts/auto_drift.py
"""
Run the Evidently drift job and keep only the last N reports.

Usage (from repo root):
  python scripts/auto_drift.py --reference data/reference.csv --current data/current.csv --keep 20
  # Optional: also append logs to a file (ASCII-safe messages):
  #   python scripts/auto_drift.py ... --log monitoring/auto_drift.log

What it does:
  1) Calls monitoring/run_drift.py to generate a new HTML report.
  2) Prints the full path of the new report.
  3) (Optional) Prunes old reports, keeping only the latest --keep files.
Notes:
  - All messages are ASCII only (no special symbols) to avoid Windows encoding issues.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def reports_dir() -> Path:
    return repo_root() / "monitoring" / "reports"


def _write_log(msg: str, log_path: Path | None) -> None:
    """Write a line to stdout and optionally append to a logfile (ASCII)."""
    # Ensure ASCII-only output to avoid UnicodeEncodeError on Windows consoles
    safe = msg.encode("ascii", "replace").decode("ascii")
    print(safe)
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="ascii", errors="replace") as f:
            f.write(safe + "\n")


def run_drift(reference: Path, current: Path) -> Path:
    """Invoke monitoring/run_drift.py and return the created report path."""
    script = repo_root() / "monitoring" / "run_drift.py"
    if not script.exists():
        raise SystemExit(f"[ERROR] Missing script: {script}")

    cmd = [
        sys.executable,
        str(script),
        "--reference",
        str(reference),
        "--current",
        str(current),
    ]
    # Capture stdout: run_drift.py prints the HTML path on success
    res = subprocess.run(cmd, check=True, text=True, capture_output=True)
    out = (res.stdout or "").strip()
    if not out:
        raise SystemExit("[ERROR] Drift script produced no output.")
    path = Path(out)
    if not path.exists():
        # stdout may be relative; try resolving under reports_dir
        candidate = reports_dir() / path.name
        if candidate.exists():
            return candidate
        raise SystemExit(f"[ERROR] Report not found at: {path}")
    return path


def list_reports() -> list[Path]:
    """Return all HTML reports, newest first."""
    rd = reports_dir()
    if not rd.exists():
        return []
    files = sorted(rd.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files


def prune_reports(keep: int) -> int:
    """Delete older reports, keeping only the latest `keep` files. Returns count deleted."""
    if keep < 0:
        return 0
    files = list_reports()
    if len(files) <= keep:
        return 0
    to_delete = files[keep:]
    deleted = 0
    for f in to_delete:
        try:
            f.unlink(missing_ok=True)
            deleted += 1
        except Exception:
            # Best-effort pruning; ignore individual failures
            pass
    return deleted


def main() -> None:
    r = repo_root()
    parser = argparse.ArgumentParser(description="Automate drift report generation and pruning.")
    parser.add_argument(
        "--reference", type=Path, default=r / "data" / "reference.csv", help="Reference CSV path."
    )
    parser.add_argument(
        "--current", type=Path, default=r / "data" / "current.csv", help="Current CSV path."
    )
    parser.add_argument(
        "--keep", type=int, default=20, help="How many latest reports to keep (default: 20)."
    )
    parser.add_argument("--no-prune", action="store_true", help="Do not delete old reports.")
    parser.add_argument(
        "--log", type=Path, default=None, help="Append ASCII logs to this file (optional)."
    )
    args = parser.parse_args()

    log_path: Path | None = args.log

    _write_log(f"[INFO] Start at {datetime.now().isoformat(timespec='seconds')}", log_path)

    # Ensure expected directories exist
    reports_dir().mkdir(parents=True, exist_ok=True)

    if not args.reference.exists() or not args.current.exists():
        raise SystemExit(
            "[ERROR] Missing input CSVs.\n"
            f"  reference: {args.reference}\n"
            f"  current:   {args.current}\n"
            "Hint: create them with scripts/split_telco.py or pass explicit paths."
        )

    report_path = run_drift(args.reference, args.current)
    _write_log(f"[OK] New drift report: {report_path.as_posix()}", log_path)

    if not args.no_prune:
        deleted = prune_reports(args.keep)
        if deleted:
            _write_log(
                f"[OK] Pruned {deleted} old report(s); keeping {args.keep} latest.", log_path
            )
        else:
            _write_log(
                f"[OK] No pruning needed; {len(list_reports())} report(s) <= keep={args.keep}.",
                log_path,
            )

    _write_log("[INFO] Done.", log_path)


if __name__ == "__main__":
    main()

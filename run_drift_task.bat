@echo off
python "%~dp0scripts\auto_drift.py" --reference "%~dp0data\reference.csv" --current "%~dp0data\current.csv" --keep 20

# Churn Early-Warning System

מערכת התראה מוקדמת לנטישת לקוחות (Churn).

## מבנה תיקיות
- `data/` – דאטה (raw, interim, processed)
- `notebooks/` – נוטבוקים לאקספלורציה
- `src/` – קוד ייצור (data, features, models, utils)
- `api/` – שירות FastAPI
- `tests/` – בדיקות
- `monitoring/` – סקריפטים ודוחות Evidently
- `infra/` – Docker, CI/CD, configs

## פיתוח
1. הפעלת סביבה:
   ```bash
   conda activate churn-env

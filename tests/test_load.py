import pathlib
import sys

import joblib

project_root = pathlib.Path(__file__).resolve().parents[1]

# חשוב: להוסיף גם את שורש הפרויקט וגם את src ל-PYTHONPATH
sys.path.extend([str(project_root), str(project_root / "src")])

# נסה קודם את הייבוא ה"רגיל" שלנו
try:
    from features.build_features import AddFeatures  # noqa: F401
except ModuleNotFoundError:
    # אם המודל נשמר עם שמות מלאים של 'src.features...', נוודא שגם זה זמין
    from src.features.build_features import AddFeatures  # noqa: F401

m = joblib.load(str(project_root / "models" / "best_pipeline.pkl"))
print("Loaded OK:", type(m))

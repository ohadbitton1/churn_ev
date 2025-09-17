import os

import pandas as pd

src = r"data/raw/telco_churn.csv"
df = pd.read_csv(src)

# Add numeric column if missing
if "TotalCharges_num" not in df.columns and "TotalCharges" in df.columns:
    df["TotalCharges_num"] = pd.to_numeric(df["TotalCharges"], errors="coerce")

# Shuffle and split 80/20
df = df.sample(frac=1.0, random_state=42).reset_index(drop=True)
cut = int(len(df) * 0.8)
ref, cur = df.iloc[:cut].copy(), df.iloc[cut:].copy()

os.makedirs("data", exist_ok=True)
ref.to_csv("data/reference.csv", index=False)
cur.to_csv("data/current.csv", index=False)

print("Wrote: data/reference.csv and data/current.csv")

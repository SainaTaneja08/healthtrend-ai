"""FDSA part: cleaning -> EDA -> model training -> evaluation -> save artefacts."""
import json, joblib
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

FEATURES = ["age","sex","cp","trestbps","chol","fbs","restecg","thalach","exang","oldpeak","slope","ca","thal"]

# 1. LOAD + CLEAN ------------------------------------------------------------
df = pd.read_csv("data/heart.csv", encoding="utf-8-sig")
print("Shape:", df.shape)
print("Missing values:\n", df.isna().sum().sum())
before = len(df)
df = df.drop_duplicates().reset_index(drop=True)
print(f"Removed {before-len(df)} duplicate row(s); {len(df)} rows left")
print(df.describe().round(2))

# 2. EDA ---------------------------------------------------------------------
corr = df.corr()
fig, ax = plt.subplots(figsize=(7, 6))
im = ax.imshow(corr, cmap="coolwarm", vmin=-1, vmax=1)
ax.set_xticks(range(len(corr))); ax.set_xticklabels(corr.columns, rotation=90)
ax.set_yticks(range(len(corr))); ax.set_yticklabels(corr.columns)
fig.colorbar(im); ax.set_title("Correlation heatmap"); fig.tight_layout()
fig.savefig("static/heatmap.png", dpi=110); plt.close(fig)

# 3. MODELS ------------------------------------------------------------------
X, y = df[FEATURES], df["target"]
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
models = {
    "Logistic Regression": Pipeline([("sc", StandardScaler()), ("m", LogisticRegression(max_iter=1000))]),
    "Random Forest": Pipeline([("sc", StandardScaler()), ("m", RandomForestClassifier(n_estimators=200, random_state=42))]),
}
results, best_name, best_f1 = {}, None, -1
for name, pipe in models.items():
    pipe.fit(Xtr, ytr); p = pipe.predict(Xte)
    r = {"accuracy": accuracy_score(yte, p), "precision": precision_score(yte, p),
         "recall": recall_score(yte, p), "f1": f1_score(yte, p),
         "cv_accuracy": cross_val_score(pipe, X, y, cv=5).mean(),
         "confusion_matrix": confusion_matrix(yte, p).tolist()}
    results[name] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}
    print(name, results[name])
    if r["f1"] > best_f1: best_name, best_f1 = name, r["f1"]
print("Best model:", best_name)
best = models[best_name]
joblib.dump(best, "model/model.joblib")

# feature importance (RF) or |coef| (LR)
m = best.named_steps["m"]
imp = m.feature_importances_ if hasattr(m, "feature_importances_") else np.abs(m.coef_[0])
imp = (imp / imp.sum()).round(3)

# 4. STATS FOR DASHBOARD -----------------------------------------------------
bins = list(range(25, 85, 10))
labels = [f"{b}-{b+9}" for b in bins[:-1]]
df["age_band"] = pd.cut(df["age"], bins=bins, labels=labels, right=False)
ab = df.groupby(["age_band", "target"], observed=False).size().unstack(fill_value=0)
stats = {
    "rows": int(len(df)), "features": len(FEATURES), "best_model": best_name,
    "target_counts": df["target"].value_counts().sort_index().tolist(),
    "age_labels": labels, "age_t0": ab[0].tolist(), "age_t1": ab[1].tolist(),
    "mean_by_target": df.groupby("target")[["age","trestbps","chol","thalach"]].mean().round(1).to_dict(),
    "importance": dict(zip(FEATURES, imp.tolist())),
    "models": results,
}
json.dump(stats, open("model/stats.json", "w"), indent=2)
print("Saved model/model.joblib, model/stats.json, static/heatmap.png")

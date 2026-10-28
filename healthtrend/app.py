"""Flask app: website + REST API (IDCCN) deployed on cloud (Cloud Computing)."""
import json, joblib
import pandas as pd
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
MODEL = joblib.load("model/model.joblib")
STATS = json.load(open("model/stats.json"))

# name: (label, min, max, options or None)
FIELDS = {
    "age": ("Age (years)", 1, 120, None),
    "sex": ("Sex", 0, 1, {0: "Female", 1: "Male"}),
    "cp": ("Chest pain type", 0, 3, {0: "Typical angina", 1: "Atypical angina", 2: "Non-anginal", 3: "Asymptomatic"}),
    "trestbps": ("Resting blood pressure (mm Hg)", 80, 220, None),
    "chol": ("Cholesterol (mg/dl)", 100, 600, None),
    "fbs": ("Fasting blood sugar > 120 mg/dl", 0, 1, {0: "No", 1: "Yes"}),
    "restecg": ("Resting ECG", 0, 2, {0: "Normal", 1: "ST-T abnormality", 2: "LV hypertrophy"}),
    "thalach": ("Max heart rate achieved", 60, 220, None),
    "exang": ("Exercise-induced angina", 0, 1, {0: "No", 1: "Yes"}),
    "oldpeak": ("ST depression (oldpeak)", 0, 7, None),
    "slope": ("Slope of peak exercise ST", 0, 2, {0: "Upsloping", 1: "Flat", 2: "Downsloping"}),
    "ca": ("Major vessels coloured (0-4)", 0, 4, None),
    "thal": ("Thalassemia (0-3)", 0, 3, {0: "Null", 1: "Fixed defect", 2: "Normal", 3: "Reversible defect"}),
}

def validate(data):
    """Return (clean_values, error_message, http_status)."""
    missing = [k for k in FIELDS if data.get(k) in (None, "")]
    if missing:
        return None, f"Missing fields: {', '.join(missing)}", 400
    clean = {}
    for k, (label, lo, hi, opts) in FIELDS.items():
        try:
            v = float(data[k])
        except (TypeError, ValueError):
            return None, f"Invalid value for {k}: must be a number", 422
        if not lo <= v <= hi:
            return None, f"{k} must be between {lo} and {hi}", 422
        clean[k] = v
    return clean, None, 200

def predict(clean):
    row = pd.DataFrame([clean])[list(FIELDS)]
    prob = float(MODEL.predict_proba(row)[0][1])
    level = "High" if prob >= 0.7 else "Moderate" if prob >= 0.4 else "Low"
    return {"prediction": int(prob >= 0.5), "probability": round(prob, 3), "risk_level": level}

@app.route("/")
def home():
    return render_template("index.html", s=STATS)

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html", s=STATS)

@app.route("/predict", methods=["GET", "POST"])
def predict_page():
    result = error = None
    if request.method == "POST":
        clean, error, _ = validate(request.form)
        if not error:
            result = predict(clean)
    return render_template("predict.html", fields=FIELDS, result=result, error=error, form=request.form)

# ---- REST API (used by tests/test_api.py) ----
@app.route("/api/predict", methods=["POST"])
def api_predict():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Request body must be JSON"), 400
    clean, error, status = validate(data)
    if error:
        return jsonify(error=error), status
    return jsonify(predict(clean)), 200

@app.route("/api/stats")
def api_stats():
    return jsonify(STATS)

@app.route("/health")
def health():
    return jsonify(status="ok", model=STATS["best_model"])

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("DEBUG") == "1")

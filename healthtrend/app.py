"""HealthTrend AI v2: dashboard, prediction + explanation, history (SQLite), PDF report, REST API."""
import io, json, os, sqlite3
from datetime import datetime
import joblib, pandas as pd
from flask import Flask, render_template, request, jsonify, send_file, abort

app = Flask(__name__)
MODEL = joblib.load("model/model.joblib")
STATS = json.load(open("model/stats.json"))
DB = os.environ.get("DB_PATH", "history.db")

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

# "Typical patient" baseline used to explain predictions (median for numbers, most common value for categories)
_df = pd.read_csv("data/heart.csv", encoding="utf-8-sig").drop_duplicates()
NUMERIC = ["age", "trestbps", "chol", "thalach", "oldpeak"]
BASELINE = {k: float(_df[k].median()) if k in NUMERIC else float(_df[k].mode()[0]) for k in FIELDS}

# ---------- database (prediction history) ----------
def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, inputs TEXT,
            probability REAL, risk_level TEXT, factors TEXT, source TEXT)""")
init_db()

# ---------- helpers ----------
def validate(data):
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

def show(k, v):
    opts = FIELDS[k][3]
    return opts.get(int(v), str(v)) if opts else f"{v:g}"

def proba(row):
    return float(MODEL.predict_proba(pd.DataFrame([row])[list(FIELDS)])[0][1])

def explain(clean, p):
    """What-if: how much does each input push the result vs a typical patient?"""
    out = []
    for k in FIELDS:
        alt = dict(clean); alt[k] = BASELINE[k]
        out.append({"feature": k, "label": FIELDS[k][0], "value": show(k, clean[k]),
                    "effect": round(p - proba(alt), 3)})
    out.sort(key=lambda d: abs(d["effect"]), reverse=True)
    return out[:5]

def run_prediction(clean, source):
    p = proba(clean)
    level = "High" if p >= 0.7 else "Moderate" if p >= 0.4 else "Low"
    factors = explain(clean, p)
    with db() as con:
        cur = con.execute("INSERT INTO predictions (ts, inputs, probability, risk_level, factors, source) VALUES (?,?,?,?,?,?)",
                          (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), json.dumps(clean), round(p, 3), level, json.dumps(factors), source))
        pid = cur.lastrowid
    return {"id": pid, "prediction": int(p >= 0.5), "probability": round(p, 3), "risk_level": level, "top_factors": factors}

# ---------- pages ----------
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
            result = run_prediction(clean, "web form")
    return render_template("predict.html", fields=FIELDS, result=result, error=error, form=request.form)

@app.route("/history")
def history():
    with db() as con:
        rows = con.execute("SELECT * FROM predictions ORDER BY id DESC LIMIT 25").fetchall()
        total = con.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
    items = []
    for r in rows:
        inp = json.loads(r["inputs"])
        items.append({"id": r["id"], "ts": r["ts"], "level": r["risk_level"], "prob": round(r["probability"] * 100, 1),
                      "age": int(inp["age"]), "sex": show("sex", inp["sex"]), "chol": inp["chol"], "source": r["source"]})
    return render_template("history.html", items=items, total=total)

@app.route("/report/<int:pid>.pdf")
def report_pdf(pid):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    with db() as con:
        r = con.execute("SELECT * FROM predictions WHERE id=?", (pid,)).fetchone()
    if r is None:
        abort(404)
    inputs, factors = json.loads(r["inputs"]), json.loads(r["factors"])
    st = getSampleStyleSheet()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=f"HealthTrend AI report #{pid}")
    grid = TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b5c8a")),
                       ("TEXTCOLOR", (0, 0), (-1, 0), colors.white)])
    el = [Paragraph("HealthTrend AI: Risk Report", st["Title"]),
          Paragraph(f"Report #{pid} | {r['ts']}", st["Normal"]), Spacer(1, 12),
          Paragraph(f"<b>Risk level: {r['risk_level']}</b> (model probability {r['probability'] * 100:.1f}%)", st["Heading2"]),
          Paragraph("Main factors compared with a typical patient", st["Heading3"])]
    ft = [["Input", "Your value", "Effect on risk"]] + [[f["label"], f["value"], f"{f['effect'] * 100:+.1f} points"] for f in factors]
    t = Table(ft, colWidths=[200, 120, 120]); t.setStyle(grid); el += [t, Spacer(1, 12), Paragraph("All inputs", st["Heading3"])]
    it = [["Input", "Value"]] + [[FIELDS[k][0], show(k, v)] for k, v in inputs.items()]
    t2 = Table(it, colWidths=[260, 180]); t2.setStyle(grid); el += [t2, Spacer(1, 16),
          Paragraph("<i>Educational prototype only. Not a medical diagnostic tool. Do not use for real medical decisions.</i>", st["Normal"])]
    doc.build(el); buf.seek(0)
    return send_file(buf, mimetype="application/pdf", download_name=f"healthtrend_report_{pid}.pdf")

# ---------- REST API ----------
@app.route("/api/predict", methods=["POST"])
def api_predict():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Request body must be JSON"), 400
    clean, error, status = validate(data)
    if error:
        return jsonify(error=error), status
    return jsonify(run_prediction(clean, "api")), 200

@app.route("/api/history")
def api_history():
    with db() as con:
        rows = con.execute("SELECT id, ts, probability, risk_level, source FROM predictions ORDER BY id DESC LIMIT 25").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/stats")
def api_stats():
    return jsonify(STATS)

@app.route("/health")
def health():
    return jsonify(status="ok", model=STATS["best_model"])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("DEBUG") == "1")

"""IDCCN: HTTP request/API tests. Start the app first (python app.py), then: python tests/test_api.py [base_url]"""
import sys, requests
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000"
VALID = dict(age=54, sex=1, cp=0, trestbps=130, chol=246, fbs=0, restecg=1,
             thalach=150, exang=0, oldpeak=1.0, slope=1, ca=0, thal=2)
passed = 0
def check(name, ok, detail=""):
    global passed; passed += ok
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")

try:
    r = requests.get(f"{BASE}/health", timeout=5)
    check("Server availability", r.status_code == 200, r.text.strip())
except requests.exceptions.ConnectionError:
    print("[FAIL] Server not reachable"); sys.exit(1)

r = requests.post(f"{BASE}/api/predict", json=VALID, timeout=5)
check("Valid input -> 200 (with explanation)", r.status_code == 200 and "probability" in r.json() and "top_factors" in r.json(), str(r.json())[:120])
rid = r.json().get("id")
if rid:
    pdf = requests.get(f"{BASE}/report/{rid}.pdf", timeout=10)
    check("PDF report download", pdf.status_code == 200 and pdf.content[:4] == b"%PDF")

bad = {k: v for k, v in VALID.items() if k != "chol"}
r = requests.post(f"{BASE}/api/predict", json=bad, timeout=5)
check("Missing input -> 400", r.status_code == 400, str(r.json()))

r = requests.post(f"{BASE}/api/predict", json={**VALID, "age": "abc"}, timeout=5)
check("Invalid type -> 422", r.status_code == 422, str(r.json()))

r = requests.post(f"{BASE}/api/predict", json={**VALID, "age": 500}, timeout=5)
check("Out-of-range -> 422", r.status_code == 422, str(r.json()))

r = requests.post(f"{BASE}/api/predict", data="not json", timeout=5)
check("Non-JSON body -> 400", r.status_code == 400)

for p in ["/", "/dashboard", "/predict", "/history", "/api/stats", "/api/history"]:
    check(f"GET {p} -> 200", requests.get(BASE + p, timeout=5).status_code == 200)
print(f"\n{passed} checks passed")

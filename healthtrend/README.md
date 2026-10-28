# HealthTrend AI (educational prototype, not a medical tool)

Run locally:
```
pip install -r requirements.txt
python train_model.py      # cleans data, EDA, trains, saves model + stats
python app.py              # http://127.0.0.1:5000
python tests/test_api.py   # in a second terminal (IDCCN HTTP/API tests)
```
| Subject | Where |
|---|---|
| FDSA | train_model.py, /dashboard, model/stats.json |
| IDCCN | networking/PACKET_TRACER_GUIDE.md, tests/test_api.py, REST API in app.py |
| Cloud | cloud/DEPLOY.md, Dockerfile, Procfile, /health |

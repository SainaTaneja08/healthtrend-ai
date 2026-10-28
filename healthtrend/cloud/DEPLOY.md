# Cloud Computing: Deployment Guide

## Recommended: Render (free web service, fastest)
1. Push this folder to a GitHub repo (include `model/model.joblib`).
2. render.com > New > Web Service > connect repo.
3. Build command: `pip install -r requirements.txt`  Start command: `gunicorn app:app`
4. Open the generated `https://<name>.onrender.com`; screenshot the dashboard, /health, and the Render dashboard.
5. Run `python tests/test_api.py https://<name>.onrender.com` and screenshot the result.

## Alternative: AWS EC2 (better for explaining IaaS)
1. Launch Ubuntu t2/t3.micro; Security Group: allow SSH (22) from your IP only, HTTP/custom 5000 from anywhere.
2. SSH in, `sudo apt install python3-pip`, copy project (scp/git), `pip install -r requirements.txt`.
3. `gunicorn app:app --bind 0.0.0.0:5000`; visit `http://<public-ip>:5000`.
4. Or use the included Dockerfile: `docker build -t healthtrend . && docker run -p 5000:5000 healthtrend`.

## Concepts to explain in the report
| Topic | Explanation for this project |
|---|---|
| Service model | Render = PaaS; EC2 = IaaS; the app is SaaS to end users |
| Storage | Model/dataset in the repo or an S3 bucket; stats served as JSON |
| Access control | Security groups/firewall, HTTPS, no secrets in code, IAM least privilege |
| Security | Input validation (400/422), no patient data stored, HTTPS, dependency pinning |
| Availability | `/health` endpoint, auto-restart by platform, gunicorn workers, redeploy on git push |
| Scalability | Stateless app, so more instances behind a load balancer |

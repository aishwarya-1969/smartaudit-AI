# SmartAudit AI - Smart Audit Analysis for Finance

## Quick start: run app.py

Open the folder in VS Code, open `app.py` and click the Run button (or type `python app.py` in the terminal). It installs the packages on first run and opens the browser.

## Other ways (3 steps)

1. Install **Python 3.10-3.12** (tick "Add to PATH") and **VS Code**. Unzip this folder, then in VS Code use File > Open Folder.
2. Press `Ctrl+Shift+B` (or double-click `run.bat` on Windows, run `./run.sh` on macOS/Linux). The first run creates a virtual environment and installs everything (several minutes).
3. The browser opens http://localhost:8000. Click "New here? Create an account" (first account = Admin), then "Try sample data".

Debugging: press F5 and choose "SmartAudit AI (run server)" after the first run has installed the packages.

AI framework for financial anomaly detection, explainable risk assessment and audit decisions.

```
smartaudit-ai/
├── backend/                FastAPI + XGBoost + SHAP
│   ├── app/
│   │   ├── main.py                       app entry, also serves the frontend
│   │   ├── config.py db.py security.py   settings, SQLite, JWT + password hashing
│   │   ├── routers/                      auth.py (login, users), analysis.py (upload, PDF)
│   │   ├── ml/                           preprocess > features > model (XGBoost) > explain (SHAP TreeExplainer) > scoring > pipeline
│   │   └── services/report.py            PDF report (ReportLab)
│   └── requirements.txt
├── frontend/               index.html, css/style.css, js/app.js (UI), js/api.js (API client)
├── Dockerfile
└── README.md
```

## Run locally (VS Code)

```
cd backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Open http://localhost:8000 (API docs at /docs). The first account you register becomes Admin.
Use "Try sample data" on the upload page to test.

## Deploy (public URL for everyone)

The Dockerfile serves backend and frontend together, so you deploy one service.
- Render / Railway / Fly.io: create a Web Service from this repo, choose Docker, set env `SECRET_KEY` to a long random string.
- Any VM: `docker build -t smartaudit . && docker run -p 80:8000 -e SECRET_KEY=... -v smartdata:/data smartaudit`

Notes: SQLite lives in /data (attach a persistent disk, or switch to Postgres for production). 512 MB RAM is enough (no PyTorch).

CSV: required `amount`; optional `txn_id, date, vendor, employee, category, approved_by, is_fraud` (labels, if present, are used only by the supervised models on the Model Evaluation page).

## Historical data (new)
Open "Historical vs Current", upload approved past transactions (Admin/Auditor), then analyse a new CSV. Overlapping rows are skipped, history is never invented, and comparisons need 5+ past payments per vendor and 3+ months of history. Tests: `cd backend && python tests/test_historical.py`.

## Model (follows the base-paper methodology)
Audit data > preprocessing > 9 audit risk features > XGBoost > risk score > SHAP (TreeExplainer) > vendor/employee/compliance/health scores > recommendations. With an `is_fraud` column XGBoost is a supervised classifier and each row is scored out-of-fold (never by a model that saw its own label). Without labels XGBoost learns from an expert rule score (weak labels), so results are screening scores, not measured fraud accuracy. SHAP shows association, not causation.

## Supervised models and evaluation (Module 2)
When the CSV has an `is_fraud` column, Logistic Regression, Random Forest and XGBoost are trained on the earlier 70% of transactions and tested on the later 30% (stratified split if dates are missing). The Model Evaluation page shows real accuracy, precision, recall, F1, ROC-AUC, PR-AUC and the confusion matrix, next to the expert rule-score baseline. Without labels nothing is invented. Try `sample_data/labeled_demo.csv` (synthetic).

"""
SkillPulse - Daily Snapshot Refresh Script
==========================================
Run this script every day to:
  1. Pull the latest job postings from MySQL
  2. Extract real apply URLs from Adzuna data
  3. Update data_exports/db_snapshot.json
  4. Commit & push to GitHub so Streamlit Cloud auto-updates

Usage:
  python scripts/refresh_snapshot.py

Schedule (Windows Task Scheduler):
  Action: python "C:\...\skillpulse\scripts\refresh_snapshot.py"
  Trigger: Daily at 06:00 AM
"""
import os, sys, json, urllib.parse
from datetime import datetime
from pathlib import Path

# Ensure UTF-8 output encoding for Windows CMD
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Find project root (parent of scripts/)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv(ROOT / ".env")

u  = os.getenv("DB_USER", "root")
pw = os.getenv("DB_PASSWORD", "")
h  = os.getenv("DB_HOST", "localhost")
d  = os.getenv("DB_NAME", "skillpulse")
p  = urllib.parse.quote_plus(pw)

print(f"[{datetime.now():%H:%M:%S}] Connecting to MySQL at {h}/{d}...")
engine = create_engine(f"mysql+pymysql://{u}:{p}@{h}/{d}")

# 1. Trigger Model Retraining Pipeline on New Data
print(f"[{datetime.now():%H:%M:%S}] 🤖 Executing ML Retraining pipeline on new data...")
import subprocess
retrain_res = subprocess.run(
    [sys.executable, str(ROOT / "mlops" / "retrain.py"), "--force"],
    cwd=ROOT, capture_output=True, text=True
)
if retrain_res.returncode == 0:
    print(f"[{datetime.now():%H:%M:%S}] ✅ Model retrained & saved to models/xgboost_model.joblib")
else:
    print(f"[{datetime.now():%H:%M:%S}] ⚠️ Retrain warning: {retrain_res.stderr.strip()}")

SNAP_PATH = ROOT / "data_exports" / "db_snapshot.json"
with open(SNAP_PATH, "r", encoding="utf-8") as f:
    snap = json.load(f)

def get_url(raw):
    try:
        r = json.loads(raw)
        return r.get("redirect_url") or r.get("url") or r.get("apply_url") or ""
    except:
        return ""

print(f"[{datetime.now():%H:%M:%S}] Refreshing job listings with apply URLs...")
new_jobs = {}
for country in ["us", "gb", "in"]:
    df = pd.read_sql(
        """
        SELECT jp.id, jp.title AS Title, jp.company AS Company, jp.location AS Location,
               CONCAT(IFNULL(jp.salary_min,0),' - ',IFNULL(jp.salary_max,0)) AS salary_range,
               jp.description AS Description, jp.posted_date, jp.raw_json
        FROM job_postings jp
        WHERE jp.country = %s
        ORDER BY jp.id DESC
        LIMIT 500
        """,
        engine, params=(country,)
    )
    df["Apply URL"] = df["raw_json"].apply(get_url)
    df["Posted"]    = pd.to_datetime(df["posted_date"], errors="coerce").dt.strftime("%Y-%m-%d").fillna("N/A")
    df = df.drop(columns=["raw_json", "posted_date", "id"], errors="ignore")
    df = df.drop_duplicates(subset=["Title", "Company"]).head(250)
    new_jobs[country] = df.to_dict(orient="records")
    with_url = df["Apply URL"].astype(bool).sum()
    print(f"  [{country.upper()}] {len(df)} jobs | {with_url} with direct apply URL")

snap["matching_jobs"] = new_jobs
snap["last_refreshed"] = datetime.now().strftime("%Y-%m-%d %H:%M")

with open(SNAP_PATH, "w", encoding="utf-8") as f:
    json.dump(snap, f, indent=2)

size_kb = SNAP_PATH.stat().st_size // 1024
print(f"[{datetime.now():%H:%M:%S}] Snapshot saved ({size_kb} KB)")

# Auto-commit and push to GitHub so Streamlit Cloud picks up new jobs & retrained model
print(f"[{datetime.now():%H:%M:%S}] Pushing updated snapshot and retrained XGBoost model to GitHub...")
result = subprocess.run(
    ["git", "add", "data_exports/db_snapshot.json", "models/xgboost_model.joblib"],
    cwd=ROOT, capture_output=True, text=True
)
result2 = subprocess.run(
    ["git", "commit", "-m", f"Daily refresh: job listings updated {datetime.now():%Y-%m-%d}"],
    cwd=ROOT, capture_output=True, text=True
)
result3 = subprocess.run(
    ["git", "push", "origin", "main"],
    cwd=ROOT, capture_output=True, text=True
)
if result3.returncode == 0:
    print(f"[{datetime.now():%H:%M:%S}] ✅ GitHub push successful! Streamlit Cloud will refresh shortly.")
else:
    print(f"[{datetime.now():%H:%M:%S}] ⚠️  Git push output: {result3.stderr.strip()}")

print(f"\n✅ Daily refresh complete at {snap['last_refreshed']}")

import os
import json
import joblib
import numpy as np
from dotenv import load_dotenv
from urllib.parse import quote_plus

from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.models import PredictRequest, PredictResponse, TopSkillsResponse, SkillItem, HealthResponse
from app.db import get_db

# ── Load env ──────────────────────────────────────────────────────────────────
load_dotenv(dotenv_path=".env")

# ── Load model & feature names at startup ────────────────────────────────────
MODEL_PATH   = "models/xgboost_model.joblib"
FEATURES_PATH = "data_exports/feature_names.json"

model = joblib.load(MODEL_PATH)
with open(FEATURES_PATH, "r") as f:
    FEATURE_NAMES = json.load(f)

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="SkillPulse API",
    description="Real-time job market analytics and salary prediction API. "
                "Built on top of 6,000 Adzuna job postings (IN, GB, US) and an XGBoost regressor.",
    version="1.0.0",
    contact={"name": "Kartik Singh", "email": "kartik@skillpulse.io"},
    license_info={"name": "MIT"},
)


# ── Health Check ─────────────────────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check(db: Session = Depends(get_db)):
    """Returns service status and database connectivity."""
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {e}"
    return HealthResponse(status="ok", model_loaded=True, db_status=db_status)


# ── Top Skills (global) ──────────────────────────────────────────────────────
@app.get("/skills/top", response_model=TopSkillsResponse, tags=["Skills"])
def top_skills(limit: int = 15, db: Session = Depends(get_db)):
    """Returns the most in-demand developer skills globally."""
    query = text("""
        SELECT s.name, COUNT(js.job_id) AS job_count
        FROM skills s
        JOIN job_skills js ON js.skill_id = s.id
        GROUP BY s.name
        ORDER BY job_count DESC
        LIMIT :limit
    """)
    rows = db.execute(query, {"limit": limit}).fetchall()
    skills = [SkillItem(skill=row[0], job_count=row[1]) for row in rows]
    return TopSkillsResponse(total_returned=len(skills), skills=skills)


# ── Top Skills by Country ────────────────────────────────────────────────────
@app.get("/skills/top/{country}", response_model=TopSkillsResponse, tags=["Skills"])
def top_skills_by_country(country: str, limit: int = 12, db: Session = Depends(get_db)):
    """Returns top skills for a specific country (gb, us, in)."""
    country = country.lower()
    if country not in ("gb", "us", "in"):
        raise HTTPException(status_code=400, detail="Country must be one of: gb, us, in")
    query = text("""
        SELECT s.name, COUNT(js.job_id) AS job_count
        FROM skills s
        JOIN job_skills js ON js.skill_id = s.id
        JOIN job_postings jp ON jp.id = js.job_id
        WHERE jp.country = :country
        GROUP BY s.name
        ORDER BY job_count DESC
        LIMIT :limit
    """)
    rows = db.execute(query, {"country": country, "limit": limit}).fetchall()
    skills = [SkillItem(skill=row[0], job_count=row[1]) for row in rows]
    return TopSkillsResponse(total_returned=len(skills), skills=skills)


# ── Salary Prediction ─────────────────────────────────────────────────────────
@app.post("/predict", response_model=PredictResponse, tags=["Predict"])
def predict_salary(payload: PredictRequest):
    """
    Predicts the salary range given a list of skills and target country.
    
    - **skills**: list of skill names (e.g. ["Python", "AWS", "Docker"])
    - **country**: target country code — 'gb' (UK) or 'us' (US)
    """
    country = payload.country.lower()
    if country not in ("gb", "us"):
        raise HTTPException(
            status_code=400,
            detail="Only 'gb' (UK) and 'us' (US) are supported for salary prediction. "
                   "India is excluded due to insufficient salary data coverage."
        )

    # Build feature vector
    skill_set = {s.lower().strip() for s in payload.skills}
    feature_vector = []
    for feat in FEATURE_NAMES:
        if feat == "country_gb":
            feature_vector.append(1 if country == "gb" else 0)
        elif feat == "country_us":
            feature_vector.append(1 if country == "us" else 0)
        else:
            # Match skill case-insensitively
            feature_vector.append(1 if feat.lower() in skill_set else 0)

    X = np.array([feature_vector], dtype=np.float32)
    log_pred = float(model.predict(X)[0])

    # Back-transform from log scale to raw USD
    salary_usd = float(np.expm1(log_pred))

    # Back-convert to local currency
    if country == "gb":
        salary_local = salary_usd / 1.27
        currency = "GBP"
    else:
        salary_local = salary_usd
        currency = "USD"

    return PredictResponse(
        predicted_salary_usd=round(salary_usd, 2),
        predicted_salary_local=round(salary_local, 2),
        currency=currency,
        country=country.upper(),
        skills_matched=[f for f in FEATURE_NAMES if f.lower() in skill_set],
        note="Prediction based on skill signals only. Actual salaries vary with seniority and company."
    )

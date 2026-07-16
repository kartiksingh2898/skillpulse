"""
retrain.py  — SkillPulse Phase 7 MLOps
=======================================
Auto-retraining trigger. Checks the latest drift report in MySQL and,
if drift was detected (alert_triggered = 1), retrains the XGBoost model
from scratch using the same Phase 4 methodology.

Usage:
    python mlops/retrain.py [--force]

    --force : Skip drift check and retrain regardless.

On completion:
  • Overwrites  models/xgboost_model.joblib  with the new model
  • Appends a new row to model_runs table
  • Prints a clear pass/skip summary
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

import joblib
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.model_selection import train_test_split
from sqlalchemy import create_engine, text
from xgboost import XGBRegressor

BASE_DIR   = Path(__file__).resolve().parent.parent
DATA_DIR   = BASE_DIR / "data_exports"
MODELS_DIR = BASE_DIR / "models"

load_dotenv(dotenv_path=str(BASE_DIR / ".env"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("retrain")


# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────
def get_engine():
    return create_engine(
        "mysql+pymysql://{}:{}@{}:{}/{}".format(
            os.getenv("DB_USER"),
            quote_plus(os.getenv("DB_PASSWORD", "")),
            os.getenv("DB_HOST", "localhost"),
            os.getenv("DB_PORT", "3306"),
            os.getenv("DB_NAME"),
        ),
        pool_pre_ping=True,
    )


def drift_alert_pending(engine) -> bool:
    """Return True if the most recent drift report has alert_triggered = 1."""
    sql = text("""
        SELECT alert_triggered
        FROM drift_reports
        ORDER BY run_date DESC
        LIMIT 1
    """)
    with engine.connect() as conn:
        row = conn.execute(sql).fetchone()
    if row is None:
        log.info("No drift reports found in database. Running baseline retrain.")
        return True
    return bool(row[0])


def log_run(engine, mae: float, rmse: float, r2: float,
            raw_mae_usd: float, params: dict):
    """Insert a new row into model_runs."""
    notes = json.dumps({
        "trigger"     : "auto-retrain (Phase 7)",
        "best_params" : params,
        "r2"          : round(r2, 4),
        "raw_mae_usd" : round(raw_mae_usd, 2),
    })
    sql = text("""
        INSERT INTO model_runs (model_type, mae, rmse, notes)
        VALUES ('xgboost_retrain', :mae, :rmse, :notes)
    """)
    with engine.begin() as conn:
        conn.execute(sql, {"mae": round(mae, 4), "rmse": round(rmse, 4),
                           "notes": notes})


# ─────────────────────────────────────────────────────────────────
# RETRAIN
# ─────────────────────────────────────────────────────────────────
def retrain(engine):
    log.info("Loading training data from disk …")
    X = pd.read_csv(DATA_DIR / "X_train.csv")
    y = pd.read_csv(DATA_DIR / "y_train.csv")["log_salary_usd"]

    log.info("Training set: %s  |  Target range: [%.2f, %.2f]",
             X.shape, y.min(), y.max())

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.20, random_state=42
    )

    # Use the best hyperparameters found in Phase 4 as a solid starting point
    best_params = {
        "n_estimators"     : 191,
        "max_depth"        : 5,
        "learning_rate"    : 0.0556,
        "subsample"        : 0.952,
        "colsample_bytree" : 0.930,
        "min_child_weight" : 5,
        "reg_alpha"        : 5.378,
        "reg_lambda"       : 5.530,
        "objective"        : "reg:squarederror",
        "random_state"     : 42,
        "n_jobs"           : -1,
    }

    log.info("Fitting XGBRegressor with Phase-4 optimal hyperparameters …")
    model = XGBRegressor(**best_params)
    model.fit(X_tr, y_tr, eval_set=[(X_te, y_te)], verbose=False)

    # Metrics
    preds_log = model.predict(X_te)
    residuals = preds_log - y_te.values
    mae       = float(np.mean(np.abs(residuals)))
    rmse      = float(np.sqrt(np.mean(residuals ** 2)))

    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((y_te.values - y_te.mean()) ** 2)
    r2     = float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.0

    preds_usd  = np.expm1(preds_log)
    actual_usd = np.expm1(y_te.values)
    raw_mae    = float(np.mean(np.abs(preds_usd - actual_usd)))

    log.info("Retrain metrics  MAE=%.4f  RMSE=%.4f  R²=%.4f  RawMAE=$%.0f",
             mae, rmse, r2, raw_mae)

    # Save model
    MODELS_DIR.mkdir(exist_ok=True)
    model_path = MODELS_DIR / "xgboost_model.joblib"
    joblib.dump(model, model_path)
    log.info("Model saved → %s", model_path)

    # Log to MySQL
    log_run(engine, mae, rmse, r2, raw_mae, best_params)
    log.info("Run logged to MySQL model_runs table ✓")

    print("\n" + "="*60)
    print("  SkillPulse — Auto-Retrain Complete")
    print("="*60)
    print(f"  Log MAE   : {mae:.4f}")
    print(f"  Log RMSE  : {rmse:.4f}")
    print(f"  R² Score  : {r2:.4f}")
    print(f"  USD MAE   : ${raw_mae:,.2f}")
    print(f"  Model     : {model_path}")
    print("="*60 + "\n")

    return {"mae": mae, "rmse": rmse, "r2": r2, "raw_mae_usd": raw_mae}


# ─────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SkillPulse auto-retraining trigger")
    parser.add_argument("--force", action="store_true",
                        help="Retrain unconditionally, ignoring drift status")
    args = parser.parse_args()

    engine = get_engine()

    if args.force:
        log.info("--force flag set. Retraining unconditionally …")
        retrain(engine)
    else:
        log.info("Checking latest drift report for alert status …")
        if drift_alert_pending(engine):
            log.info("Drift alert detected → triggering retraining pipeline …")
            retrain(engine)
        else:
            print("\n✅  No drift alert detected. Model is stable — skipping retrain.\n")
            sys.exit(0)

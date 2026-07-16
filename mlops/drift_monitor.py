"""
drift_monitor.py  — SkillPulse Phase 7 MLOps
=============================================
Runs an Evidently AI data-drift report comparing:
  • REFERENCE : X_train.csv  (baseline from EDA / Phase 3)
  • CURRENT   : freshest N job records pulled live from MySQL

Outputs
  • HTML report  → drift_reports/drift_<timestamp>.html
  • JSON summary → drift_reports/drift_<timestamp>.json
  • MySQL row    → drift_reports table (drift_date, feature_drift_pct,
                   target_drift, alert_triggered, report_json)

Exit codes
  0 = no drift alert
  1 = drift alert triggered  (use in CI/CD or retrain.py)
"""

import os
import sys
import json
import logging
import datetime
import numpy as np
import pandas as pd
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from evidently import Report, Dataset
from evidently.presets import DataDriftPreset

# ─────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────
BASE_DIR         = Path(__file__).resolve().parent.parent
DATA_DIR         = BASE_DIR / "data_exports"
DRIFT_OUT_DIR    = BASE_DIR / "drift_reports"
FEATURE_NAMES_F  = DATA_DIR / "feature_names.json"
X_TRAIN_F        = DATA_DIR / "X_train.csv"
Y_TRAIN_F        = DATA_DIR / "y_train.csv"

# Drift thresholds
FEATURE_DRIFT_THRESHOLD = 0.30   # Alert if >30% of features drift
CURRENT_SAMPLE_SIZE     = 500    # How many recent DB jobs to pull as current

load_dotenv(dotenv_path=str(BASE_DIR / ".env"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("drift_monitor")

# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────
def get_engine():
    user     = os.getenv("DB_USER")
    password = quote_plus(os.getenv("DB_PASSWORD", ""))
    host     = os.getenv("DB_HOST", "localhost")
    port     = os.getenv("DB_PORT", "3306")
    db       = os.getenv("DB_NAME")
    return create_engine(
        f"mysql+pymysql://{user}:{password}@{host}:{port}/{db}",
        pool_pre_ping=True
    )


def build_feature_matrix(job_ids: pd.Series, feature_names: list,
                          engine) -> pd.DataFrame:
    """Pull skill tags for a set of job IDs and build the multi-hot matrix."""
    if job_ids.empty:
        return pd.DataFrame(columns=feature_names)

    id_list = ", ".join(str(i) for i in job_ids.tolist())
    sql = f"""
        SELECT js.job_id, s.name AS skill, jp.country
        FROM job_skills js
        JOIN skills s  ON s.id  = js.skill_id
        JOIN job_postings jp ON jp.id = js.job_id
        WHERE js.job_id IN ({id_list})
    """
    with engine.connect() as conn:
        rows = pd.DataFrame(conn.execute(text(sql)).fetchall(),
                            columns=["job_id", "skill", "country"])

    # Build multi-hot
    matrix = pd.DataFrame(index=job_ids)
    for fn in feature_names:
        if fn == "country_gb":
            matrix[fn] = rows.groupby("job_id")["country"].first().reindex(job_ids).eq("gb").astype(int).values
        elif fn == "country_us":
            matrix[fn] = rows.groupby("job_id")["country"].first().reindex(job_ids).eq("us").astype(int).values
        else:
            tagged = rows[rows["skill"] == fn]["job_id"].unique()
            matrix[fn] = job_ids.isin(tagged).astype(int).values

    matrix.reset_index(drop=True, inplace=True)
    return matrix.fillna(0)


def fetch_current_jobs(engine, n: int = CURRENT_SAMPLE_SIZE) -> pd.Series:
    """Return job IDs of the most recently scraped postings."""
    sql = f"""
        SELECT jp.id
        FROM job_postings jp
        WHERE jp.country IN ('us', 'gb')
        ORDER BY jp.id DESC
        LIMIT {n}
    """
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        return pd.Series([r[0] for r in result.fetchall()])


def log_to_mysql(engine, run_ts: str, feature_drift_pct: float,
                 target_drift: bool, alert: bool, summary: dict):
    """Insert a drift report row into the drift_reports table."""
    payload = json.dumps(summary, default=str)
    sql = text("""
        INSERT INTO drift_reports
            (run_date, feature_drift_pct, target_drift, alert_triggered, report_json)
        VALUES
            (:run_date, :fdp, :td, :alert, :rjson)
    """)
    with engine.begin() as conn:
        conn.execute(sql, {
            "run_date" : run_ts,
            "fdp"      : round(feature_drift_pct, 4),
            "td"       : int(target_drift),
            "alert"    : int(alert),
            "rjson"    : payload,
        })


# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────
def run_drift_check(verbose: bool = True) -> dict:
    """
    Execute the full drift check pipeline.
    Returns a summary dict and exits with code 1 if alert triggered.
    """
    DRIFT_OUT_DIR.mkdir(exist_ok=True)
    ts      = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    ts_iso  = datetime.datetime.now().isoformat(timespec="seconds")

    # ── 1. Load reference data ────────────────────────────────────
    log.info("Loading reference dataset (X_train.csv) …")
    X_ref = pd.read_csv(X_TRAIN_F)
    y_ref = pd.read_csv(Y_TRAIN_F, header=None, names=["log_salary"])

    with open(FEATURE_NAMES_F) as f:
        feature_names: list = json.load(f)

    log.info("Reference shape: %s", X_ref.shape)

    # ── 2. Fetch current data from MySQL ──────────────────────────
    log.info("Connecting to MySQL to fetch current jobs …")
    engine = get_engine()
    current_ids = fetch_current_jobs(engine, n=CURRENT_SAMPLE_SIZE)

    if current_ids.empty:
        log.warning("No current job IDs found. Aborting drift check.")
        return {}

    log.info("Building feature matrix for %d current jobs …", len(current_ids))
    X_cur = build_feature_matrix(current_ids, feature_names, engine)
    log.info("Current shape: %s", X_cur.shape)

    # Align columns
    X_ref_aligned = X_ref[feature_names].fillna(0)
    X_cur_aligned = X_cur[feature_names].fillna(0)

    # ── 3. Run Evidently Report ───────────────────────────────────
    log.info("Running Evidently DataDriftPreset report …")
    ref_dataset = Dataset.from_pandas(X_ref_aligned)
    cur_dataset = Dataset.from_pandas(X_cur_aligned)

    report = Report([DataDriftPreset()])
    result = report.run(reference_data=ref_dataset, current_data=cur_dataset)

    # ── 4. Save HTML report ───────────────────────────────────────
    html_path = DRIFT_OUT_DIR / f"drift_{ts}.html"
    result.save_html(str(html_path))
    log.info("HTML report saved → %s", html_path)

    # ── 5. Extract drift metrics ──────────────────────────────────
    result_dict  = result.dict()
    drift_by_col = {}
    drifted_features = 0
    feature_drift_pct = 0.0

    try:
        metrics_raw = result_dict.get("metrics", [])
        for m in metrics_raw:
            m_type = str(m.get("config", {}).get("type", ""))
            if "DriftedColumnsCount" in m_type:
                val = m.get("value", {})
                drifted_features = int(val.get("count", 0))
                feature_drift_pct = float(val.get("share", 0.0))
            elif "ValueDrift" in m_type:
                cfg = m.get("config", {})
                col_name = cfg.get("column")
                method = cfg.get("method", "")
                threshold = cfg.get("threshold", 0.05)
                val = m.get("value")
                if val is not None:
                    is_p_val = "p_value" in method.lower()
                    if is_p_val:
                        drifted = val <= threshold
                    else:
                        drifted = val >= threshold
                    if drifted:
                        drift_by_col[col_name] = True
                    
    except Exception as parse_err:
        log.warning("Could not parse detailed drift metrics: %s", parse_err)
        feature_drift_pct = 0.0

    target_drift  = False   # No target (y) drift check — we only have X
    alert_triggered = feature_drift_pct >= FEATURE_DRIFT_THRESHOLD

    # ── 6. Build summary ──────────────────────────────────────────
    drifted_cols = [c for c, d in drift_by_col.items() if d]
    summary = {
        "run_ts"              : ts_iso,
        "reference_samples"   : len(X_ref_aligned),
        "current_samples"     : len(X_cur_aligned),
        "total_features"      : len(feature_names),
        "features_drifted"    : len(drifted_cols),
        "feature_drift_pct"   : round(feature_drift_pct * 100, 2),
        "drifted_columns"     : drifted_cols,
        "target_drift"        : target_drift,
        "alert_triggered"     : alert_triggered,
        "threshold_pct"       : FEATURE_DRIFT_THRESHOLD * 100,
        "html_report"         : str(html_path),
    }

    # ── 7. Save JSON summary ──────────────────────────────────────
    json_path = DRIFT_OUT_DIR / f"drift_{ts}.json"
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    # ── 8. Log to MySQL ───────────────────────────────────────────
    try:
        log_to_mysql(engine, ts_iso, feature_drift_pct,
                     target_drift, alert_triggered, summary)
        log.info("Drift report logged to MySQL drift_reports table ✓")
    except Exception as db_err:
        log.warning("MySQL logging failed (table may need migration): %s", db_err)

    # ── 9. Print result ───────────────────────────────────────────
    if verbose:
        print("\n" + "="*60)
        print("  SkillPulse — Drift Monitor Report")
        print("="*60)
        print(f"  Run timestamp    : {ts_iso}")
        print(f"  Reference rows   : {summary['reference_samples']:,}")
        print(f"  Current rows     : {summary['current_samples']:,}")
        print(f"  Features checked : {summary['total_features']}")
        print(f"  Features drifted : {summary['features_drifted']}")
        print(f"  Drift %          : {summary['feature_drift_pct']:.1f}% "
              f"(threshold: {summary['threshold_pct']:.0f}%)")
        if drifted_cols:
            print(f"  Drifted columns  : {', '.join(drifted_cols[:8])}"
                  + (" ..." if len(drifted_cols) > 8 else ""))
        print(f"  Alert triggered  : {'⚠️  YES — retraining recommended!' if alert_triggered else '✅  NO — distribution stable'}")
        print(f"  HTML report      : {html_path}")
        print("="*60 + "\n")

    return summary


if __name__ == "__main__":
    summary = run_drift_check(verbose=True)
    sys.exit(1 if summary.get("alert_triggered") else 0)

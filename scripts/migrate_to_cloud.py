"""
SkillPulse — One-Time Data Migration: Local MySQL → TiDB Cloud
==============================================================
Copies all existing data from your local MySQL database to TiDB Cloud.

Design guarantees:
  - ALLOW_CLOUD_MIGRATION=true guard prevents accidental re-runs
  - Dependency-ordered DELETE (child → parent) clears destination safely
  - Dependency-ordered INSERT (parent → child) preserves all FK relationships
  - Explicit ID values preserved — cloud gets identical IDs to local
  - AUTO_INCREMENT rebased via ALTER TABLE ... AUTO_INCREMENT = 0 (TiDB mechanism)
  - Mandatory allocator collision test on all 4 AUTO_INCREMENT tables
  - Full verification: row counts, MIN/MAX IDs, FK orphan checks, sample data

WARNING: Do NOT run this script after GitHub Actions has started writing to
TiDB Cloud. It truncates (via DELETE) all destination tables first and will
erase any cloud-only data written since migration.

Usage (from repo root):
  ALLOW_CLOUD_MIGRATION=true python scripts/migrate_to_cloud.py

Pre-conditions:
  - Phase 0 (test_tidb_connection.py) must pass locally AND from GitHub Actions
  - schema_mysql.sql must already be applied to TiDB Cloud (via SQL Editor)
  - GitHub Actions workflow must be temporarily disabled
  - Local .env must contain both local MySQL and TiDB Cloud credentials
    (see "CONFIGURATION" section below)

CONFIGURATION:
  The script reads two sets of credentials from environment variables.
  Set these before running (do NOT commit them):

    # Source — local MySQL
    export LOCAL_DB_USER=root
    export LOCAL_DB_PASSWORD=your_local_password
    export LOCAL_DB_HOST=localhost
    export LOCAL_DB_PORT=3306
    export LOCAL_DB_NAME=skillpulse

    # Destination — TiDB Cloud (same as your .env after migration)
    export DB_USER=<exact username from TiDB Connect dialog>
    export DB_PASSWORD=<tidb_password>
    export DB_HOST=<tidb_host>
    export DB_PORT=4000
    export DB_NAME=skillpulse
    export DB_SSL=true
    export DB_SSL_CA=certs/tidb-ca.pem
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from app.db_utils import build_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("migrate_to_cloud")

BATCH_SIZE = 500

# FK dependency graph
# DELETE order: child → parent
TABLES_DELETE_ORDER = [
    "job_skills",     # child of job_postings AND skills
    "drift_reports",  # standalone
    "model_runs",     # standalone
    "job_postings",   # parent — safe after job_skills cleared
    "skills",         # parent — safe after job_skills cleared
]
# INSERT order: parent → child
TABLES_INSERT_ORDER = ["skills", "job_postings", "job_skills", "model_runs", "drift_reports"]

# All tables with AUTO_INCREMENT id column
AUTO_INC_TABLES = ["job_postings", "skills", "model_runs", "drift_reports"]

# Per-table minimal valid INSERT for allocator collision test.
# Uses only non-nullable columns; values clearly marked as probes.
TEST_INSERT_SQL = {
    "job_postings":  "INSERT INTO job_postings (source, title) VALUES ('_probe', '_migration_probe')",
    "skills":        "INSERT INTO skills (name) VALUES ('_migration_probe')",
    "model_runs":    "INSERT INTO model_runs (model_type) VALUES ('_migration_probe')",
    "drift_reports": "INSERT INTO drift_reports (feature_drift_pct) VALUES (0.0)",
}
TEST_DELETE_SQL = {
    "job_postings":  "DELETE FROM job_postings WHERE source = '_probe' AND title = '_migration_probe'",
    "skills":        "DELETE FROM skills WHERE name = '_migration_probe'",
    "model_runs":    "DELETE FROM model_runs WHERE model_type = '_migration_probe'",
    "drift_reports": "DELETE FROM drift_reports WHERE feature_drift_pct = 0.0",
}


def build_local_engine():
    """Builds engine for the local MySQL source using LOCAL_DB_* env vars."""
    url = URL.create(
        drivername="mysql+pymysql",
        username=os.getenv("LOCAL_DB_USER", os.getenv("DB_USER", "root")),
        password=os.getenv("LOCAL_DB_PASSWORD", os.getenv("DB_PASSWORD", "")),
        host=os.getenv("LOCAL_DB_HOST", "localhost"),
        port=int(os.getenv("LOCAL_DB_PORT", "3306")),
        database=os.getenv("LOCAL_DB_NAME", os.getenv("DB_NAME", "skillpulse")),
    )
    return create_engine(url, pool_pre_ping=True)


def fetch_all(conn, table: str) -> list[dict]:
    """Fetch all rows from a table as a list of dicts."""
    rows = conn.execute(text(f"SELECT * FROM {table}")).mappings().all()
    return [dict(r) for r in rows]


def insert_batch(conn, table: str, rows: list[dict]):
    """Insert rows in BATCH_SIZE chunks, using the exact columns from the source."""
    if not rows:
        return 0
    cols = list(rows[0].keys())
    col_str = ", ".join(f"`{c}`" for c in cols)
    param_str = ", ".join(f":{c}" for c in cols)
    sql = text(f"INSERT INTO `{table}` ({col_str}) VALUES ({param_str})")
    inserted = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        conn.execute(sql, batch)
        inserted += len(batch)
        log.info(f"    [{table}] Inserted {inserted}/{len(rows)} rows...")
    return inserted


def rebase_auto_increment(conn, table: str):
    """Use TiDB's documented rebase mechanism to reset the AUTO_INCREMENT allocator."""
    max_id = conn.execute(text(f"SELECT MAX(id) FROM `{table}`")).scalar() or 0
    conn.execute(text(f"ALTER TABLE `{table}` AUTO_INCREMENT = 0"))
    log.info(f"  [{table}] AUTO_INCREMENT rebased (max migrated id={max_id})")
    return max_id


def test_allocator(conn, table: str, max_id_before: int):
    """Verify AUTO_INCREMENT allocator produces new_id > max migrated id."""
    result = conn.execute(text(TEST_INSERT_SQL[table]))
    new_id = result.lastrowid
    conn.execute(text(TEST_DELETE_SQL[table]))
    assert new_id > max_id_before, (
        f"[{table}] AUTO_INCREMENT collision: new_id={new_id} <= max_id={max_id_before}. "
        f"Rebase did not work. Do not proceed with production use."
    )
    log.info(
        f"  [{table}] Allocator OK: new_id={new_id} > max_id={max_id_before} "
        f"(gap={new_id - max_id_before} — gaps expected on TiDB)"
    )


def verify(local_conn, cloud_conn):
    """Run all post-migration verification checks."""
    log.info("\n── Verification ─────────────────────────────────────────────")
    all_passed = True

    # 1. Row counts
    log.info("1/4  Row counts:")
    for table in TABLES_INSERT_ORDER:
        local_n = local_conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar()
        cloud_n = cloud_conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar()
        match = "✅" if local_n == cloud_n else "❌"
        log.info(f"  {match} {table}: local={local_n}, cloud={cloud_n}")
        if local_n != cloud_n:
            all_passed = False

    # 2. MIN / MAX / DISTINCT count on key tables
    log.info("2/4  MIN/MAX/DISTINCT id on job_postings and skills:")
    for table in ["job_postings", "skills"]:
        for expr in ["MIN(id)", "MAX(id)", "COUNT(DISTINCT id)"]:
            local_v = local_conn.execute(text(f"SELECT {expr} FROM `{table}`")).scalar()
            cloud_v = cloud_conn.execute(text(f"SELECT {expr} FROM `{table}`")).scalar()
            match = "✅" if local_v == cloud_v else "❌"
            log.info(f"  {match} {table} {expr}: local={local_v}, cloud={cloud_v}")
            if local_v != cloud_v:
                all_passed = False

    # 3. FK orphan checks
    log.info("3/4  FK orphan checks:")
    orphan_jobs = cloud_conn.execute(text("""
        SELECT COUNT(*) FROM job_skills js
        LEFT JOIN job_postings jp ON js.job_id = jp.id
        WHERE jp.id IS NULL
    """)).scalar()
    match = "✅" if orphan_jobs == 0 else "❌"
    log.info(f"  {match} Orphaned job_skills (bad job_id): {orphan_jobs}")
    if orphan_jobs != 0:
        all_passed = False

    orphan_skills = cloud_conn.execute(text("""
        SELECT COUNT(*) FROM job_skills js
        LEFT JOIN skills s ON js.skill_id = s.id
        WHERE s.id IS NULL
    """)).scalar()
    match = "✅" if orphan_skills == 0 else "❌"
    log.info(f"  {match} Orphaned job_skills (bad skill_id): {orphan_skills}")
    if orphan_skills != 0:
        all_passed = False

    # 4. Sample data integrity check (10 random job_postings rows)
    log.info("4/4  Sample data integrity (10 random job_postings rows):")
    sample_ids = [
        row[0] for row in local_conn.execute(text(
            "SELECT id FROM job_postings ORDER BY RAND() LIMIT 10"
        )).fetchall()
    ]
    sample_ok = True
    for job_id in sample_ids:
        local_row = local_conn.execute(text(
            "SELECT title, company, source FROM job_postings WHERE id = :id"
        ), {"id": job_id}).fetchone()
        cloud_row = cloud_conn.execute(text(
            "SELECT title, company, source FROM job_postings WHERE id = :id"
        ), {"id": job_id}).fetchone()
        if local_row != cloud_row:
            log.error(f"  ❌ Data mismatch at job_postings.id={job_id}: local={local_row}, cloud={cloud_row}")
            sample_ok = False
            all_passed = False
    if sample_ok:
        log.info(f"  ✅ All {len(sample_ids)} sampled rows match")

    return all_passed


def main():
    # ── Safety guard ─────────────────────────────────────────────────────────
    if os.getenv("ALLOW_CLOUD_MIGRATION") != "true":
        raise RuntimeError(
            "\n"
            "  Migration blocked.\n"
            "  Set ALLOW_CLOUD_MIGRATION=true in your local shell to proceed.\n"
            "\n"
            "  ⚠️  WARNING: Never run this after GitHub Actions has started writing\n"
            "  to TiDB Cloud — it erases all cloud-only data written since migration.\n"
        )

    log.info("=" * 65)
    log.info("  SkillPulse: Local MySQL → TiDB Cloud Migration")
    log.info(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("=" * 65)

    local_engine = build_local_engine()
    cloud_engine = build_engine()

    # Verify source is local and destination is TiDB
    log.info(f"Source:  {os.getenv('LOCAL_DB_HOST', 'localhost')}:{os.getenv('LOCAL_DB_PORT', '3306')}")
    log.info(f"Dest:    {os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}")

    # ── Step 1: Read all source data ─────────────────────────────────────────
    log.info("\n── Step 1/4: Reading source data from local MySQL ───────────")
    source_data = {}
    with local_engine.connect() as conn:
        for table in TABLES_INSERT_ORDER:
            rows = fetch_all(conn, table)
            source_data[table] = rows
            log.info(f"  [{table}] {len(rows):,} rows read")

    total_rows = sum(len(v) for v in source_data.values())
    log.info(f"  Total rows to migrate: {total_rows:,}")

    # ── Step 2: Clear destination tables (child → parent) ────────────────────
    log.info("\n── Step 2/4: Clearing destination tables (child → parent) ──")
    with cloud_engine.begin() as conn:
        for table in TABLES_DELETE_ORDER:
            count = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar()
            conn.execute(text(f"DELETE FROM `{table}`"))
            log.info(f"  [{table}] Deleted {count:,} existing rows")

    # ── Step 3: Insert in dependency order (parent → child) ──────────────────
    log.info("\n── Step 3/4: Inserting data (parent → child order) ─────────")
    with cloud_engine.begin() as conn:
        for table in TABLES_INSERT_ORDER:
            rows = source_data[table]
            if not rows:
                log.info(f"  [{table}] No rows to insert — skipping")
                continue
            inserted = insert_batch(conn, table, rows)
            log.info(f"  [{table}] ✅ {inserted:,} rows inserted")

    # ── Step 4: Rebase AUTO_INCREMENT + collision test ────────────────────────
    log.info("\n── Step 4/4: AUTO_INCREMENT rebase + allocator test ─────────")
    with cloud_engine.begin() as conn:
        for table in AUTO_INC_TABLES:
            max_id = rebase_auto_increment(conn, table)
            test_allocator(conn, table, max_id)

    # ── Verification ─────────────────────────────────────────────────────────
    with local_engine.connect() as local_conn, cloud_engine.connect() as cloud_conn:
        all_passed = verify(local_conn, cloud_conn)

    log.info("\n" + "=" * 65)
    if all_passed:
        log.info("  ✅ MIGRATION COMPLETE — all verification checks passed.")
        log.info("  Next steps:")
        log.info("    1. Update local .env with TiDB Cloud credentials")
        log.info("    2. Update GitHub Secrets (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME)")
        log.info("    3. Re-enable GitHub Actions workflow")
    else:
        log.error("  ❌ MIGRATION FAILED — one or more verification checks failed.")
        log.error("  Do NOT update .env or GitHub Secrets until all checks pass.")
        log.error("  Re-run this script after investigating the failures above.")
    log.info("=" * 65)

    if not all_passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

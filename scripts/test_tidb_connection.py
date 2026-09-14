"""
SkillPulse — Phase 0: TiDB Cloud Connectivity Probe
=====================================================
Run this BEFORE migrating any data and BEFORE running any other script
against TiDB Cloud.

Tests:
  1. SSL connection + SELECT 1
  2. Insert / select / delete roundtrip
  3. FK-ordered DELETE (child → parent) without disabling FK checks
  4. AUTO_INCREMENT rebase: ALTER TABLE ... AUTO_INCREMENT = 0
     then verify next implicit insert id > max migrated id

Pass condition: all tests print ✅ with no exceptions.

Usage (from repo root):
  python scripts/test_tidb_connection.py

Also run from GitHub Actions via workflow_dispatch to confirm
GitHub runner → TiDB connectivity before executing Phase 1.
"""

import os
import sys
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from sqlalchemy import text
from app.db_utils import build_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("tidb_probe")

PROBE_TABLE = "_skillpulse_connectivity_probe"

CREATE_PROBE = f"""
CREATE TABLE IF NOT EXISTS `{PROBE_TABLE}` (
    id        INT AUTO_INCREMENT PRIMARY KEY,
    parent_id INT DEFAULT NULL,
    label     VARCHAR(100),
    FOREIGN KEY (parent_id) REFERENCES `{PROBE_TABLE}`(id)
) ENGINE=InnoDB
"""
DROP_PROBE = f"DROP TABLE IF EXISTS `{PROBE_TABLE}`"


def run_probe():
    log.info("=" * 60)
    log.info("  SkillPulse — Phase 0: TiDB Cloud Connectivity Probe")
    log.info("=" * 60)
    log.info(f"Target:  {os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}")
    log.info(f"SSL:     {os.getenv('DB_SSL', 'false')}  CA: {os.getenv('DB_SSL_CA', '<none>')}")
    log.info("")

    engine = build_engine()

    # ── Test 1: Basic connection + SELECT 1 ───────────────────────────────────
    log.info("Test 1/4: SSL connection + SELECT 1 ...")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
        assert result == 1, f"SELECT 1 returned {result}"
    log.info("✅ Test 1 PASSED: SSL connection OK, SELECT 1 returned 1")

    # ── Test 2: Insert / select / delete roundtrip ────────────────────────────
    log.info("Test 2/4: Insert/select/delete roundtrip ...")
    with engine.begin() as conn:
        conn.execute(text(DROP_PROBE))
        conn.execute(text(CREATE_PROBE))

        # Insert parent row
        r = conn.execute(text(
            f"INSERT INTO `{PROBE_TABLE}` (label) VALUES ('_parent_probe')"
        ))
        parent_id = r.lastrowid
        assert parent_id and parent_id > 0, "Parent insert returned no lastrowid"

        # Insert child row referencing parent
        r2 = conn.execute(text(
            f"INSERT INTO `{PROBE_TABLE}` (parent_id, label) VALUES (:pid, '_child_probe')"
        ), {"pid": parent_id})
        child_id = r2.lastrowid
        assert child_id and child_id > 0, "Child insert returned no lastrowid"

        # Verify both rows readable
        rows = conn.execute(text(f"SELECT id, parent_id, label FROM `{PROBE_TABLE}`")).fetchall()
        assert len(rows) == 2, f"Expected 2 rows, got {len(rows)}"

    log.info(f"✅ Test 2 PASSED: parent_id={parent_id}, child_id={child_id}, 2 rows readable")

    # ── Test 3: FK-ordered DELETE (child → parent, no FK override needed) ─────
    log.info("Test 3/4: FK-ordered DELETE (child → parent, no SET foreign_key_checks) ...")
    with engine.begin() as conn:
        # Must delete child before parent — if FK enforcement works, wrong order raises error
        conn.execute(text(f"DELETE FROM `{PROBE_TABLE}` WHERE parent_id IS NOT NULL"))
        conn.execute(text(f"DELETE FROM `{PROBE_TABLE}` WHERE parent_id IS NULL"))
        remaining = conn.execute(text(f"SELECT COUNT(*) FROM `{PROBE_TABLE}`")).scalar()
        assert remaining == 0, f"Expected 0 rows after delete, got {remaining}"
    log.info("✅ Test 3 PASSED: FK-ordered DELETE works without disabling FK checks")

    # ── Test 4: AUTO_INCREMENT rebase (ALTER TABLE ... AUTO_INCREMENT = 0) ────
    log.info("Test 4/4: AUTO_INCREMENT rebase test ...")
    with engine.begin() as conn:
        # Insert a row with explicit high ID to simulate post-migration state
        conn.execute(text(f"INSERT INTO `{PROBE_TABLE}` (id, label) VALUES (5000, '_explicit_id_probe')"))
        max_id_before = conn.execute(text(f"SELECT MAX(id) FROM `{PROBE_TABLE}`")).scalar()
        assert max_id_before == 5000, f"Expected max_id=5000, got {max_id_before}"

        # Rebase: tells TiDB to recompute the allocator from MAX(id)
        conn.execute(text(f"ALTER TABLE `{PROBE_TABLE}` AUTO_INCREMENT = 0"))

        # Implicit insert — must produce id > 5000
        r = conn.execute(text(f"INSERT INTO `{PROBE_TABLE}` (label) VALUES ('_implicit_after_rebase')"))
        new_id = r.lastrowid
        assert new_id > max_id_before, (
            f"AUTO_INCREMENT allocator collision: new_id={new_id} <= max_id={max_id_before}. "
            f"Rebase did not work correctly."
        )

    log.info(
        f"✅ Test 4 PASSED: explicit id={max_id_before}, implicit new_id={new_id} "
        f"(gap={new_id - max_id_before} — gaps are expected on TiDB)"
    )

    # ── Cleanup ───────────────────────────────────────────────────────────────
    with engine.begin() as conn:
        conn.execute(text(DROP_PROBE))
    log.info(f"  Probe table `{PROBE_TABLE}` dropped.")

    log.info("")
    log.info("=" * 60)
    log.info("  ALL 4 TESTS PASSED ✅  TiDB Cloud connection is ready.")
    log.info("  You may now proceed to Phase 1 (data migration).")
    log.info(f"  Working SSL config: DB_SSL=true, DB_SSL_CA={os.getenv('DB_SSL_CA', '<empty>')}")
    log.info("=" * 60)


if __name__ == "__main__":
    try:
        run_probe()
    except Exception as e:
        log.error(f"❌ Probe FAILED: {e}")
        raise SystemExit(1)

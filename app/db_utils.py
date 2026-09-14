"""
SkillPulse — Centralized Database Engine Factory
=================================================
Single source of truth for all SQLAlchemy engine creation.
All six connection points (FastAPI, ingestion, snapshot, Streamlit,
retrain, drift monitor) import build_engine() from here.

SSL follows TiDB Cloud's documented PyMySQL configuration.
Relative CA paths are resolved from the project root so scripts
can be launched from any working directory.
"""

import os
import logging
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

logger = logging.getLogger(__name__)

# Resolved once at import time — always points to repo root regardless of cwd
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def build_engine(pool_pre_ping: bool = True):
    """
    Build and return a SQLAlchemy engine using environment variables.

    Environment variables:
        DB_USER        — exact username from TiDB Connect dialog (includes prefix)
        DB_PASSWORD    — password (URL.create handles special chars: @, :, /, #)
        DB_HOST        — hostname
        DB_PORT        — port (3306 for local MySQL; 4000 for TiDB Cloud)
        DB_NAME        — database name (default: skillpulse)
        DB_SSL         — set to 'true' to enable SSL (required for TiDB Cloud)
        DB_SSL_CA      — path to CA cert file, e.g. 'certs/tidb-ca.pem'.
                         Relative paths are resolved from the project root,
                         not the working directory — safe even when a script
                         is launched from a subdirectory.
        DB_AUTO_CREATE — set to 'true' for local MySQL dev to auto-create the
                         database if it does not exist. Never set for TiDB Cloud.

    Pool settings:
        pool_pre_ping=True  — verify connections before use (detects stale connections)
        pool_recycle=300    — recycle connections every 5 min; TiDB Cloud Starter
                              can close idle connections after 5 minutes of inactivity,
                              so this prevents 'Lost connection' errors.
    """
    url = URL.create(
        drivername="mysql+pymysql",
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME", "skillpulse"),
    )

    connect_args = {}
    if os.getenv("DB_SSL", "false").lower() == "true":
        # TiDB Cloud documented PyMySQL SSL parameters
        connect_args["ssl_verify_cert"] = True
        connect_args["ssl_verify_identity"] = True
        db_ssl_ca = os.getenv("DB_SSL_CA", "").strip()
        if db_ssl_ca:
            ca_path = Path(db_ssl_ca)
            if not ca_path.is_absolute():
                ca_path = _PROJECT_ROOT / ca_path   # resolve relative to project root
            connect_args["ssl_ca"] = str(ca_path)
            logger.debug(f"SSL enabled. CA=<{ca_path}>")
        else:
            logger.debug("SSL enabled. CA=<system trust store>")

    return create_engine(
        url,
        pool_pre_ping=pool_pre_ping,
        pool_recycle=300,        # recycle before TiDB Cloud Starter's 5-min idle timeout
        connect_args=connect_args,
    )

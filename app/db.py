"""
SkillPulse — FastAPI Database Session
======================================
Provides the SQLAlchemy session dependency used by FastAPI route handlers.
Engine creation is delegated to app.db_utils.build_engine() which handles
SSL, pool_recycle, and URL encoding centrally for all connection points.
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv
from urllib.parse import quote_plus

from app.db_utils import build_engine

load_dotenv(dotenv_path=".env")

# Local MySQL dev only: auto-create the database if it doesn't exist.
# Controlled by DB_AUTO_CREATE=true in .env.
# Never set for TiDB Cloud — the database must already exist there.
def auto_create_db():
    """Automatically creates the MySQL database if it does not exist yet (local dev only)."""
    try:
        DB_USER     = os.getenv("DB_USER", "root")
        DB_PASSWORD = os.getenv("DB_PASSWORD", "")
        DB_HOST     = os.getenv("DB_HOST", "localhost")
        DB_PORT     = os.getenv("DB_PORT", "3306")
        DB_NAME     = os.getenv("DB_NAME", "skillpulse")
        server_url = f"mysql+pymysql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}"
        server_engine = create_engine(server_url, isolation_level="AUTOCOMMIT")
        with server_engine.connect() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {DB_NAME};"))
    except Exception:
        pass  # If DB connection fails (e.g. MySQL not running), let main error handling report it


if os.getenv("DB_AUTO_CREATE", "false").lower() == "true":
    auto_create_db()


engine = build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency that yields a database session and closes it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

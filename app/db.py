import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv(dotenv_path=".env")

DB_USER     = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = os.getenv("DB_PORT", "3306")
DB_NAME     = os.getenv("DB_NAME", "skillpulse")

def auto_create_db():
    """Automatically creates the MySQL database if it does not exist yet on a new PC."""
    try:
        server_url = f"mysql+pymysql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}"
        server_engine = create_engine(server_url, isolation_level="AUTOCOMMIT")
        with server_engine.connect() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {DB_NAME};"))
    except Exception:
        pass  # If DB connection fails (e.g. MySQL not running), let main error handling report it

auto_create_db()

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """FastAPI dependency that yields a database session and closes it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

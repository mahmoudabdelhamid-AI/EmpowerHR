"""
Database configuration for EmpowerHR backend.

Sets up the SQLAlchemy engine, session factory, and declarative base
used across the application. Uses SQLite as the database engine.
"""

import os

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# STEP 13 (D-2): anchor all persistent storage (SQLite file,
# uploads/, cv_uploads/) to a single, stable directory instead of
# relying on the process's current working directory. Defaults to
# this file's own directory (project root), which is what the app
# already effectively used when started from the project root —
# this makes that assumption explicit and safe regardless of CWD.
# EMPOWERHR_DATA_DIR lets a deployment point this at a different
# (e.g. persistent/mounted) directory without any other code change.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(
    os.environ.get("EMPOWERHR_DATA_DIR", BASE_DIR)
)
os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "database.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# SQLite requires this connect argument when used with multiple threads
# (FastAPI can handle requests in different threads)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# SQLite does not enforce FOREIGN KEY constraints by default -- it must be
# turned on per-connection. This applies PRAGMA foreign_keys=ON to every
# DBAPI connection the engine opens, so the ForeignKey constraints already
# defined in models.py (Application.user_id / job_id) are actually
# enforced. Guarded to SQLite only so non-SQLite databases are unaffected.
if engine.dialect.name == "sqlite":
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# Session factory used to create database sessions per request
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class that all SQLAlchemy models will inherit from
Base = declarative_base()


def get_db():
    """
    Dependency that provides a database session to path operations
    and ensures it is closed after the request finishes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

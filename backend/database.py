"""
Database configuration for EmpowerHR backend.

Sets up the SQLAlchemy engine, session factory, and declarative base
used across the application. Uses SQLite as the database engine.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# SQLite database URL (creates database.db in the backend folder)
SQLALCHEMY_DATABASE_URL = "sqlite:///./database.db"

# SQLite requires this connect argument when used with multiple threads
# (FastAPI can handle requests in different threads)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

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

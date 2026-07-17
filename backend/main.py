"""
Entry point for the EmpowerHR backend.

Configures the FastAPI application, initializes the SQLite database
via SQLAlchemy, and includes the (currently empty) API router.

Run with:
    uvicorn main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, SessionLocal, engine
import models# noqa: F401  (imported so models are registered with Base.metadata)
from models import Job  
from routes import router
# Create all database tables registered with Base.metadata.

Base.metadata.create_all(bind=engine)


def _seed_jobs():
    db = SessionLocal()
    try:
        if db.query(Job).first() is None:
            db.add_all([
                Job(
                    title="Frontend Developer",
                    company="Tech Solutions",
                    location="Cairo",
                    salary="8000 EGP",
                ),
                Job(
                    title="Backend Developer",
                    company="Future Systems",
                    location="Alexandria",
                    salary="10000 EGP",
                ),
            ])
            db.commit()
    finally:
        db.close()


_seed_jobs()

app = FastAPI(
    title="EmpowerHR API",
    description="Backend API for the EmpowerHR recruitment platform.",
    version="0.1.0",
)

# Allow the frontend (served from a different origin during development)
# to make requests to this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the API router (no endpoints defined yet)
app.include_router(router)

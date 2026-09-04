"""
Entry point for the EmpowerHR backend.

Configures the FastAPI application, initializes the SQLite database
via SQLAlchemy, and includes the API router.

Development (auto-reload):
    uvicorn main:app --reload

Production (single worker -- see DEPLOYMENT.md for the full
runbook, including why this app must not run with multiple
workers):
    uvicorn main:app --host 0.0.0.0 --port 8000
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import Base, SessionLocal, engine
import models# noqa: F401  (imported so models are registered with Base.metadata)
from models import Job  
from routes import router, UPLOAD_DIR
# Create all database tables registered with Base.metadata.

Base.metadata.create_all(bind=engine)

# STEP 13 (D-1): demo job seeding must never happen implicitly in
# production. Off by default; requires an explicit, deliberate
# opt-in, matching the ALLOW_DEV_JWT_SECRET pattern already used
# for the JWT secret fallback (auth_utils.py, STEP 12 H-1).
SEED_DEMO_DATA = os.getenv("SEED_DEMO_DATA", "false").strip().lower() == "true"


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


if SEED_DEMO_DATA:
    _seed_jobs()

app = FastAPI(
    title="EmpowerHR API",
    description="Backend API for the EmpowerHR recruitment platform.",
    version="0.1.0",
)

# Allow the frontend (served from a different origin during development)
# to make requests to this API.
# STEP 13 (D-6): allowed CORS origins are environment-driven so
# production can supply its real frontend origin(s) without a code
# change. ALLOWED_ORIGINS is a comma-separated list. Whitespace
# around each entry and empty entries (e.g. from a stray trailing
# comma) are stripped/discarded. If the variable is unset, empty,
# or contains no usable entries after parsing, the original
# localhost defaults are preserved unchanged -- this keeps local
# development working exactly as before with zero configuration.
#
# Note: allow_credentials=True below means a literal "*" origin
# will NOT work correctly per the CORS spec even though
# CORSMiddleware accepts it -- browsers reject a wildcard
# Access-Control-Allow-Origin when credentials are involved.
# ALLOWED_ORIGINS must list explicit origin(s), not "*".
_DEFAULT_ALLOWED_ORIGINS = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:3000",
    "http://localhost:3000",
]


def _get_allowed_origins():
    raw = os.environ.get("ALLOWED_ORIGINS", "")
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return origins if origins else _DEFAULT_ALLOWED_ORIGINS


ALLOWED_ORIGINS = _get_allowed_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded profile photos (see routes.py: UPLOAD_DIR) at /uploads/<file>
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


# STEP 12 (M-3): baseline security response headers on every response.
# Deliberately minimal -- no CSP/HSTS here, since those need
# production-domain/HTTPS context that's out of scope for this change.
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# Include the API router
app.include_router(router)

"""
STEP 12 security-regression tests.

Covers only the six STEP 12 findings implemented in this pass:
  - H-1: JWT secret fail-closed behavior (auth_utils.py)
  - H-3: profile-photo upload size/content validation (routes.py)
  - M-1: minimum password length (schemas.py)
  - H-2: rate limiting on /login, /register, /employer/register (routes.py)
  - M-3: baseline security response headers (main.py)

Follows the exact test-isolation pattern already established by
test_profile_auth.py / test_candidate_profile_cv.py: a bare FastAPI()
app built from routes.router, an isolated in-memory SQLite database via
dependency_overrides[get_db], and main.py is never imported -- with one
narrow, explicitly-documented exception below for the M-3 header test,
which needs the actual middleware registered on the real `app` object.
"""

import io
import os
import subprocess
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from auth_utils import create_access_token
from database import Base, get_db
from models import User
from routes import router


# ---------------------------------------------------------------------------
# Shared fixtures (isolated in-memory DB, matching the existing pattern)
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_session(monkeypatch, tmp_path):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    import routes as routes_module
    monkeypatch.setattr(routes_module, "UPLOAD_DIR", str(tmp_path))

    session = TestingSessionLocal()
    try:
        yield session, TestingSessionLocal
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session):
    _, TestingSessionLocal = db_session

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture()
def user_a(db_session):
    from pwdlib import PasswordHash
    password_hash = PasswordHash.recommended()
    session, _ = db_session
    user = User(full_name="User A", email="usera@example.com", password=password_hash.hash("correct-horse-battery"))
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def auth_header(user):
    token = create_access_token(user_id=user.id, email=user.email)
    return {"Authorization": f"Bearer {token}"}


def _real_png_bytes():
    return b"\x89PNG\r\n\x1a\n" + b"real-png-signature-then-arbitrary-bytes"


# ---------------------------------------------------------------------------
# H-1: JWT secret fail-closed
# ---------------------------------------------------------------------------

def _project_dir():
    return os.path.dirname(os.path.abspath(__file__))


def test_auth_utils_fails_closed_without_jwt_secret_or_dev_opt_in():
    env = {
        k: v for k, v in os.environ.items()
        if k not in ("JWT_SECRET_KEY", "ENVIRONMENT", "ALLOW_DEV_JWT_SECRET")
    }
    result = subprocess.run(
        [sys.executable, "-c", "import auth_utils"],
        cwd=_project_dir(),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "JWT_SECRET_KEY" in result.stderr


def test_auth_utils_allows_explicit_dev_opt_in_fallback():
    env = {k: v for k, v in os.environ.items() if k != "JWT_SECRET_KEY"}
    env["ENVIRONMENT"] = "development"
    env["ALLOW_DEV_JWT_SECRET"] = "true"
    result = subprocess.run(
        [sys.executable, "-c", "import auth_utils; print('OK')"],
        cwd=_project_dir(),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "OK" in result.stdout


def test_auth_utils_succeeds_with_explicit_jwt_secret():
    env = dict(os.environ)
    env["JWT_SECRET_KEY"] = "some-explicit-production-secret"
    env.pop("ENVIRONMENT", None)
    result = subprocess.run(
        [sys.executable, "-c", "import auth_utils; print('OK')"],
        cwd=_project_dir(),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "OK" in result.stdout


# ---------------------------------------------------------------------------
# H-3: profile photo upload hardening
# ---------------------------------------------------------------------------

def test_upload_photo_oversized_rejected(client, user_a):
    from routes import MAX_PHOTO_SIZE_BYTES
    oversized = _real_png_bytes() + b"A" * MAX_PHOTO_SIZE_BYTES
    response = client.post(
        "/profile/photo",
        headers=auth_header(user_a),
        files={"file": ("photo.png", io.BytesIO(oversized), "image/png")},
    )
    assert response.status_code == 400


def test_upload_photo_content_mismatch_rejected(client, user_a):
    response = client.post(
        "/profile/photo",
        headers=auth_header(user_a),
        files={"file": ("photo.png", io.BytesIO(b"this is not a real png"), "image/png")},
    )
    assert response.status_code == 400


def test_upload_photo_valid_content_still_succeeds(client, user_a):
    response = client.post(
        "/profile/photo",
        headers=auth_header(user_a),
        files={"file": ("photo.png", io.BytesIO(_real_png_bytes()), "image/png")},
    )
    assert response.status_code == 200
    assert response.json()["profile_image"].startswith("/uploads/")


# ---------------------------------------------------------------------------
# M-1: minimum password length
# ---------------------------------------------------------------------------

def test_register_rejects_short_password(client):
    response = client.post("/register", json={
        "full_name": "Short Pw",
        "email": "shortpw@example.com",
        "password": "abc123",
    })
    assert response.status_code == 422


def test_register_accepts_password_at_minimum_length(client):
    response = client.post("/register", json={
        "full_name": "Min Pw",
        "email": "minpw@example.com",
        "password": "abcd1234",
    })
    assert response.status_code == 200


def test_employer_register_rejects_short_password(client):
    response = client.post("/employer/register", json={
        "full_name": "Short Pw Employer",
        "email": "shortpwemployer@example.com",
        "password": "abc123",
        "company_name": "TestCo",
    })
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# H-2: rate limiting
# ---------------------------------------------------------------------------

def test_login_rate_limited_after_repeated_attempts(client, user_a):
    for _ in range(5):
        response = client.post("/login", json={"email": user_a.email, "password": "wrong-password"})
        assert response.status_code == 401

    response = client.post("/login", json={"email": user_a.email, "password": "wrong-password"})
    assert response.status_code == 429


def test_register_rate_limit_does_not_block_normal_single_use(client):
    response = client.post("/register", json={
        "full_name": "Normal User",
        "email": "normaluser@example.com",
        "password": "abcd1234",
    })
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# M-3: security headers
# ---------------------------------------------------------------------------

def test_security_headers_present_on_response():
    # Deliberate, narrow exception to the "never import main.py" pattern
    # used elsewhere in this test suite: the M-3 middleware is registered
    # directly on the `app` object in main.py, so verifying it requires
    # the real app. Base.metadata.create_all()/_seed_jobs() are both
    # idempotent/non-destructive against the real database.db, so this
    # does not corrupt or depend on any particular pre-existing state.
    import main as main_module

    with TestClient(main_module.app) as test_client:
        response = test_client.get("/jobs")

    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"

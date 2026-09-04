"""
Regression tests for JWT-based authorization (Step 7.4).

Covers:
    - GET /profile requires a valid JWT and returns only the caller's
      own profile, ignoring any user_id supplied by the client.
    - POST /profile/photo requires a valid JWT and updates only the
      caller's own record.
    - The already-JWT-protected endpoints (POST /jobs/{id}/apply,
      GET /applications) remain protected.

Test isolation:
    These tests build their own FastAPI() app directly from the
    existing `routes.router` and override the `get_db` dependency with
    an isolated in-memory SQLite database (via SQLAlchemy's StaticPool).
    `main.py` is never imported, so its startup side effects
    (Base.metadata.create_all against the real database.db, and job
    seeding) never run. The real database.db used by the running
    application is never opened, created, or written to by this file.

    Profile-photo uploads are redirected to a pytest tmp_path via
    monkeypatch on routes.UPLOAD_DIR (an in-memory attribute patch for
    the duration of a single test only) so tests never write into the
    project's real uploads/ directory.

No production code is modified to make these tests pass. The only
"override" involved is FastAPI's standard `dependency_overrides`
mechanism, which is the normal, documented way to test FastAPI apps.
"""

import io

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import routes as routes_module
from auth_utils import create_access_token
from database import Base, get_db
from models import Job, User
from routes import router


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_session(monkeypatch, tmp_path):
    """An isolated, in-memory SQLite database, fresh for each test.

    StaticPool keeps a single underlying connection alive for the engine's
    lifetime, so every Session created from it (including the ones opened
    per-request inside the app via the overridden get_db) sees the same
    data. This database is never persisted to disk and is completely
    separate from the project's real database.db.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    # Redirect profile-photo uploads to a throwaway temp directory instead
    # of the real project's uploads/ folder. This patches the in-memory
    # module attribute for the duration of this test only -- it does not
    # edit routes.py.
    monkeypatch.setattr(routes_module, "UPLOAD_DIR", str(tmp_path))

    session = TestingSessionLocal()
    try:
        yield session, TestingSessionLocal
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session):
    """A TestClient wired to the isolated test database.

    Builds its own FastAPI() app from the existing routes.router rather
    than importing main.py, so main.py's startup side effects never run
    against the real database.db.
    """
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
    session, _ = db_session
    user = User(full_name="User A", email="usera@example.com", password="not-used")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture()
def user_b(db_session):
    session, _ = db_session
    user = User(full_name="User B", email="userb@example.com", password="not-used")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture()
def sample_job(db_session):
    session, _ = db_session
    job = Job(title="Backend Developer", company="Acme", location="Cairo", salary="10000 EGP")
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def auth_header(user):
    token = create_access_token(user_id=user.id, email=user.email)
    return {"Authorization": f"Bearer {token}"}


def tampered_token_header(user):
    """A syntactically JWT-shaped but invalid (signature-broken) token."""
    token = create_access_token(user_id=user.id, email=user.email)
    broken = token[:-1] + ("B" if token.endswith("A") else "A")
    return {"Authorization": f"Bearer {broken}"}


def tiny_png_file():
    # STEP 12 (H-3): upload_profile_photo now validates content against
    # a magic-byte signature, so this fixture must start with real PNG
    # magic bytes for the "valid token succeeds" test to still get a
    # 200 response.
    return ("photo.png", io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"rest-of-fake-png-data"), "image/png")


# ---------------------------------------------------------------------------
# GET /profile
# ---------------------------------------------------------------------------

def test_get_profile_without_token_returns_401(client):
    response = client.get("/profile")
    assert response.status_code == 401


def test_get_profile_with_valid_token_returns_own_profile(client, user_a):
    response = client.get("/profile", headers=auth_header(user_a))
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == user_a.id
    assert body["email"] == user_a.email
    assert body["full_name"] == user_a.full_name


def test_get_profile_with_invalid_token_returns_401(client, user_a):
    response = client.get("/profile", headers=tampered_token_header(user_a))
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /profile/photo
# ---------------------------------------------------------------------------

def test_upload_photo_without_token_returns_401(client):
    response = client.post("/profile/photo", files={"file": tiny_png_file()})
    assert response.status_code == 401


def test_upload_photo_with_valid_token_succeeds(client, user_a):
    response = client.post(
        "/profile/photo",
        headers=auth_header(user_a),
        files={"file": tiny_png_file()},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == user_a.id
    assert body["profile_image"] is not None
    assert body["profile_image"].startswith("/uploads/")


def test_upload_photo_with_invalid_token_returns_401(client, user_a):
    response = client.post(
        "/profile/photo",
        headers=tampered_token_header(user_a),
        files={"file": tiny_png_file()},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# User A cannot reach User B's profile
# ---------------------------------------------------------------------------

def test_user_a_token_ignores_supplied_user_id_and_returns_own_profile(client, user_a, user_b):
    # user_id is no longer part of the endpoint's contract (Step 7.3).
    # Supplying one anyway must have no effect: identity must come
    # entirely from the JWT, never from client-supplied input.
    response = client.get(f"/profile?user_id={user_b.id}", headers=auth_header(user_a))
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == user_a.id
    assert body["email"] == user_a.email
    assert body["id"] != user_b.id


# ---------------------------------------------------------------------------
# Other already-protected endpoints remain protected
# ---------------------------------------------------------------------------

def test_apply_to_job_without_token_returns_401(client, sample_job):
    response = client.post(f"/jobs/{sample_job.id}/apply")
    assert response.status_code == 401


def test_get_applications_without_token_returns_401(client):
    response = client.get("/applications")
    assert response.status_code == 401
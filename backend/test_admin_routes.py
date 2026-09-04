"""
Tests for Step 11 (Admin & Moderation, MVP scope). Follows the exact
test-isolation pattern established by test_employer_routes.py: a bare
FastAPI() app built from routes.router, an isolated in-memory SQLite
database via dependency_overrides[get_db] (with the PRAGMA
foreign_keys=ON connect listener), and main.py is never imported.

Also covers fix_admin_columns.py's idempotency in isolation, against a
disposable on-disk SQLite file (never the project's real database.db),
using the same check-before-acting migration pattern already exercised
implicitly by the other fix_*_column.py scripts.
"""

import importlib
import sqlite3

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from auth_utils import create_access_token
from database import Base, get_db
from models import Job, User
from routes import router


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

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


def _make_user(session, **kwargs):
    defaults = dict(full_name="User", email="user@example.com", password="not-used", role="candidate")
    defaults.update(kwargs)
    user = User(**defaults)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture()
def candidate(db_session):
    session, _ = db_session
    return _make_user(session, full_name="Candidate", email="candidate@example.com", role="candidate")


@pytest.fixture()
def employer(db_session):
    session, _ = db_session
    return _make_user(session, full_name="Employer", email="employer@example.com", role="employer", company_name="Acme")


@pytest.fixture()
def admin(db_session):
    session, _ = db_session
    return _make_user(session, full_name="Admin", email="admin@example.com", role="admin")


@pytest.fixture()
def job_owned_by_employer(db_session, employer):
    session, _ = db_session
    job = Job(title="Dev", company="Acme", location="Cairo", salary="1000", employment_type="Full-time",
              employer_id=employer.id, is_active=True)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


@pytest.fixture()
def inactive_job_owned_by_employer(db_session, employer):
    session, _ = db_session
    job = Job(title="Closed Role", company="Acme", location="Cairo", salary="1000", employment_type="Full-time",
              employer_id=employer.id, is_active=False)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


@pytest.fixture()
def legacy_job(db_session):
    session, _ = db_session
    job = Job(title="Legacy Role", company="Unowned Co", location="Cairo", salary="1000", employment_type="Full-time",
              employer_id=None, is_active=True)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def auth_header(user):
    token = create_access_token(user_id=user.id, email=user.email)
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# GET /admin/users
# ---------------------------------------------------------------------------

def test_list_users_no_token_401(client):
    assert client.get("/admin/users").status_code == 401


def test_list_users_candidate_403(client, candidate):
    assert client.get("/admin/users", headers=auth_header(candidate)).status_code == 403


def test_list_users_employer_403(client, employer):
    assert client.get("/admin/users", headers=auth_header(employer)).status_code == 403


def test_list_users_admin_success_all_roles_no_password(client, admin, candidate, employer):
    response = client.get("/admin/users", headers=auth_header(admin))
    assert response.status_code == 200
    users = response.json()
    ids = {u["id"] for u in users}
    assert admin.id in ids
    assert candidate.id in ids
    assert employer.id in ids

    roles = {u["role"] for u in users}
    assert {"admin", "candidate", "employer"} <= roles

    for u in users:
        assert "password" not in u
        assert "is_active" in u


# ---------------------------------------------------------------------------
# PATCH /admin/users/{user_id}/status
# ---------------------------------------------------------------------------

def test_update_user_status_no_token_401(client, candidate):
    response = client.patch(f"/admin/users/{candidate.id}/status", json={"is_active": False})
    assert response.status_code == 401


def test_update_user_status_candidate_403(client, candidate, employer):
    response = client.patch(
        f"/admin/users/{employer.id}/status", headers=auth_header(candidate), json={"is_active": False}
    )
    assert response.status_code == 403


def test_update_user_status_employer_403(client, employer, candidate):
    response = client.patch(
        f"/admin/users/{candidate.id}/status", headers=auth_header(employer), json={"is_active": False}
    )
    assert response.status_code == 403


def test_update_user_status_admin_success(client, admin, candidate):
    response = client.patch(
        f"/admin/users/{candidate.id}/status", headers=auth_header(admin), json={"is_active": False}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == candidate.id
    assert body["is_active"] is False


def test_update_user_status_nonexistent_user_404(client, admin):
    response = client.patch("/admin/users/999999/status", headers=auth_header(admin), json={"is_active": False})
    assert response.status_code == 404


def test_update_user_status_ignores_extra_fields(client, admin, candidate):
    response = client.patch(
        f"/admin/users/{candidate.id}/status",
        headers=auth_header(admin),
        json={"is_active": True, "role": "admin", "company_name": "Hacked Co", "full_name": "Hacked"},
    )
    assert response.status_code == 200
    body = response.json()
    # role/company_name/full_name must be entirely unaffected -- only
    # is_active is a real field on UserStatusUpdate.
    assert body["role"] == "candidate"
    assert body["full_name"] == candidate.full_name
    assert body["company_name"] is None


def test_deactivated_user_cannot_log_in(client, admin, db_session):
    session, _ = db_session
    from pwdlib import PasswordHash
    password_hash = PasswordHash.recommended()
    user = User(
        full_name="Soon Deactivated",
        email="deactivateme@example.com",
        password=password_hash.hash("secret123"),
        role="candidate",
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    # Confirm login works before deactivation.
    pre_login = client.post("/login", json={"email": user.email, "password": "secret123"})
    assert pre_login.status_code == 200

    deactivate = client.patch(f"/admin/users/{user.id}/status", headers=auth_header(admin), json={"is_active": False})
    assert deactivate.status_code == 200

    post_login = client.post("/login", json={"email": user.email, "password": "secret123"})
    assert post_login.status_code == 401


# ---------------------------------------------------------------------------
# GET /admin/jobs
# ---------------------------------------------------------------------------

def test_list_jobs_no_token_401(client):
    assert client.get("/admin/jobs").status_code == 401


def test_list_jobs_candidate_403(client, candidate):
    assert client.get("/admin/jobs", headers=auth_header(candidate)).status_code == 403


def test_list_jobs_employer_403(client, employer):
    assert client.get("/admin/jobs", headers=auth_header(employer)).status_code == 403


def test_list_jobs_admin_includes_inactive_and_legacy(
    client, admin, job_owned_by_employer, inactive_job_owned_by_employer, legacy_job
):
    response = client.get("/admin/jobs", headers=auth_header(admin))
    assert response.status_code == 200
    ids = {j["id"] for j in response.json()}
    assert job_owned_by_employer.id in ids
    assert inactive_job_owned_by_employer.id in ids
    assert legacy_job.id in ids


# ---------------------------------------------------------------------------
# PATCH /admin/jobs/{job_id}/status
# ---------------------------------------------------------------------------

def test_update_job_status_no_token_401(client, job_owned_by_employer):
    response = client.patch(f"/admin/jobs/{job_owned_by_employer.id}/status", json={"is_active": False})
    assert response.status_code == 401


def test_update_job_status_candidate_403(client, candidate, job_owned_by_employer):
    response = client.patch(
        f"/admin/jobs/{job_owned_by_employer.id}/status", headers=auth_header(candidate), json={"is_active": False}
    )
    assert response.status_code == 403


def test_update_job_status_employer_403(client, employer, job_owned_by_employer):
    # Even the owning employer must go through the employer-scoped
    # PUT /employer/jobs/{id} endpoint -- not this admin-only one.
    response = client.patch(
        f"/admin/jobs/{job_owned_by_employer.id}/status", headers=auth_header(employer), json={"is_active": False}
    )
    assert response.status_code == 403


def test_update_job_status_admin_success_any_employer(client, admin, job_owned_by_employer, legacy_job):
    # Works on a job owned by a real employer...
    response = client.patch(
        f"/admin/jobs/{job_owned_by_employer.id}/status", headers=auth_header(admin), json={"is_active": False}
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    # ...and equally on a legacy/unowned job, confirming admin authority
    # is global and not ownership-scoped (unlike get_owned_job).
    response2 = client.patch(
        f"/admin/jobs/{legacy_job.id}/status", headers=auth_header(admin), json={"is_active": False}
    )
    assert response2.status_code == 200
    assert response2.json()["is_active"] is False


def test_update_job_status_nonexistent_job_404(client, admin):
    response = client.patch("/admin/jobs/999999/status", headers=auth_header(admin), json={"is_active": False})
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Migration idempotency (fix_admin_columns.py)
# ---------------------------------------------------------------------------

def test_migration_idempotent_and_non_destructive(tmp_path, monkeypatch):
    db_path = tmp_path / "migration_test.db"

    # Build a pre-Step-11 users table (no is_active column) with one
    # existing row, mirroring a real pre-migration database.
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE users ("
        "id INTEGER PRIMARY KEY, full_name VARCHAR NOT NULL, email VARCHAR NOT NULL UNIQUE, "
        "password VARCHAR NOT NULL, profile_image VARCHAR, "
        "role VARCHAR NOT NULL DEFAULT 'candidate', company_name VARCHAR"
        ");"
    )
    cur.execute(
        "INSERT INTO users (full_name, email, password, role) VALUES (?, ?, ?, ?);",
        ("Existing User", "existing@example.com", "hashed", "candidate"),
    )
    conn.commit()
    conn.close()

    fix_admin_columns = importlib.import_module("fix_admin_columns")
    monkeypatch.setattr(fix_admin_columns, "DB_PATH", str(db_path))

    # First run: column is missing, should be added without error.
    fix_admin_columns.main()

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(users);")
    columns = [row[1] for row in cur.fetchall()]
    assert "is_active" in columns

    cur.execute("SELECT is_active FROM users WHERE email = ?;", ("existing@example.com",))
    row = cur.fetchone()
    assert row is not None
    assert bool(row[0]) is True
    conn.close()

    # Second run: column already exists -- must be a no-op, no error.
    fix_admin_columns.main()

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("SELECT is_active FROM users WHERE email = ?;", ("existing@example.com",))
    row = cur.fetchone()
    assert bool(row[0]) is True
    conn.close()

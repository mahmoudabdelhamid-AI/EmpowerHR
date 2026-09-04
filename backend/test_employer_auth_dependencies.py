"""
Dependency-level tests for Step 9 employer authorization (Phase 9.2).

Tests get_current_employer and get_owned_job in isolation, via a
throwaway protected test route, before they are wired into any real
endpoint. Follows the exact test-isolation pattern established by
test_profile_auth.py: builds a bare FastAPI() app, overrides get_db
with an isolated in-memory SQLite database, and never imports main.py.
"""

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from auth_utils import create_access_token, get_current_employer, get_owned_job
from database import Base, get_db
from models import Job, User


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
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

    # Throwaway protected routes used only to exercise the dependencies.
    @app.get("/test/employer-only")
    def employer_only_route(current_employer: User = Depends(get_current_employer)):
        return {"id": current_employer.id, "role": current_employer.role}

    @app.get("/test/owned-job/{job_id}")
    def owned_job_route(job: Job = Depends(get_owned_job)):
        return {"id": job.id, "employer_id": job.employer_id}

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture()
def candidate(db_session):
    session, _ = db_session
    user = User(full_name="Candidate", email="candidate@example.com", password="x", role="candidate")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture()
def employer_a(db_session):
    session, _ = db_session
    user = User(full_name="Employer A", email="employera@example.com", password="x", role="employer", company_name="Acme")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture()
def employer_b(db_session):
    session, _ = db_session
    user = User(full_name="Employer B", email="employerb@example.com", password="x", role="employer", company_name="Globex")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture()
def job_owned_by_a(db_session, employer_a):
    session, _ = db_session
    job = Job(title="Dev", company="Acme", location="Cairo", salary="1", employer_id=employer_a.id, is_active=True)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


@pytest.fixture()
def legacy_unowned_job(db_session):
    session, _ = db_session
    job = Job(title="Legacy", company="Old Co", location="Cairo", salary="1", employer_id=None, is_active=True)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def auth_header(user):
    token = create_access_token(user_id=user.id, email=user.email)
    return {"Authorization": f"Bearer {token}"}


# --- get_current_employer -------------------------------------------------

def test_get_current_employer_no_token_returns_401(client):
    response = client.get("/test/employer-only")
    assert response.status_code == 401


def test_get_current_employer_candidate_token_returns_403(client, candidate):
    response = client.get("/test/employer-only", headers=auth_header(candidate))
    assert response.status_code == 403


def test_get_current_employer_employer_token_succeeds(client, employer_a):
    response = client.get("/test/employer-only", headers=auth_header(employer_a))
    assert response.status_code == 200
    assert response.json()["role"] == "employer"


# --- get_owned_job ----------------------------------------------------------

def test_get_owned_job_no_token_returns_401(client, job_owned_by_a):
    response = client.get(f"/test/owned-job/{job_owned_by_a.id}")
    assert response.status_code == 401


def test_get_owned_job_candidate_token_returns_403(client, candidate, job_owned_by_a):
    response = client.get(f"/test/owned-job/{job_owned_by_a.id}", headers=auth_header(candidate))
    assert response.status_code == 403


def test_get_owned_job_wrong_owner_returns_403(client, employer_b, job_owned_by_a):
    response = client.get(f"/test/owned-job/{job_owned_by_a.id}", headers=auth_header(employer_b))
    assert response.status_code == 403


def test_get_owned_job_correct_owner_succeeds(client, employer_a, job_owned_by_a):
    response = client.get(f"/test/owned-job/{job_owned_by_a.id}", headers=auth_header(employer_a))
    assert response.status_code == 200
    assert response.json()["id"] == job_owned_by_a.id


def test_get_owned_job_nonexistent_job_returns_404(client, employer_a):
    response = client.get("/test/owned-job/999999", headers=auth_header(employer_a))
    assert response.status_code == 404


def test_get_owned_job_legacy_unowned_job_returns_403_not_success(client, employer_a, legacy_unowned_job):
    # employer_id IS NULL must never equal any real employer's id.
    response = client.get(f"/test/owned-job/{legacy_unowned_job.id}", headers=auth_header(employer_a))
    assert response.status_code == 403

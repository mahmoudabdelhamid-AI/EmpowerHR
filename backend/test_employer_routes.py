"""
Authorization/IDOR + functional tests for the Step 9 employer endpoints
(Phases 9.3-9.6). Follows the exact test-isolation pattern established by
test_profile_auth.py: a bare FastAPI() app built from routes.router, an
isolated in-memory SQLite database via dependency_overrides[get_db], and
main.py is never imported.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from auth_utils import create_access_token
from database import Base, get_db
from models import Application, Job, User
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

    # SQLite disables FK enforcement by default per-connection. Mirrors
    # database.py's connect-event listener exactly so this test engine
    # enforces the same ForeignKey constraints (e.g. Application.job_id)
    # production does -- otherwise the DELETE-with-applications -> 409
    # test below would never actually hit an IntegrityError.
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
def employer_a(db_session):
    session, _ = db_session
    return _make_user(session, full_name="Employer A", email="employera@example.com", role="employer", company_name="Acme")


@pytest.fixture()
def employer_b(db_session):
    session, _ = db_session
    return _make_user(session, full_name="Employer B", email="employerb@example.com", role="employer", company_name="Globex")


@pytest.fixture()
def job_owned_by_a(db_session, employer_a):
    session, _ = db_session
    job = Job(title="Dev", company="Acme", location="Cairo", salary="1000", employment_type="Full-time",
              employer_id=employer_a.id, is_active=True)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


@pytest.fixture()
def inactive_job_owned_by_a(db_session, employer_a):
    session, _ = db_session
    job = Job(title="Closed Role", company="Acme", location="Cairo", salary="1000", employment_type="Full-time",
              employer_id=employer_a.id, is_active=False)
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


@pytest.fixture()
def application_on_job_a(db_session, candidate, job_owned_by_a):
    session, _ = db_session
    app_row = Application(user_id=candidate.id, job_id=job_owned_by_a.id, status="Pending")
    session.add(app_row)
    session.commit()
    session.refresh(app_row)
    return app_row


def auth_header(user):
    token = create_access_token(user_id=user.id, email=user.email)
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# 1. POST /employer/register (public)
# ---------------------------------------------------------------------------

def test_employer_register_success(client):
    response = client.post("/employer/register", json={
        "full_name": "New Employer",
        "email": "newemployer@example.com",
        "password": "secret123",
        "company_name": "NewCo",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "employer"
    assert body["company_name"] == "NewCo"
    assert "password" not in body


def test_employer_register_duplicate_email_returns_400(client, employer_a):
    response = client.post("/employer/register", json={
        "full_name": "Dup",
        "email": employer_a.email,
        "password": "secret123",
        "company_name": "Dup Co",
    })
    assert response.status_code == 400


def test_employer_login_reports_employer_role(client):
    client.post("/employer/register", json={
        "full_name": "Login Employer",
        "email": "loginemployer@example.com",
        "password": "secret123",
        "company_name": "LoginCo",
    })
    response = client.post("/login", json={"email": "loginemployer@example.com", "password": "secret123"})
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "employer"
    assert body["company_name"] == "LoginCo"


def test_candidate_login_reports_candidate_role(client):
    client.post("/register", json={
        "full_name": "Login Candidate",
        "email": "logincandidate@example.com",
        "password": "secret123",
    })
    response = client.post("/login", json={"email": "logincandidate@example.com", "password": "secret123"})
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "candidate"
    assert body["company_name"] is None


def test_employer_register_ignores_client_supplied_role(client):
    response = client.post("/employer/register", json={
        "full_name": "Sneaky",
        "email": "sneaky@example.com",
        "password": "secret123",
        "company_name": "Sneaky Co",
        "role": "admin",  # not a real field on EmployerCreate -- must be ignored
    })
    assert response.status_code == 200
    assert response.json()["role"] == "employer"


# ---------------------------------------------------------------------------
# 2. GET /employer/jobs
# ---------------------------------------------------------------------------

def test_list_employer_jobs_no_token_401(client):
    assert client.get("/employer/jobs").status_code == 401


def test_list_employer_jobs_candidate_403(client, candidate):
    assert client.get("/employer/jobs", headers=auth_header(candidate)).status_code == 403


def test_list_employer_jobs_returns_only_own_jobs(client, employer_a, employer_b, job_owned_by_a):
    response = client.get("/employer/jobs", headers=auth_header(employer_a))
    assert response.status_code == 200
    ids = [j["id"] for j in response.json()]
    assert job_owned_by_a.id in ids

    response_b = client.get("/employer/jobs", headers=auth_header(employer_b))
    assert response_b.status_code == 200
    assert job_owned_by_a.id not in [j["id"] for j in response_b.json()]


# ---------------------------------------------------------------------------
# 3. POST /employer/jobs
# ---------------------------------------------------------------------------

def test_create_job_no_token_401(client):
    assert client.post("/employer/jobs", json={
        "title": "X", "location": "Y", "salary": "Z", "employment_type": "Full-time",
    }).status_code == 401


def test_create_job_candidate_403(client, candidate):
    response = client.post("/employer/jobs", headers=auth_header(candidate), json={
        "title": "X", "location": "Y", "salary": "Z", "employment_type": "Full-time",
    })
    assert response.status_code == 403


def test_create_job_employer_success_and_company_derived(client, employer_a):
    response = client.post("/employer/jobs", headers=auth_header(employer_a), json={
        "title": "QA Engineer",
        "location": "Giza",
        "salary": "9000 EGP",
        "employment_type": "Full-time",
        "company": "Attacker-Supplied Co",   # must be ignored -- not a JobCreate field
        "employer_id": 9999,                  # must be ignored -- not a JobCreate field
        "is_active": False,                   # must be ignored -- not a JobCreate field
    })
    assert response.status_code == 200
    body = response.json()
    assert body["employer_id"] == employer_a.id
    assert body["is_active"] is True

    # Confirm company was derived server-side from the employer's
    # company_name, not the client-supplied value.
    listing = client.get("/employer/jobs", headers=auth_header(employer_a)).json()
    created = next(j for j in listing if j["id"] == body["id"])
    assert created["company"] == employer_a.company_name


# ---------------------------------------------------------------------------
# 4. PUT /employer/jobs/{job_id}
# ---------------------------------------------------------------------------

def test_update_job_no_token_401(client, job_owned_by_a):
    assert client.put(f"/employer/jobs/{job_owned_by_a.id}", json={"title": "New"}).status_code == 401


def test_update_job_candidate_403(client, candidate, job_owned_by_a):
    response = client.put(f"/employer/jobs/{job_owned_by_a.id}", headers=auth_header(candidate), json={"title": "New"})
    assert response.status_code == 403


def test_update_job_not_owner_403(client, employer_b, job_owned_by_a):
    response = client.put(f"/employer/jobs/{job_owned_by_a.id}", headers=auth_header(employer_b), json={"title": "New"})
    assert response.status_code == 403


def test_update_job_owner_success(client, employer_a, job_owned_by_a):
    response = client.put(f"/employer/jobs/{job_owned_by_a.id}", headers=auth_header(employer_a), json={
        "title": "Senior Dev", "is_active": False,
    })
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Senior Dev"
    assert body["is_active"] is False


# ---------------------------------------------------------------------------
# 5. DELETE /employer/jobs/{job_id}
# ---------------------------------------------------------------------------

def test_delete_job_no_token_401(client, job_owned_by_a):
    assert client.delete(f"/employer/jobs/{job_owned_by_a.id}").status_code == 401


def test_delete_job_candidate_403(client, candidate, job_owned_by_a):
    assert client.delete(f"/employer/jobs/{job_owned_by_a.id}", headers=auth_header(candidate)).status_code == 403


def test_delete_job_not_owner_403(client, employer_b, job_owned_by_a):
    assert client.delete(f"/employer/jobs/{job_owned_by_a.id}", headers=auth_header(employer_b)).status_code == 403


def test_delete_job_owner_no_applications_204(client, employer_a, job_owned_by_a):
    response = client.delete(f"/employer/jobs/{job_owned_by_a.id}", headers=auth_header(employer_a))
    assert response.status_code == 204
    # Confirm it's gone
    listing = client.get("/employer/jobs", headers=auth_header(employer_a)).json()
    assert job_owned_by_a.id not in [j["id"] for j in listing]


def test_delete_job_owner_with_applications_409(client, employer_a, job_owned_by_a, application_on_job_a):
    response = client.delete(f"/employer/jobs/{job_owned_by_a.id}", headers=auth_header(employer_a))
    assert response.status_code == 409
    # Confirm the job still exists afterward
    listing = client.get("/employer/jobs", headers=auth_header(employer_a)).json()
    assert job_owned_by_a.id in [j["id"] for j in listing]


# ---------------------------------------------------------------------------
# is_active behavior (Phase 9.4)
# ---------------------------------------------------------------------------

def test_public_jobs_excludes_inactive(client, job_owned_by_a, inactive_job_owned_by_a):
    response = client.get("/jobs")
    ids = [j["id"] for j in response.json()]
    assert job_owned_by_a.id in ids
    assert inactive_job_owned_by_a.id not in ids


def test_apply_to_inactive_job_returns_400(client, candidate, inactive_job_owned_by_a):
    response = client.post(f"/jobs/{inactive_job_owned_by_a.id}/apply", headers=auth_header(candidate))
    assert response.status_code == 400


def test_apply_to_active_job_still_works(client, candidate, job_owned_by_a):
    response = client.post(f"/jobs/{job_owned_by_a.id}/apply", headers=auth_header(candidate))
    assert response.status_code == 200


def test_public_jobs_still_includes_legacy_unowned_active_job(client, legacy_job):
    response = client.get("/jobs")
    ids = [j["id"] for j in response.json()]
    assert legacy_job.id in ids


def test_delete_legacy_unowned_job_by_real_employer_returns_403(client, employer_a, legacy_job):
    # employer_id IS NULL must never be treated as owned by any real
    # employer -- confirmed end-to-end through the actual DELETE route,
    # not just at the get_owned_job dependency level.
    response = client.delete(f"/employer/jobs/{legacy_job.id}", headers=auth_header(employer_a))
    assert response.status_code == 403
    # Confirm the legacy job was NOT deleted.
    still_public = [j["id"] for j in client.get("/jobs").json()]
    assert legacy_job.id in still_public


def test_applicants_for_legacy_unowned_job_returns_403(client, employer_a, legacy_job):
    response = client.get(f"/employer/jobs/{legacy_job.id}/applicants", headers=auth_header(employer_a))
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# 6. GET /employer/jobs/{job_id}/applicants
# ---------------------------------------------------------------------------

def test_applicants_no_token_401(client, job_owned_by_a):
    assert client.get(f"/employer/jobs/{job_owned_by_a.id}/applicants").status_code == 401


def test_applicants_candidate_403(client, candidate, job_owned_by_a):
    assert client.get(f"/employer/jobs/{job_owned_by_a.id}/applicants", headers=auth_header(candidate)).status_code == 403


def test_applicants_not_owner_403(client, employer_b, job_owned_by_a):
    assert client.get(f"/employer/jobs/{job_owned_by_a.id}/applicants", headers=auth_header(employer_b)).status_code == 403


def test_applicants_owner_success_and_field_scope(client, employer_a, job_owned_by_a, application_on_job_a, candidate):
    response = client.get(f"/employer/jobs/{job_owned_by_a.id}/applicants", headers=auth_header(employer_a))
    assert response.status_code == 200
    applicants = response.json()
    assert len(applicants) == 1
    applicant = applicants[0]
    assert applicant["full_name"] == candidate.full_name
    assert applicant["email"] == candidate.email
    assert applicant["application_id"] == application_on_job_a.id
    assert applicant["has_cv"] is False  # this fixture's candidate never uploaded a CV
    # Ensure no disallowed fields leak.
    allowed_keys = {"application_id", "job_id", "status", "date_applied", "full_name", "email", "profile_image", "has_cv"}
    assert set(applicant.keys()) <= allowed_keys
    assert "password" not in applicant


# ---------------------------------------------------------------------------
# 7. PATCH /employer/applications/{application_id}/status
# ---------------------------------------------------------------------------

def test_update_status_no_token_401(client, application_on_job_a):
    assert client.patch(
        f"/employer/applications/{application_on_job_a.id}/status", json={"status": "Reviewed"}
    ).status_code == 401


def test_update_status_candidate_403(client, candidate, application_on_job_a):
    response = client.patch(
        f"/employer/applications/{application_on_job_a.id}/status",
        headers=auth_header(candidate),
        json={"status": "Reviewed"},
    )
    assert response.status_code == 403


def test_update_status_wrong_employer_403(client, employer_b, application_on_job_a):
    # Application belongs to a job owned by employer_a; employer_b must
    # be rejected even though the URL contains no job_id.
    response = client.patch(
        f"/employer/applications/{application_on_job_a.id}/status",
        headers=auth_header(employer_b),
        json={"status": "Reviewed"},
    )
    assert response.status_code == 403


def test_update_status_owner_success(client, employer_a, application_on_job_a):
    response = client.patch(
        f"/employer/applications/{application_on_job_a.id}/status",
        headers=auth_header(employer_a),
        json={"status": "Interview"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "Interview"


def test_update_status_invalid_value_422(client, employer_a, application_on_job_a):
    response = client.patch(
        f"/employer/applications/{application_on_job_a.id}/status",
        headers=auth_header(employer_a),
        json={"status": "NotARealStatus"},
    )
    assert response.status_code == 422


def test_update_status_backwards_transition_allowed(client, employer_a, application_on_job_a):
    client.patch(f"/employer/applications/{application_on_job_a.id}/status",
                 headers=auth_header(employer_a), json={"status": "Accepted"})
    response = client.patch(f"/employer/applications/{application_on_job_a.id}/status",
                             headers=auth_header(employer_a), json={"status": "Pending"})
    assert response.status_code == 200
    assert response.json()["status"] == "Pending"


def test_candidate_sees_updated_status_via_existing_endpoint(client, candidate, employer_a, application_on_job_a):
    client.patch(f"/employer/applications/{application_on_job_a.id}/status",
                 headers=auth_header(employer_a), json={"status": "Accepted"})
    response = client.get("/applications", headers=auth_header(candidate))
    assert response.status_code == 200
    app_entry = next(a for a in response.json() if a["id"] == application_on_job_a.id)
    assert app_entry["status"] == "Accepted"

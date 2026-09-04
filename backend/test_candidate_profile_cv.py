"""
Tests for Step 10 (Candidate Profile & CV). Follows the exact
test-isolation pattern established by test_profile_auth.py /
test_employer_routes.py: a bare FastAPI() app built from routes.router,
an isolated in-memory SQLite database via dependency_overrides[get_db]
(with the PRAGMA foreign_keys=ON connect listener so FK-dependent
behavior is actually exercised, matching database.py), and main.py is
never imported.

File uploads (both UPLOAD_DIR and CV_UPLOAD_DIR) are redirected to a
pytest tmp_path via monkeypatch, exactly mirroring the existing
photo-upload test pattern in test_profile_auth.py, so tests never
touch the project's real uploads/ or cv_uploads/ directories.
"""

import io
import os
import zipfile

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import routes as routes_module
from auth_utils import create_access_token
from database import Base, get_db
from models import Application, CandidateProfile, Job, User
from routes import router


# ---------------------------------------------------------------------------
# File-content builders (valid + invalid, for content-validation tests)
# ---------------------------------------------------------------------------

def _pdf_bytes():
    return b"%PDF-1.4\n%mock pdf content for testing\n%%EOF"


def _doc_bytes():
    # Legacy binary Word files are OLE Compound Files -- all start with
    # this fixed 8-byte signature, which is exactly what the validator
    # checks for.
    return b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1" + b"\x00" * 64


def _docx_bytes():
    # A real, minimal Office Open XML zip containing word/document.xml,
    # which is the structural marker the validator looks for.
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("word/document.xml", "<xml>minimal</xml>")
        archive.writestr("[Content_Types].xml", "<Types/>")
    return buf.getvalue()


def _plaintext_bytes():
    return b"This is plain text, not a real PDF/DOC/DOCX file at all."


def _oversized_pdf_bytes():
    # Correct magic bytes, but past the 10MB cap.
    return b"%PDF-1.4\n" + b"A" * (10 * 1024 * 1024 + 1)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_session(monkeypatch, tmp_path):
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

    # Redirect both upload directories to disposable tmp_path
    # subdirectories -- never touch the project's real uploads/ or
    # cv_uploads/ folders.
    photo_dir = tmp_path / "uploads"
    cv_dir = tmp_path / "cv_uploads"
    photo_dir.mkdir()
    cv_dir.mkdir()
    monkeypatch.setattr(routes_module, "UPLOAD_DIR", str(photo_dir))
    monkeypatch.setattr(routes_module, "CV_UPLOAD_DIR", str(cv_dir))

    session = TestingSessionLocal()
    try:
        yield session, TestingSessionLocal
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def cv_dir(db_session):
    return routes_module.CV_UPLOAD_DIR


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
def other_candidate(db_session):
    session, _ = db_session
    return _make_user(session, full_name="Other Candidate", email="othercandidate@example.com", role="candidate")


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


@pytest.fixture()
def application_on_legacy_job(db_session, candidate, legacy_job):
    session, _ = db_session
    app_row = Application(user_id=candidate.id, job_id=legacy_job.id, status="Pending")
    session.add(app_row)
    session.commit()
    session.refresh(app_row)
    return app_row


def auth_header(user):
    token = create_access_token(user_id=user.id, email=user.email)
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Candidate Profile
# ---------------------------------------------------------------------------

def test_get_candidate_profile_no_token_401(client):
    assert client.get("/profile/candidate").status_code == 401


def test_get_candidate_profile_default_when_no_row(client, candidate):
    response = client.get("/profile/candidate", headers=auth_header(candidate))
    assert response.status_code == 200
    body = response.json()
    assert body["specialization"] is None
    assert body["skills"] is None
    assert body["has_cv"] is False
    assert body["cv_uploaded_at"] is None


def test_update_candidate_profile_sets_values(client, candidate):
    response = client.put("/profile/candidate", headers=auth_header(candidate), json={
        "specialization": "Backend Development",
        "skills": "Python, SQL",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["specialization"] == "Backend Development"
    assert body["skills"] == "Python, SQL"

    # Persisted -- a fresh GET reflects it.
    get_response = client.get("/profile/candidate", headers=auth_header(candidate))
    assert get_response.json()["specialization"] == "Backend Development"


def test_update_candidate_profile_partial_update_preserves_other_field(client, candidate):
    client.put("/profile/candidate", headers=auth_header(candidate), json={
        "specialization": "Design", "skills": "Figma",
    })
    response = client.put("/profile/candidate", headers=auth_header(candidate), json={"skills": "Figma, Photoshop"})
    assert response.status_code == 200
    body = response.json()
    assert body["specialization"] == "Design"  # unchanged
    assert body["skills"] == "Figma, Photoshop"


def test_candidate_profile_no_token_put_401(client):
    assert client.put("/profile/candidate", json={"specialization": "X"}).status_code == 401


def test_candidate_profile_ownership_is_always_self_not_client_supplied(client, candidate, other_candidate):
    # Candidate A sets their own profile.
    client.put("/profile/candidate", headers=auth_header(candidate), json={"specialization": "A's field"})
    # Candidate B reads their own profile -- must NOT see A's data, even
    # though no id is ever accepted from the client (identity is always
    # get_current_user()).
    response = client.get("/profile/candidate", headers=auth_header(other_candidate))
    assert response.status_code == 200
    assert response.json()["specialization"] is None


# ---------------------------------------------------------------------------
# CV upload / replace / delete
# ---------------------------------------------------------------------------

def test_upload_valid_pdf_succeeds(client, candidate):
    response = client.post("/profile/cv", headers=auth_header(candidate),
                            files={"file": ("resume.pdf", _pdf_bytes(), "application/pdf")})
    assert response.status_code == 200
    body = response.json()
    assert body["has_cv"] is True
    assert body["cv_uploaded_at"] is not None


def test_upload_valid_docx_succeeds(client, candidate):
    response = client.post("/profile/cv", headers=auth_header(candidate), files={
        "file": ("resume.docx", _docx_bytes(),
                  "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    })
    assert response.status_code == 200
    assert response.json()["has_cv"] is True


def test_upload_valid_doc_succeeds(client, candidate):
    response = client.post("/profile/cv", headers=auth_header(candidate),
                            files={"file": ("resume.doc", _doc_bytes(), "application/msword")})
    assert response.status_code == 200
    assert response.json()["has_cv"] is True


def test_upload_no_token_401(client):
    response = client.post("/profile/cv", files={"file": ("resume.pdf", _pdf_bytes(), "application/pdf")})
    assert response.status_code == 401


def test_upload_unsupported_extension_rejected(client, candidate):
    response = client.post("/profile/cv", headers=auth_header(candidate),
                            files={"file": ("resume.exe", b"MZ\x90\x00", "application/octet-stream")})
    assert response.status_code == 400


def test_upload_oversized_rejected(client, candidate):
    response = client.post("/profile/cv", headers=auth_header(candidate),
                            files={"file": ("resume.pdf", _oversized_pdf_bytes(), "application/pdf")})
    assert response.status_code == 400


def test_upload_content_mismatch_rejected(client, candidate):
    # .pdf extension, but the bytes are plain text, not a real PDF.
    response = client.post("/profile/cv", headers=auth_header(candidate),
                            files={"file": ("resume.pdf", _plaintext_bytes(), "application/pdf")})
    assert response.status_code == 400


def test_upload_docx_content_mismatch_rejected(client, candidate):
    # .docx extension with a zip that has no word/document.xml entry
    # (a plain, non-Office zip) must be rejected too.
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("hello.txt", "not a real docx")
    response = client.post("/profile/cv", headers=auth_header(candidate),
                            files={"file": ("resume.docx", buf.getvalue(),
                                             "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
    assert response.status_code == 400


def test_replace_cv_removes_old_file_from_disk(client, candidate, db_session, cv_dir):
    session, _ = db_session

    first = client.post("/profile/cv", headers=auth_header(candidate),
                         files={"file": ("resume.pdf", _pdf_bytes(), "application/pdf")})
    assert first.status_code == 200

    profile = session.query(CandidateProfile).filter(CandidateProfile.user_id == candidate.id).first()
    first_filepath = os.path.join(cv_dir, profile.cv_path)
    assert os.path.exists(first_filepath)

    second = client.post("/profile/cv", headers=auth_header(candidate),
                          files={"file": ("resume2.docx", _docx_bytes(),
                                           "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
    assert second.status_code == 200

    session.expire_all()
    profile = session.query(CandidateProfile).filter(CandidateProfile.user_id == candidate.id).first()
    second_filepath = os.path.join(cv_dir, profile.cv_path)

    assert second_filepath != first_filepath
    # The old file must actually be gone from disk, not just replaced in the DB.
    assert not os.path.exists(first_filepath)
    assert os.path.exists(second_filepath)


def test_delete_cv_removes_file_from_disk_and_clears_db(client, candidate, db_session, cv_dir):
    session, _ = db_session

    client.post("/profile/cv", headers=auth_header(candidate),
                files={"file": ("resume.pdf", _pdf_bytes(), "application/pdf")})

    profile = session.query(CandidateProfile).filter(CandidateProfile.user_id == candidate.id).first()
    filepath = os.path.join(cv_dir, profile.cv_path)
    assert os.path.exists(filepath)

    response = client.delete("/profile/cv", headers=auth_header(candidate))
    assert response.status_code == 200
    body = response.json()
    assert body["has_cv"] is False
    assert body["cv_uploaded_at"] is None

    assert not os.path.exists(filepath)

    session.expire_all()
    profile = session.query(CandidateProfile).filter(CandidateProfile.user_id == candidate.id).first()
    assert profile.cv_path is None
    assert profile.cv_uploaded_at is None


def test_delete_cv_when_none_exists_returns_404(client, candidate):
    response = client.delete("/profile/cv", headers=auth_header(candidate))
    assert response.status_code == 404


def test_delete_cv_no_token_401(client):
    assert client.delete("/profile/cv").status_code == 401


# ---------------------------------------------------------------------------
# has_cv reflected in the employer applicants list
# ---------------------------------------------------------------------------

def test_has_cv_false_for_candidate_with_no_cv(client, employer_a, job_owned_by_a, application_on_job_a):
    response = client.get(f"/employer/jobs/{job_owned_by_a.id}/applicants", headers=auth_header(employer_a))
    assert response.status_code == 200
    assert response.json()[0]["has_cv"] is False


def test_has_cv_true_after_candidate_uploads(client, candidate, employer_a, job_owned_by_a, application_on_job_a):
    client.post("/profile/cv", headers=auth_header(candidate),
                files={"file": ("resume.pdf", _pdf_bytes(), "application/pdf")})
    response = client.get(f"/employer/jobs/{job_owned_by_a.id}/applicants", headers=auth_header(employer_a))
    assert response.status_code == 200
    assert response.json()[0]["has_cv"] is True


# ---------------------------------------------------------------------------
# Employer CV access endpoint
# ---------------------------------------------------------------------------

def test_employer_cv_no_token_401(client, application_on_job_a):
    assert client.get(f"/employer/applications/{application_on_job_a.id}/cv").status_code == 401


def test_employer_cv_candidate_token_403(client, candidate, application_on_job_a):
    response = client.get(f"/employer/applications/{application_on_job_a.id}/cv", headers=auth_header(candidate))
    assert response.status_code == 403


def test_employer_cv_owner_success(client, candidate, employer_a, application_on_job_a):
    client.post("/profile/cv", headers=auth_header(candidate),
                files={"file": ("resume.pdf", _pdf_bytes(), "application/pdf")})
    response = client.get(f"/employer/applications/{application_on_job_a.id}/cv", headers=auth_header(employer_a))
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content == _pdf_bytes()


def test_employer_cv_other_employer_403(client, candidate, employer_b, application_on_job_a):
    client.post("/profile/cv", headers=auth_header(candidate),
                files={"file": ("resume.pdf", _pdf_bytes(), "application/pdf")})
    response = client.get(f"/employer/applications/{application_on_job_a.id}/cv", headers=auth_header(employer_b))
    assert response.status_code == 403


def test_employer_cv_nonexistent_application_404(client, employer_a):
    response = client.get("/employer/applications/999999/cv", headers=auth_header(employer_a))
    assert response.status_code == 404


def test_employer_cv_legacy_job_application_403(client, candidate, employer_a, application_on_legacy_job):
    # A candidate applied to a legacy/unowned job (employer_id IS NULL).
    # No real employer -- including employer_a -- may ever access this,
    # exactly matching the existing legacy-job ownership behavior.
    client.post("/profile/cv", headers=auth_header(candidate),
                files={"file": ("resume.pdf", _pdf_bytes(), "application/pdf")})
    response = client.get(f"/employer/applications/{application_on_legacy_job.id}/cv", headers=auth_header(employer_a))
    assert response.status_code == 403


def test_employer_cv_no_cv_present_clean_404(client, employer_a, application_on_job_a):
    # A valid, owned applicant who simply never uploaded a CV -- must be
    # a clean 404, not a crash.
    response = client.get(f"/employer/applications/{application_on_job_a.id}/cv", headers=auth_header(employer_a))
    assert response.status_code == 404


def test_employer_cv_candidate_who_never_applied_to_this_employer(client, candidate, employer_a, employer_b, db_session):
    # A candidate who applied to Employer B's job (not Employer A's) --
    # Employer A must not be able to reach that application at all
    # (covered structurally by the "other employer" test above, but this
    # exercises it with a candidate who has zero applications to
    # employer_a specifically).
    session, _ = db_session
    job_b = Job(title="QA", company="Globex", location="Giza", salary="1", employment_type="Full-time",
                employer_id=employer_b.id, is_active=True)
    session.add(job_b)
    session.commit()
    session.refresh(job_b)
    app_row = Application(user_id=candidate.id, job_id=job_b.id, status="Pending")
    session.add(app_row)
    session.commit()
    session.refresh(app_row)

    response = client.get(f"/employer/applications/{app_row.id}/cv", headers=auth_header(employer_a))
    assert response.status_code == 403

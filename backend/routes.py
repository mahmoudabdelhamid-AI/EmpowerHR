"""
API routes for EmpowerHR backend.

Endpoints (e.g. candidate registration, job listings) are added to
this router as they are implemented.
"""

import io
import os
import threading
import time
import uuid
import zipfile
from datetime import datetime

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from sqlalchemy.exc import IntegrityError

from auth_utils import create_access_token, get_current_admin, get_current_employer, get_current_user, get_owned_job
from database import get_db, DATA_DIR
from models import Application, CandidateProfile, Job, User
from schemas import (
    AdminUserOut,
    ApplicantResponse,
    ApplicationResponse,
    ApplicationStatusUpdate,
    CandidateProfileResponse,
    CandidateProfileUpdate,
    EmployerCreate,
    JobCreate,
    JobOut,
    JobStatusUpdate,
    JobUpdate,
    LoginRequest,
    LoginResponse,
    ProfileUpdate,
    UserCreate,
    UserResponse,
    UserStatusUpdate,
    ApplicationWithJobResponse,
)

router = APIRouter()

password_hash = PasswordHash.recommended()


# STEP 13 (D-9): lightweight liveness endpoint for deployment
# health checks. Deliberately has no dependencies -- no DB session,
# no auth, no rate limiting -- so it reflects only "is the process
# up and serving requests," not "is the database reachable." Must
# stay this simple; do not add a DB query or other side effect to
# this endpoint.
@router.get("/health")
def health_check():
    return {"status": "ok"}

# STEP 12 (H-2): minimal in-memory rate limiting for the unauthenticated
# authentication endpoints (/login, /register, /employer/register).
# Fixed-window counter keyed by (bucket_name, client IP). Intentionally
# simple for the current single-process deployment -- not distributed,
# not persisted across restarts.
_RATE_LIMIT_WINDOW_SECONDS = 60
_RATE_LIMIT_MAX_REQUESTS = 5
_rate_limit_lock = threading.Lock()
_rate_limit_buckets = {}


def _enforce_rate_limit(request: Request, bucket_name: str) -> None:
    """Raise HTTP 429 once the calling client IP exceeds
    _RATE_LIMIT_MAX_REQUESTS requests to `bucket_name` within the last
    _RATE_LIMIT_WINDOW_SECONDS seconds."""
    client_ip = request.client.host if request.client else "unknown"
    key = (bucket_name, client_ip)
    now = time.monotonic()

    with _rate_limit_lock:
        timestamps = _rate_limit_buckets.setdefault(key, [])
        cutoff = now - _RATE_LIMIT_WINDOW_SECONDS
        while timestamps and timestamps[0] < cutoff:
            timestamps.pop(0)

        if len(timestamps) >= _RATE_LIMIT_MAX_REQUESTS:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again later.",
            )

        timestamps.append(now)

# Local disk storage for uploaded profile photos. Kept simple (no cloud
# storage) since this is the smallest sensible approach for the project's
# current scale; main.py mounts this directory at /uploads so the saved
# path can be served back to the frontend directly.
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
MAX_PHOTO_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

# Step 10: CV storage. Deliberately a SEPARATE directory from `uploads/`
# and NEVER mounted as static files anywhere in main.py -- CVs must not
# be reachable via a guessable/public URL, only through the controlled,
# authenticated endpoints below. cv_path in the DB stores a bare
# filename (not a URL), reinforcing that it is never served directly.
CV_UPLOAD_DIR = os.path.join(DATA_DIR, "cv_uploads")
os.makedirs(CV_UPLOAD_DIR, exist_ok=True)
ALLOWED_CV_EXTENSIONS = {".pdf", ".doc", ".docx"}
# 10 MB: generous enough for an image-heavy/scanned CV (typical text
# resumes are well under 1MB) while still bounding upload size. Chosen
# independently of the 5MB photo cap per the Step 10 spec.
MAX_CV_SIZE_BYTES = 10 * 1024 * 1024
_CV_MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _cv_content_matches_extension(content: bytes, ext: str) -> bool:
    """Verify the uploaded bytes actually look like the claimed file
    type, rather than trusting the filename extension alone. Uses only
    the standard library (magic-byte signatures + zipfile for .docx's
    internal structure) -- no new dependency needed for this check.

    - .pdf: files start with the literal "%PDF-" header.
    - .doc: legacy binary Word files are OLE Compound Files, which all
      start with the fixed 8-byte OLE2 signature.
    - .docx: a real Office Open XML file is a zip archive (starts with
      the local-file-header signature "PK\\x03\\x04") that, unlike an
      arbitrary zip, actually contains a word/document.xml entry.
    """
    if ext == ".pdf":
        return content.startswith(b"%PDF-")

    if ext == ".doc":
        return content.startswith(b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1")

    if ext == ".docx":
        if not content.startswith(b"PK\x03\x04"):
            return False
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                return "word/document.xml" in archive.namelist()
        except zipfile.BadZipFile:
            return False

    return False


def _image_content_matches_extension(content: bytes, ext: str) -> bool:
    """STEP 12 (H-3): verify the uploaded bytes actually look like the
    claimed image type via magic-byte signatures, mirroring
    _cv_content_matches_extension above -- rather than trusting the
    filename extension alone."""
    if ext in (".jpg", ".jpeg"):
        return content.startswith(b"\xff\xd8\xff")
    if ext == ".png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if ext == ".gif":
        return content.startswith(b"GIF87a") or content.startswith(b"GIF89a")
    if ext == ".webp":
        return content.startswith(b"RIFF") and content[8:12] == b"WEBP"
    return False


@router.get("/jobs", response_model=List[JobOut])
def list_jobs(db: Session = Depends(get_db)):
    """Return the list of active job postings stored in the database."""
    return db.query(Job).filter(Job.is_active == True).all()  # noqa: E712


@router.post("/register", response_model=UserResponse)
def register(user: UserCreate, request: Request, db: Session = Depends(get_db)):
    """Create a new user account."""
    _enforce_rate_limit(request, "register")

    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user is not None:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        full_name=user.full_name,
        email=user.email,
        password=password_hash.hash(user.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user



@router.post("/login", response_model=LoginResponse)
def login(credentials: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Authenticate a user by email and password and issue a JWT."""
    _enforce_rate_limit(request, "login")

    user = db.query(User).filter(User.email == credentials.email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not password_hash.verify(credentials.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Step 11: block login for deactivated accounts. This check only
    # runs after credentials are already verified correct, so it never
    # gives an attacker without the right password any information they
    # didn't already have from the generic "Invalid email or password"
    # response above -- it only ever informs the legitimate account
    # holder that their own account has been deactivated.
    if not user.is_active:
        raise HTTPException(status_code=401, detail="This account has been deactivated")

    access_token = create_access_token(user_id=user.id, email=user.email)

    return LoginResponse(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        access_token=access_token,
        profile_image=user.profile_image,
        role=user.role,
        company_name=user.company_name,
    )



@router.post("/jobs/{job_id}/apply", response_model=ApplicationResponse)
def apply_to_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create an application for the given job on behalf of the authenticated user."""
    if current_user.role == "employer":
        raise HTTPException(
            status_code=403,
            detail="Employers cannot apply to jobs",
        )
    job = db.query(Job).filter(Job.id == job_id).first()

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.is_active:
        raise HTTPException(status_code=400, detail="This job is no longer accepting applications")

    existing_application = (
        db.query(Application)
        .filter(Application.user_id == current_user.id, Application.job_id == job.id)
        .first()
    )
    if existing_application is not None:
        raise HTTPException(status_code=400, detail="You have already applied to this job.")

    new_application = Application(
        user_id=current_user.id,
        job_id=job.id,
        status="Pending",
        date_applied=datetime.utcnow(),
    )
    db.add(new_application)
    db.commit()
    db.refresh(new_application)
    return new_application

@router.get("/profile", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/profile", response_model=UserResponse)
def update_profile(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update the authenticated user's own full name and/or password.
    Target user comes only from the JWT (get_current_user); no client
    id is accepted. Password is hashed with the existing password_hash
    and never returned (UserResponse has no password field)."""
    if payload.full_name is not None:
        current_user.full_name = payload.full_name

    if payload.password is not None:
        current_user.password = password_hash.hash(payload.password)

    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/profile/photo", response_model=UserResponse)
def upload_profile_photo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = current_user
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported image type")

    # STEP 12 (H-3): read the actual bytes and check their length instead
    # of trusting UploadFile.size, which can be None and silently skip
    # the size check entirely. Mirrors the existing CV upload pattern.
    content = file.file.read()
    if len(content) > MAX_PHOTO_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Image exceeds maximum size of 5MB")

    # STEP 12 (H-3): verify the bytes actually look like the claimed
    # image type, not just the filename extension.
    if not _image_content_matches_extension(content, ext):
        raise HTTPException(status_code=400, detail="File content does not match its claimed file type")

    filename = f"user_{user.id}_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as buffer:
        buffer.write(content)

    user.profile_image = f"/uploads/{filename}"
    db.commit()
    db.refresh(user)
    return user


@router.get("/applications", response_model=List[ApplicationWithJobResponse])
def get_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all applications submitted by the authenticated user, newest first."""
    applications = (
        db.query(Application)
        .filter(Application.user_id == current_user.id)
        .order_by(Application.date_applied.desc())
        .all()
    )

    return [
        ApplicationWithJobResponse(
            id=application.id,
            job_id=application.job_id,
            job_title=application.job.title,
            company=application.job.company,
            location=application.job.location,
            salary=application.job.salary,
            employment_type=application.job.employment_type,
            status=application.status,
            date_applied=application.date_applied,
        )
        for application in applications
    ]
@router.post("/employer/register", response_model=UserResponse)
def register_employer(employer: EmployerCreate, request: Request, db: Session = Depends(get_db)):
    """Create a new employer account. role is hardcoded server-side --
    never read from the request body."""
    _enforce_rate_limit(request, "employer_register")

    existing_user = db.query(User).filter(User.email == employer.email).first()
    if existing_user is not None:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        full_name=employer.full_name,
        email=employer.email,
        password=password_hash.hash(employer.password),
        role="employer",
        company_name=employer.company_name,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.get("/employer/jobs", response_model=List[JobOut])
def list_employer_jobs(
    db: Session = Depends(get_db),
    current_employer: User = Depends(get_current_employer),
):
    """Return only the jobs owned by the authenticated employer."""
    return db.query(Job).filter(Job.employer_id == current_employer.id).all()


@router.post("/employer/jobs", response_model=JobOut)
def create_employer_job(
    job_data: JobCreate,
    db: Session = Depends(get_db),
    current_employer: User = Depends(get_current_employer),
):
    """Create a job owned by the authenticated employer. `company` and
    `employer_id` are always derived server-side; `is_active` defaults
    to True and is not settable on create."""
    new_job = Job(
        title=job_data.title,
        company=current_employer.company_name,
        location=job_data.location,
        salary=job_data.salary,
        employment_type=job_data.employment_type,
        employer_id=current_employer.id,
        is_active=True,
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return new_job


@router.put("/employer/jobs/{job_id}", response_model=JobOut)
def update_employer_job(
    job_update: JobUpdate,
    db: Session = Depends(get_db),
    job: Job = Depends(get_owned_job),
):
    """Update a job owned by the authenticated employer. `company` and
    `employer_id` are never accepted or changed here."""
    if job_update.title is not None:
        job.title = job_update.title
    if job_update.location is not None:
        job.location = job_update.location
    if job_update.salary is not None:
        job.salary = job_update.salary
    if job_update.employment_type is not None:
        job.employment_type = job_update.employment_type
    if job_update.is_active is not None:
        job.is_active = job_update.is_active

    db.commit()
    db.refresh(job)
    return job


@router.delete("/employer/jobs/{job_id}", status_code=204)
def delete_employer_job(
    db: Session = Depends(get_db),
    job: Job = Depends(get_owned_job),
):
    """Delete a job owned by the authenticated employer. Never
    cascade-deletes Applications -- if any exist, the delete is rejected
    with 409 instead."""
    try:
        db.delete(job)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Cannot delete a job with existing applications",
        )
    return None


@router.get("/employer/jobs/{job_id}/applicants", response_model=List[ApplicantResponse])
def list_job_applicants(
    db: Session = Depends(get_db),
    job: Job = Depends(get_owned_job),
):
    """Return the applicants for a job owned by the authenticated
    employer. Only the approved fields are included -- no password,
    hash, or token."""
    applications = (
        db.query(Application)
        .filter(Application.job_id == job.id)
        .order_by(Application.date_applied.desc())
        .all()
    )

    return [
        ApplicantResponse(
            application_id=application.id,
            job_id=application.job_id,
            status=application.status,
            date_applied=application.date_applied,
            full_name=application.user.full_name,
            email=application.user.email,
            profile_image=application.user.profile_image,
            has_cv=(
                db.query(CandidateProfile)
                .filter(CandidateProfile.user_id == application.user_id, CandidateProfile.cv_path.isnot(None))
                .first()
                is not None
            ),
        )
        for application in applications
    ]


@router.patch("/employer/applications/{application_id}/status", response_model=ApplicationResponse)
def update_application_status(
    application_id: int,
    status_update: ApplicationStatusUpdate,
    db: Session = Depends(get_db),
    current_employer: User = Depends(get_current_employer),
):
    """Update the status of an application. Ownership is verified
    manually through the Application -> Job -> employer_id chain, since
    this endpoint only receives an application_id, not a job_id."""
    application = db.query(Application).filter(Application.id == application_id).first()
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")

    job = db.query(Job).filter(Job.id == application.job_id).first()
    if job is None or job.employer_id != current_employer.id:
        raise HTTPException(status_code=403, detail="You do not own this job")

    application.status = status_update.status
    db.commit()
    db.refresh(application)
    return application


# ---------------------------------------------------------------------
# Step 10: Candidate Profile & CV
# ---------------------------------------------------------------------

def _candidate_profile_response(profile: Optional[CandidateProfile]) -> CandidateProfileResponse:
    """Build the response for a (possibly absent) CandidateProfile row.
    A user with no row yet is a normal state -- returned as all-empty/
    has_cv=False rather than an error."""
    if profile is None:
        return CandidateProfileResponse(specialization=None, skills=None, has_cv=False, cv_uploaded_at=None)
    return CandidateProfileResponse(
        specialization=profile.specialization,
        skills=profile.skills,
        has_cv=profile.cv_path is not None,
        cv_uploaded_at=profile.cv_uploaded_at,
    )


@router.get("/profile/candidate", response_model=CandidateProfileResponse)
def get_candidate_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the authenticated user's own candidate profile. Identity
    comes only from the JWT (get_current_user); no client id accepted."""
    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == current_user.id).first()
    return _candidate_profile_response(profile)


@router.put("/profile/candidate", response_model=CandidateProfileResponse)
def update_candidate_profile(
    payload: CandidateProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create-or-update the authenticated user's own candidate profile.
    Only specialization/skills are handled here -- no accommodations/
    phone/city/birth_date field exists anywhere in this schema. Omitting
    a field (None) leaves it unchanged; an explicit empty string clears
    it."""
    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == current_user.id).first()
    if profile is None:
        profile = CandidateProfile(user_id=current_user.id)
        db.add(profile)

    if payload.specialization is not None:
        profile.specialization = payload.specialization.strip() or None
    if payload.skills is not None:
        profile.skills = payload.skills.strip() or None

    db.commit()
    db.refresh(profile)
    return _candidate_profile_response(profile)


@router.post("/profile/cv", response_model=CandidateProfileResponse)
def upload_cv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload (or replace) the authenticated user's own CV. A second
    call always replaces the first -- one CV per candidate, not
    multiple versions. The new file is written and committed first;
    the previous file (if any) is only removed afterward, so a failed
    write never loses the old CV, and a failed old-file cleanup never
    invalidates the new one."""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_CV_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported CV file type. Allowed types: PDF, DOC, DOCX")

    content = file.file.read()
    if len(content) > MAX_CV_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="CV exceeds maximum size of 10MB")

    if not _cv_content_matches_extension(content, ext):
        raise HTTPException(status_code=400, detail="File content does not match its claimed file type")

    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == current_user.id).first()
    if profile is None:
        profile = CandidateProfile(user_id=current_user.id)
        db.add(profile)

    # Replace behavior: capture the previous file's path (if any) but do
    # NOT delete it yet -- the old CV must stay intact until the new one
    # is safely written to disk and committed to the database.
    old_filepath = None
    if profile.cv_path:
        old_filepath = os.path.join(CV_UPLOAD_DIR, profile.cv_path)

    filename = f"cv_{current_user.id}_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(CV_UPLOAD_DIR, filename)
    with open(filepath, "wb") as buffer:
        buffer.write(content)

    # Bare filename only -- never a public URL/path (see CV_UPLOAD_DIR).
    profile.cv_path = filename
    profile.cv_uploaded_at = datetime.utcnow()

    db.commit()
    db.refresh(profile)

    # Only now that the new CV is safely written and committed do we
    # remove the old one. Best-effort: if this fails, the already-valid
    # new CV/database state is unaffected.
    if old_filepath and old_filepath != filepath and os.path.exists(old_filepath):
        try:
            os.remove(old_filepath)
        except OSError:
            pass

    return _candidate_profile_response(profile)


@router.delete("/profile/cv", response_model=CandidateProfileResponse)
def delete_cv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete the authenticated user's own CV: removes the file from
    disk and clears cv_path/cv_uploaded_at."""
    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == current_user.id).first()
    if profile is None or profile.cv_path is None:
        raise HTTPException(status_code=404, detail="No CV to delete")

    filepath = os.path.join(CV_UPLOAD_DIR, profile.cv_path)
    if os.path.exists(filepath):
        os.remove(filepath)

    profile.cv_path = None
    profile.cv_uploaded_at = None
    db.commit()
    db.refresh(profile)
    return _candidate_profile_response(profile)


@router.get("/employer/applications/{application_id}/cv")
def download_applicant_cv(
    application_id: int,
    db: Session = Depends(get_db),
    current_employer: User = Depends(get_current_employer),
):
    """Download an applicant's CV. Ownership is verified manually
    through the Application -> Job -> employer_id chain (same pattern
    and same 404/403 order as update_application_status), since this
    endpoint only receives an application_id, not a job_id. A legacy
    job (employer_id IS NULL) is never treated as owned by any real
    employer -- job.employer_id != current_employer.id already rejects
    it, exactly as get_owned_job does elsewhere."""
    application = db.query(Application).filter(Application.id == application_id).first()
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")

    job = db.query(Job).filter(Job.id == application.job_id).first()
    if job is None or job.employer_id != current_employer.id:
        raise HTTPException(status_code=403, detail="You do not own this job")

    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == application.user_id).first()
    if profile is None or profile.cv_path is None:
        raise HTTPException(status_code=404, detail="No CV uploaded for this applicant")

    filepath = os.path.join(CV_UPLOAD_DIR, profile.cv_path)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="No CV uploaded for this applicant")

    cv_ext = os.path.splitext(profile.cv_path)[1].lower()
    return FileResponse(
        path=filepath,
        media_type=_CV_MEDIA_TYPES.get(cv_ext, "application/octet-stream"),
        filename=f"cv_{application.user_id}{cv_ext}",
    )


# ---------------------------------------------------------------------
# Step 11: Admin & Moderation (MVP)
# ---------------------------------------------------------------------
# Admin accounts are seeded manually (directly in the database) -- there
# is deliberately no public /admin/register endpoint. Authorization
# follows the exact same pattern as get_current_employer: role is read
# fresh from the User DB row via get_current_user, never trusted from
# the JWT payload.


@router.get("/admin/users", response_model=List[AdminUserOut])
def list_all_users(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """Return every user account, across all roles. Admin-only."""
    return db.query(User).all()


@router.patch("/admin/users/{user_id}/status", response_model=AdminUserOut)
def update_user_status(
    user_id: int,
    status_update: UserStatusUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """Activate or deactivate any user account. Only is_active is ever
    accepted (UserStatusUpdate has no other fields) -- role, company_name,
    email, etc. can never be changed through this endpoint."""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = status_update.is_active
    db.commit()
    db.refresh(user)
    return user


@router.get("/admin/jobs", response_model=List[JobOut])
def list_all_jobs(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """Return every job posting, regardless of owning employer,
    is_active status, or legacy (employer_id IS NULL) status. Admin-only."""
    return db.query(Job).all()


@router.patch("/admin/jobs/{job_id}/status", response_model=JobOut)
def update_job_status_admin(
    job_id: int,
    status_update: JobStatusUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """Activate or deactivate any job posting, owned by any employer (or
    unowned/legacy). Admin authority is global, so this deliberately does
    NOT use get_owned_job -- that dependency is employer-ownership-scoped
    and would incorrectly reject jobs the admin doesn't "own"."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    job.is_active = status_update.is_active
    db.commit()
    db.refresh(job)
    return job


# More endpoints will be added here, for example:
#
# @router.get("/candidates")
# def list_candidates():
#     ...
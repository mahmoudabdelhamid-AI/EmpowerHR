"""
API routes for EmpowerHR backend.

Endpoints (e.g. candidate registration, job listings) are added to
this router as they are implemented.
"""

import os
import uuid
from datetime import datetime

from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from database import get_db
from models import Application, Job, User
from schemas import (
    ApplicationResponse,
    ApplyRequest,
    JobOut,
    LoginRequest,
    UserCreate,
    UserResponse,
    ApplicationWithJobResponse,
)

router = APIRouter()

password_hash = PasswordHash.recommended()

# Local disk storage for uploaded profile photos. Kept simple (no cloud
# storage) since this is the smallest sensible approach for the project's
# current scale; main.py mounts this directory at /uploads so the saved
# path can be served back to the frontend directly.
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


@router.get("/jobs", response_model=List[JobOut])
def list_jobs(db: Session = Depends(get_db)):
    """Return the list of job postings stored in the database."""
    return db.query(Job).all()


@router.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user account."""
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



@router.post("/login", response_model=UserResponse)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate a user by email and password."""
    user = db.query(User).filter(User.email == credentials.email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not password_hash.verify(credentials.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return user



@router.post("/jobs/{job_id}/apply", response_model=ApplicationResponse)
def apply_to_job(job_id: int, application: ApplyRequest, db: Session = Depends(get_db)):
    """Create an application for the given job on behalf of the given user."""
    user = db.query(User).filter(User.id == application.user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    existing_application = (
        db.query(Application)
        .filter(Application.user_id == user.id, Application.job_id == job.id)
        .first()
    )
    if existing_application is not None:
        raise HTTPException(status_code=400, detail="You have already applied to this job.")

    new_application = Application(
        user_id=user.id,
        job_id=job.id,
        status="Pending",
        date_applied=datetime.utcnow(),
    )
    db.add(new_application)
    db.commit()
    db.refresh(new_application)
    return new_application

@router.get("/profile", response_model=UserResponse)
def get_profile(user_id: int, db: Session = Depends(get_db)):
    """Return the current profile info for the given user."""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/profile/photo", response_model=UserResponse)
def upload_profile_photo(
    user_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Save an uploaded profile photo to local disk and persist its URL on the user."""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported image type")

    filename = f"user_{user.id}_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as buffer:
        buffer.write(file.file.read())

    user.profile_image = f"/uploads/{filename}"
    db.commit()
    db.refresh(user)
    return user


@router.get("/applications", response_model=List[ApplicationWithJobResponse])
def get_applications(user_id: int, db: Session = Depends(get_db)):
    """Return all applications submitted by the given user, newest first."""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    applications = (
        db.query(Application)
        .filter(Application.user_id == user_id)
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
# More endpoints will be added here, for example:
#
# @router.get("/candidates")
# def list_candidates():
#     ...
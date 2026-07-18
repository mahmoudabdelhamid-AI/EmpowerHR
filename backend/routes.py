"""
API routes for EmpowerHR backend.

Endpoints (e.g. candidate registration, job listings) are added to
this router as they are implemented.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Job, User
from schemas import JobOut, UserCreate, UserResponse
from pwdlib import PasswordHash

router = APIRouter()

password_hash = PasswordHash.recommended()


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

# More endpoints will be added here, for example:
#
# @router.get("/candidates")
# def list_candidates():
#     ...
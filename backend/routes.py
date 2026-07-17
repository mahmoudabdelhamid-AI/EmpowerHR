"""
API routes for EmpowerHR backend.

Endpoints (e.g. candidate registration, job listings) are added to
this router as they are implemented.
"""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import Job
from schemas import JobOut

router = APIRouter()


@router.get("/jobs", response_model=List[JobOut])
def list_jobs(db: Session = Depends(get_db)):
    """Return the list of job postings stored in the database."""
    return db.query(Job).all()


# More endpoints will be added here, for example:
#
# @router.get("/candidates")
# def list_candidates():
#     ...
"""
Pydantic schemas for EmpowerHR backend.

Request/response models
(e.g. CandidateCreate, CandidateOut, JobOut) will be added here
in a future task, once the corresponding endpoints are built.

Example of how a schema will be defined once needed:

    from pydantic import BaseModel

    class CandidateBase(BaseModel):
        first_name: str
        last_name: str
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class JobOut(BaseModel):
    id: int
    title: str
    company: str
    location: str
    salary: str

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    full_name: str
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    profile_image: Optional[str] = None

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    email: str
    password: str

class ApplyRequest(BaseModel):
    user_id: int


class ApplicationResponse(BaseModel):
    id: int
    user_id: int
    job_id: int
    status: str
    date_applied: datetime

    model_config = {"from_attributes": True}

class ApplicationWithJobResponse(BaseModel):
    id: int
    job_id: int
    job_title: str
    company: str
    location: str
    salary: str
    employment_type: str
    status: str
    date_applied: datetime

    model_config = {"from_attributes": True}
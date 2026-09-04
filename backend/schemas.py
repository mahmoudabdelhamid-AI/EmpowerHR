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

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator

# Minimal email shape check (no external dependency): local@domain.tld
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _require_non_blank(value: str, field_name: str) -> str:
    if value is None or not value.strip():
        raise ValueError(f"{field_name} must not be empty")
    return value.strip()


def _require_valid_email(value: str) -> str:
    value = _require_non_blank(value, "email")
    if not _EMAIL_RE.match(value):
        raise ValueError("email must be a valid email address")
    return value


# STEP 12 (M-1): minimum password length. Intentionally simple -- length
# only, no additional complexity rules.
MIN_PASSWORD_LENGTH = 8


def _require_valid_password(value: str) -> str:
    value = _require_non_blank(value, "password")
    if len(value) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"password must be at least {MIN_PASSWORD_LENGTH} characters long")
    return value


class JobOut(BaseModel):
    id: int
    title: str
    company: str
    location: str
    salary: str
    employer_id: Optional[int] = None
    is_active: bool = True

    model_config = {"from_attributes": True}


class EmployerCreate(BaseModel):
    """Body for POST /employer/register. role is always hardcoded
    server-side to "employer" -- it is never read from this schema."""
    full_name: str
    email: str
    password: str
    company_name: str

    @field_validator("full_name")
    @classmethod
    def _validate_full_name(cls, v: str) -> str:
        return _require_non_blank(v, "full_name")

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str) -> str:
        return _require_valid_email(v)

    @field_validator("password")
    @classmethod
    def _validate_password(cls, v: str) -> str:
        return _require_valid_password(v)

    @field_validator("company_name")
    @classmethod
    def _validate_company_name(cls, v: str) -> str:
        return _require_non_blank(v, "company_name")


class JobCreate(BaseModel):
    """Body for POST /employer/jobs. `company` is intentionally NOT a
    field here -- it is always derived server-side from the current
    employer's company_name. `employer_id` and `is_active` are likewise
    never accepted from the client."""
    title: str
    location: str
    salary: str
    employment_type: str

    @field_validator("title")
    @classmethod
    def _validate_title(cls, v: str) -> str:
        return _require_non_blank(v, "title")

    @field_validator("location")
    @classmethod
    def _validate_location(cls, v: str) -> str:
        return _require_non_blank(v, "location")

    @field_validator("salary")
    @classmethod
    def _validate_salary(cls, v: str) -> str:
        return _require_non_blank(v, "salary")

    @field_validator("employment_type")
    @classmethod
    def _validate_employment_type(cls, v: str) -> str:
        return _require_non_blank(v, "employment_type")


class JobUpdate(BaseModel):
    """Body for PUT /employer/jobs/{job_id}. All fields optional.
    `company` and `employer_id` are intentionally NOT fields here --
    company identity is fixed at job-creation time and never changes."""
    title: Optional[str] = None
    location: Optional[str] = None
    salary: Optional[str] = None
    employment_type: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("title")
    @classmethod
    def _validate_title(cls, v: Optional[str]) -> Optional[str]:
        return _require_non_blank(v, "title") if v is not None else v

    @field_validator("location")
    @classmethod
    def _validate_location(cls, v: Optional[str]) -> Optional[str]:
        return _require_non_blank(v, "location") if v is not None else v

    @field_validator("salary")
    @classmethod
    def _validate_salary(cls, v: Optional[str]) -> Optional[str]:
        return _require_non_blank(v, "salary") if v is not None else v

    @field_validator("employment_type")
    @classmethod
    def _validate_employment_type(cls, v: Optional[str]) -> Optional[str]:
        return _require_non_blank(v, "employment_type") if v is not None else v


class ApplicantResponse(BaseModel):
    """Response item for GET /employer/jobs/{job_id}/applicants. Contains
    only the fields explicitly approved -- no password, hash, token, or
    CV storage internals (no cv_path/filename/URL -- only the boolean
    has_cv)."""
    application_id: int
    job_id: int
    status: str
    date_applied: datetime
    full_name: str
    email: str
    profile_image: Optional[str] = None
    has_cv: bool = False

    model_config = {"from_attributes": True}


class CandidateProfileUpdate(BaseModel):
    """Body for PUT /profile/candidate. Both fields optional so a
    request can update either without the other -- omitting a field
    (None) leaves it unchanged; an explicit empty string clears it.
    No accommodations/phone/city/birth_date field exists here or
    anywhere else in this schema module -- out of Step 10 scope."""
    specialization: Optional[str] = None
    skills: Optional[str] = None


class CandidateProfileResponse(BaseModel):
    """Response for GET/PUT /profile/candidate. Deliberately excludes
    cv_path/filename -- only the boolean has_cv and, for the candidate's
    own view, the upload timestamp (not a storage path)."""
    specialization: Optional[str] = None
    skills: Optional[str] = None
    has_cv: bool = False
    cv_uploaded_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


VALID_APPLICATION_STATUSES = {"Pending", "Reviewed", "Interview", "Accepted", "Rejected"}


class ApplicationStatusUpdate(BaseModel):
    """Body for PATCH /employer/applications/{application_id}/status."""
    status: str

    @field_validator("status")
    @classmethod
    def _validate_status(cls, v: str) -> str:
        v = _require_non_blank(v, "status")
        if v not in VALID_APPLICATION_STATUSES:
            raise ValueError(
                f"status must be one of {sorted(VALID_APPLICATION_STATUSES)}"
            )
        return v


class UserCreate(BaseModel):
    full_name: str
    email: str
    password: str

    @field_validator("full_name")
    @classmethod
    def _validate_full_name(cls, v: str) -> str:
        return _require_non_blank(v, "full_name")

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str) -> str:
        return _require_valid_email(v)

    @field_validator("password")
    @classmethod
    def _validate_password(cls, v: str) -> str:
        return _require_valid_password(v)


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    profile_image: Optional[str] = None
    role: str = "candidate"
    company_name: Optional[str] = None


    model_config = {"from_attributes": True}



class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str) -> str:
        return _require_valid_email(v)

    @field_validator("password")
    @classmethod
    def _validate_password(cls, v: str) -> str:
        return _require_non_blank(v, "password")

class ProfileUpdate(BaseModel):
    """Fields an authenticated user may edit on their own profile.
    Both optional so a request can update either without the other.
    Email is intentionally excluded (read-only)."""
    full_name: Optional[str] = None
    password: Optional[str] = None

    @field_validator("full_name")
    @classmethod
    def _validate_full_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return _require_non_blank(v, "full_name")

    @field_validator("password")
    @classmethod
    def _validate_password(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return _require_valid_password(v)


class LoginResponse(BaseModel):
    id: int
    full_name: str
    email: str
    access_token: str
    token_type: str = "bearer"
    profile_image: Optional[str] = None
    role: str = "candidate"
    company_name: Optional[str] = None

    model_config = {"from_attributes": True}




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


# ---------------------------------------------------------------------
# Step 11: Admin & Moderation
# ---------------------------------------------------------------------

class AdminUserOut(BaseModel):
    """Response for GET /admin/users and PATCH /admin/users/{id}/status.
    Deliberately excludes password -- never returned anywhere."""
    id: int
    full_name: str
    email: str
    role: str
    is_active: bool
    company_name: Optional[str] = None

    model_config = {"from_attributes": True}


class UserStatusUpdate(BaseModel):
    """Body for PATCH /admin/users/{user_id}/status. Only is_active is
    accepted -- role, company_name, email, etc. are never settable here.
    This is the sole guard against mass assignment on this endpoint."""
    is_active: bool


class JobStatusUpdate(BaseModel):
    """Body for PATCH /admin/jobs/{job_id}/status. Only is_active is
    accepted -- title/location/salary/employer_id etc. are never
    settable here (that's JobUpdate's job, and is employer-owned-only)."""
    is_active: bool
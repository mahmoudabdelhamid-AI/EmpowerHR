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

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    email: str
    password: str
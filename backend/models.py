"""
SQLAlchemy models for EmpowerHR backend.

Example of how a model will be defined once needed:

    from sqlalchemy import Column, Integer, String
    from database import Base

    class Candidate(Base):
        __tablename__ = "candidates"

        id = Column(Integer, primary_key=True, index=True)
        first_name = Column(String)
        last_name = Column(String)
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint

from sqlalchemy.orm import relationship

from database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    location = Column(String, nullable=False)
    salary = Column(String, nullable=False)
    employment_type = Column(String, nullable=False, default="Full-time")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    profile_image = Column(String, nullable=True)


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_user_job"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    status = Column(String, nullable=False, default="Pending")
    date_applied = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    job = relationship("Job")
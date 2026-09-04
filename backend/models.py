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

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint

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
    # Step 9: owning employer. Nullable so legacy/pre-Step-9 jobs remain
    # valid with no owner (see fix_employer_columns.py / Step 9 report).
    employer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    # Step 9: whether the job is publicly visible / applicable to.
    is_active = Column(Boolean, nullable=False, default=True)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    profile_image = Column(String, nullable=True)
    # Step 9: application-level role, one of "candidate" or "employer".
    role = Column(String, nullable=False, default="candidate")
    # Step 9: employer-only display name; NULL for candidate accounts.
    company_name = Column(String, nullable=True)
    # Step 11: admin moderation flag. True for every existing/new user
    # unless an admin deactivates the account (see /admin/users/{id}/status).
    # A deactivated user fails login (see routes.py /login) but their row
    # and data are never deleted or altered otherwise.
    is_active = Column(Boolean, nullable=False, default=True)


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


class CandidateProfile(Base):
    """Step 10: candidate-only profile data (specialization, skills, CV),
    kept off the User table proper -- one-to-one via user_id (unique),
    matching the ForeignKey("users.id") pattern already used by
    Job.employer_id / Application.user_id. A user with no row here is a
    normal, expected state (mirrors a user with zero Application rows)."""
    __tablename__ = "candidate_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    specialization = Column(String, nullable=True)
    skills = Column(String, nullable=True)
    # Bare stored filename within CV_UPLOAD_DIR (routes.py) -- never a
    # public URL/path. NULL means "no CV uploaded", a normal valid state.
    cv_path = Column(String, nullable=True)
    cv_uploaded_at = Column(DateTime, nullable=True)

    user = relationship("User")
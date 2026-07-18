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

from sqlalchemy import Column, Integer, String

from database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    location = Column(String, nullable=False)
    salary = Column(String, nullable=False)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
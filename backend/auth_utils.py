"""
JWT utilities for EmpowerHR backend authentication.

Step 7.1 foundation: this module is only responsible for creating a JWT
that identifies an authenticated user. Verifying/decoding tokens on
protected endpoints is intentionally NOT implemented yet -- that is
Step 7.2+.

Step 7.2: adds `get_current_user`, a reusable FastAPI dependency that
verifies the JWT sent in the `Authorization: Bearer <token>` header and
resolves it to the corresponding `User` row. No endpoints are wired up
to use it yet -- that is Step 7.3.
"""

import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from database import get_db
from models import Job, User

# STEP 12 (H-1): fail closed by default. ENVIRONMENT now defaults to
# "production" -- a deployment that forgets to set ENVIRONMENT no longer
# silently falls back to a known, hardcoded JWT secret. The insecure
# fallback is now reachable only via an explicit, deliberate opt-in:
# ENVIRONMENT must be set to "development" AND ALLOW_DEV_JWT_SECRET must
# be set to "true".
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
SECRET_KEY = os.getenv("JWT_SECRET_KEY")

if not SECRET_KEY:
    if ENVIRONMENT == "development" and os.getenv("ALLOW_DEV_JWT_SECRET") == "true":
        # Explicit, opt-in-only local-development fallback.
        SECRET_KEY = "dev-secret-key-change-in-production"
    else:
        raise RuntimeError(
            "JWT_SECRET_KEY environment variable must be set. To use the "
            "local-development fallback secret instead, explicitly set "
            "ENVIRONMENT=development and ALLOW_DEV_JWT_SECRET=true."
        )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# auto_error=False: lets us raise our own 401 (with a consistent detail
# message) for a missing header, instead of FastAPI's default 403.
_bearer_scheme = HTTPBearer(auto_error=False)


def create_access_token(user_id: int, email: str) -> str:
    """Create a JWT whose payload identifies the given user.

    `sub` (subject) holds the user's id, which is the standard JWT claim
    for "who this token belongs to". `email` is included for convenience
    so it doesn't need a DB lookup to display who is logged in.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Reusable FastAPI dependency that resolves the authenticated User.

    Reads the `Authorization: Bearer <token>` header, verifies the JWT
    (signature, algorithm, and expiration) against the same SECRET_KEY /
    ALGORITHM used in Step 7.1, extracts the user id from the `sub`
    claim, and loads that user from the database.

    Raises HTTP 401 for every failure case: missing header, malformed/
    missing Bearer token, invalid JWT, expired JWT, missing/invalid
    `sub`, or a `sub` that doesn't match any user in the database.

    Usage in a future protected endpoint:
        @router.get("/some-protected-route")
        def handler(current_user: User = Depends(get_current_user)):
            ...
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Missing Authorization header, or a scheme other than "Bearer".
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise unauthorized

    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise unauthorized
    except jwt.InvalidTokenError:
        raise unauthorized

    user_id = payload.get("sub")
    if user_id is None:
        raise unauthorized

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        raise unauthorized

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise unauthorized

    return user


def get_current_employer(current_user: User = Depends(get_current_user)) -> User:
    """Reusable FastAPI dependency that resolves the authenticated User and
    additionally requires that the account's role (read exclusively from
    the DB row already resolved by get_current_user) is "employer".

    Raises HTTP 403 for any authenticated user whose role is not
    "employer" (e.g. "candidate"). Role is never read from the request
    body, query params, headers, or JWT claims -- only from the User row.
    """
    if current_user.role != "employer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employer account required",
        )
    return current_user


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Reusable FastAPI dependency that resolves the authenticated User and
    additionally requires that the account's role (read exclusively from
    the DB row already resolved by get_current_user) is "admin". Mirrors
    get_current_employer exactly.

    Raises HTTP 403 for any authenticated user whose role is not "admin"
    (e.g. "candidate" or "employer"). Role is never read from the request
    body, query params, headers, or JWT claims -- only from the User row.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account required",
        )
    return current_user


def get_owned_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_employer: User = Depends(get_current_employer),
) -> Job:
    """Reusable FastAPI dependency that loads a Job by job_id (a path
    parameter, matched automatically by FastAPI) and verifies the
    authenticated employer owns it.

    Raises HTTP 404 if no such job exists. Raises HTTP 403 if the job's
    employer_id does not match the current employer's id -- this also
    correctly rejects legacy/unowned jobs, since employer_id IS NULL
    never equals any real employer's id.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if job.employer_id != current_employer.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this job")

    return job
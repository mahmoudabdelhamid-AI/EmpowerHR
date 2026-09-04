"""
STEP 13 deployment-regression tests.

Batch 1 covers:
  - D-1: demo job auto-seeding gated behind an explicit SEED_DEMO_DATA
    opt-in (main.py), defaulting to off.
  - D-2: SQLite database path and upload directories anchored to a
    single, stable DATA_DIR instead of the process's current working
    directory (database.py / routes.py / main.py).

Batch 2 additionally covers:
  - D-6: environment-driven CORS allowed origins (main.py).
  - D-9: unauthenticated, DB-free health check endpoint (routes.py).

Follows the exact subprocess-isolation pattern already established by
test_step12_security.py's H-1 tests: spawn `python -c "..."` with a
controlled environment, since these behaviors are determined at import
time and must never touch the project's real database.db or uploads/
directories from the pytest process itself.
"""

import os
import subprocess
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routes import router


def _project_dir():
    return os.path.dirname(os.path.abspath(__file__))


def _base_env(data_dir):
    """A scrubbed environment safe for subprocess imports: explicit
    JWT_SECRET_KEY (so auth_utils doesn't fail closed / require the dev
    opt-in) and EMPOWERHR_DATA_DIR pointed at a disposable tmp_path so
    the real database.db/uploads/cv_uploads are never touched."""
    env = dict(os.environ)
    env["JWT_SECRET_KEY"] = "pytest-only-step13-secret"
    env["EMPOWERHR_DATA_DIR"] = str(data_dir)
    return env


# ---------------------------------------------------------------------------
# D-1: demo job seeding gate
# ---------------------------------------------------------------------------

def test_seed_demo_data_default_off(tmp_path):
    env = _base_env(tmp_path)
    env.pop("SEED_DEMO_DATA", None)

    code = (
        "import main\n"
        "from database import SessionLocal\n"
        "from models import Job\n"
        "db = SessionLocal()\n"
        "print('JOB_COUNT', db.query(Job).count())\n"
        "db.close()\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=_project_dir(),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "JOB_COUNT 0" in result.stdout


def test_seed_demo_data_explicit_opt_in(tmp_path):
    env = _base_env(tmp_path)
    env["SEED_DEMO_DATA"] = "true"

    code = (
        "import main\n"
        "from database import SessionLocal\n"
        "from models import Job\n"
        "db = SessionLocal()\n"
        "print('JOB_COUNT', db.query(Job).count())\n"
        "db.close()\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=_project_dir(),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "JOB_COUNT 2" in result.stdout


# ---------------------------------------------------------------------------
# D-2: stable data directory
# ---------------------------------------------------------------------------

def test_data_dir_defaults_to_database_py_directory_not_cwd(tmp_path):
    env = dict(os.environ)
    env["JWT_SECRET_KEY"] = "pytest-only-step13-secret"
    env.pop("EMPOWERHR_DATA_DIR", None)

    # Run from a different CWD than the project root to prove DATA_DIR
    # does not depend on the process's current working directory.
    code = (
        "import database\n"
        "print('DATA_DIR', database.DATA_DIR)\n"
        "print('BASE_DIR', database.BASE_DIR)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0 or "DATA_DIR" in result.stdout
    # database.py must be importable; since it's not on sys.path from a
    # foreign cwd, point PYTHONPATH at the project directory instead.
    env["PYTHONPATH"] = _project_dir()
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    lines = dict(
        line.split(" ", 1) for line in result.stdout.strip().splitlines()
    )
    assert lines["DATA_DIR"] == lines["BASE_DIR"]
    assert lines["DATA_DIR"] == _project_dir()
    assert lines["DATA_DIR"] != str(tmp_path)


def test_data_dir_honors_explicit_override(tmp_path):
    env = _base_env(tmp_path)

    code = (
        "import database\n"
        "print('DB_PATH', database.DB_PATH)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=_project_dir(),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    db_path_line = next(
        line for line in result.stdout.strip().splitlines()
        if line.startswith("DB_PATH ")
    )
    db_path = db_path_line.split(" ", 1)[1]
    assert db_path.startswith(str(tmp_path))


def test_upload_dirs_share_root_with_database(tmp_path):
    env = _base_env(tmp_path)

    code = (
        "import database\n"
        "import routes\n"
        "print('DATA_DIR', database.DATA_DIR)\n"
        "print('UPLOAD_DIR', routes.UPLOAD_DIR)\n"
        "print('CV_UPLOAD_DIR', routes.CV_UPLOAD_DIR)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=_project_dir(),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    lines = dict(
        line.split(" ", 1) for line in result.stdout.strip().splitlines()
    )
    assert lines["UPLOAD_DIR"].startswith(lines["DATA_DIR"])
    assert lines["CV_UPLOAD_DIR"].startswith(lines["DATA_DIR"])
    assert lines["DATA_DIR"] == str(tmp_path)

def test_data_dir_is_absolute_with_relative_env_override(tmp_path):
    env = os.environ.copy()
    env["EMPOWERHR_DATA_DIR"] = "relative_empowerhr_data"
    env["PYTHONPATH"] = _project_dir()

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import os; import database; "
            "print(database.DATA_DIR); "
            "assert os.path.isabs(database.DATA_DIR); "
            "assert database.DATA_DIR.endswith('relative_empowerhr_data')",
        ],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


# ---------------------------------------------------------------------------
# D-9: health endpoint
# ---------------------------------------------------------------------------

def test_health_endpoint_no_auth_no_db():
    # No dependency_overrides[get_db] set at all -- proves the endpoint
    # truly never touches the DB layer, unlike every other route in
    # this test suite.
    app = FastAPI()
    app.include_router(router)

    with TestClient(app) as test_client:
        response = test_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# D-6: CORS allowed origins
# ---------------------------------------------------------------------------

def test_cors_defaults_when_env_unset(tmp_path):
    env = _base_env(tmp_path)
    env.pop("ALLOWED_ORIGINS", None)

    code = (
        "import main\n"
        "print('ALLOWED_ORIGINS', main.ALLOWED_ORIGINS)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=_project_dir(),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    line = next(
        line for line in result.stdout.strip().splitlines()
        if line.startswith("ALLOWED_ORIGINS ")
    )
    origins = eval(line.split(" ", 1)[1])
    assert origins == [
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ]


def test_cors_parses_env_var(tmp_path):
    env = _base_env(tmp_path)
    env["ALLOWED_ORIGINS"] = " https://app.example.com ,https://admin.example.com,,"

    code = (
        "import main\n"
        "print('ALLOWED_ORIGINS', main.ALLOWED_ORIGINS)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=_project_dir(),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    line = next(
        line for line in result.stdout.strip().splitlines()
        if line.startswith("ALLOWED_ORIGINS ")
    )
    origins = eval(line.split(" ", 1)[1])
    assert origins == ["https://app.example.com", "https://admin.example.com"]


@pytest.mark.parametrize("value", ["", "   ,  "])
def test_cors_empty_env_falls_back_to_defaults(tmp_path, value):
    env = _base_env(tmp_path)
    env["ALLOWED_ORIGINS"] = value

    code = (
        "import main\n"
        "print('ALLOWED_ORIGINS', main.ALLOWED_ORIGINS)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=_project_dir(),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    line = next(
        line for line in result.stdout.strip().splitlines()
        if line.startswith("ALLOWED_ORIGINS ")
    )
    origins = eval(line.split(" ", 1)[1])
    assert origins == [
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ]
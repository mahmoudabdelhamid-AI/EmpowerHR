# EmpowerHR — Deployment Guide

This document covers running the EmpowerHR backend in production.
For local development, see the command in `main.py`'s docstring —
development workflow is unchanged by this guide.

## 1. Starting the server

**Development** (auto-reload, for local iteration only):

    uvicorn main:app --reload

**Production**:

    uvicorn main:app --host 0.0.0.0 --port 8000

Do not use `--reload` in production. Do not pass `--workers` with a
value greater than 1 (see "Single-worker requirement" below) --
omit `--workers` entirely, which defaults to a single worker
process.

## 2. Single-worker requirement (SQLite architecture)

This deployment MUST run as a single application process/worker.
Do not scale this app horizontally via multiple Uvicorn/Gunicorn
worker processes on the same machine, and do not run more than one
instance pointed at the same database.db file. Two concrete reasons:

1. **SQLite itself.** SQLite serializes writes at the file level;
   multiple concurrent writer processes increase the chance of
   "database is locked" errors under load.
2. **In-process rate limiting.** The STEP 12 (H-2) login/register
   rate limiter (`routes.py`, `_rate_limit_buckets`) is a plain
   in-memory dictionary scoped to a single Python process. Running
   multiple worker processes would give each process its own
   independent counters, silently multiplying the effective rate
   limit by the number of workers and weakening that already-closed
   security control.

If this application is later moved to PostgreSQL and a
process-shared or distributed rate limiter, multi-worker deployment
can be revisited then. That migration is explicitly out of scope
for the current architecture.

(Optional future consideration, not implemented: SQLite's WAL
journal mode can reduce lock contention between concurrent request
threads within a single worker process. This is not required for
a first deployment and is not enabled by this guide — revisit only
if write-lock contention is actually observed in production.)

## 3. Database migrations for a carried-forward database

On a **fresh** deployment (no existing database.db), no manual
action is needed: `Base.metadata.create_all(bind=engine)` in
`main.py` creates the full current schema automatically on startup.

On a deployment that carries forward an **existing** database.db
created before certain columns existed, run the following one-time
migration scripts before starting the app:

    python fix_profile_image_column.py
    python fix_employment_type_column.py
    python fix_employer_columns.py
    python fix_admin_columns.py

Notes:
- Each script only adds columns it finds missing and is a no-op
  (safe to re-run) if already applied. They do not depend on each
  other and can be run in any order; the order above simply
  reflects the rough order these features were introduced.
- **Important:** each script resolves its target database file via
  `EMPOWERHR_DATA_DIR` (see STEP 13 D-2), exactly like the running
  app does. If your deployment sets `EMPOWERHR_DATA_DIR`, set the
  same value in the environment before running these scripts, e.g.:

      EMPOWERHR_DATA_DIR=/var/data/empowerhr python fix_admin_columns.py

  Running a migration script with a different `EMPOWERHR_DATA_DIR`
  than the app uses will silently operate on the wrong file. If
  `EMPOWERHR_DATA_DIR` is unset, both the app and these scripts
  default to the project directory, and no special handling is
  needed.

## 4. Process management

This project currently ships with no process-manager configuration
(no Dockerfile, systemd unit, or Procfile). For a small first
deployment, running the production Uvicorn command above under
whatever process supervisor your hosting platform provides is
sufficient. A specific process-manager configuration should be
added once an actual hosting target is chosen -- do not add
speculative platform configuration ahead of that decision.

## 5. TLS/HTTPS and upload storage assumptions

**TLS/HTTPS:** This application does not terminate TLS itself and
does not set an HSTS header. HTTPS must be terminated by the
hosting platform, reverse proxy, or load balancer in front of this
app. Once HTTPS is confirmed working end-to-end for the actual
production domain, an HSTS header can be added to the existing
security-headers middleware in `main.py` (STEP 12 M-3). Do not add
HSTS before HTTPS is confirmed for that domain -- doing so can
break access if HTTPS is ever misconfigured or briefly unavailable.

**Upload storage:** Profile photos and CVs are currently stored on
local disk under `EMPOWERHR_DATA_DIR` (see below). This is
appropriate as long as the production deployment is a single,
persistent instance (i.e. the disk survives restarts/redeploys and
there is only one running instance at a time). If the eventual
hosting target uses ephemeral storage (files don't survive a
restart/redeploy) or runs multiple instances of this app
simultaneously, local disk storage will no longer be sufficient and
persistent/object storage should be introduced at that time -- do
not migrate storage before that requirement actually exists.

## 6. Environment variables (reference)

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `JWT_SECRET_KEY` | Yes (production) | none — fails closed | Signs/verifies JWTs (STEP 12 H-1) |
| `ENVIRONMENT` | No | `production` | Set to `development` only with `ALLOW_DEV_JWT_SECRET=true` for the local fallback secret |
| `ALLOW_DEV_JWT_SECRET` | No | unset | Opt-in for the local-dev JWT fallback; never set in production |
| `SEED_DEMO_DATA` | No | `false` | Set `true` only to seed the two demo jobs (dev/demo environments only) |
| `EMPOWERHR_DATA_DIR` | No | project directory | Where database.db, uploads/, and cv_uploads/ live |
| `ALLOWED_ORIGINS` | No | localhost dev origins | Comma-separated list of allowed CORS origins for production |

This table is a reference only; each variable's actual behavior is
defined in code (`auth_utils.py`, `main.py`, `database.py`).

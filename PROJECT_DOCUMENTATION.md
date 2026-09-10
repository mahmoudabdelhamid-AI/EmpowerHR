# EmpowerHR — Comprehensive Project Documentation

> **Status:** Active & Deployed (Demo / MVP)  
> **Source of Truth:** EmpowerHR codebase at current revision  
> **Verification Date:** September 2026  
> **Automated Test Status:** 127 passed, 0 failed (backend pytest suite)

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Current Features](#2-current-features)
3. [User Flows](#3-user-flows)
4. [Project Structure](#4-project-structure)
5. [Technology Stack](#5-technology-stack)
6. [Backend Architecture](#6-backend-architecture)
7. [Database Architecture](#7-database-architecture)
8. [Authentication & Authorization](#8-authentication--authorization)
9. [File Uploads](#9-file-uploads)
10. [Frontend Architecture](#10-frontend-architecture)
11. [Local Development](#11-local-development)
12. [Environment Variables](#12-environment-variables)
13. [Current Vercel Deployment](#13-current-vercel-deployment)
14. [Vercel Deployment Steps](#14-vercel-deployment-steps)
15. [Deployment Configuration Comparison](#15-deployment-configuration-comparison)
16. [Database Persistence & Demo Limitations](#16-database-persistence--demo-limitations)
17. [Testing](#17-testing)
18. [Troubleshooting](#18-troubleshooting)
19. [Security & Protection Controls](#19-security--protection-controls)
20. [Project Team](#20-project-team)
21. [Current Project Status](#21-current-project-status)

---

## 1. Project Overview

### 1.1 Project Name
**EmpowerHR** (منصة التوظيف الشامل)

### 1.2 Platform Purpose
EmpowerHR is an inclusive recruitment platform designed to connect qualified professionals with disabilities (ذوي الاحتياجات الخاصة) with inclusive employers seeking skilled talent. 

### 1.3 Problem Addressed
In Egypt and across the region, employment quotas for individuals with disabilities (such as the 5% legal quota — نسبة الـ 5%) often result in **tokenistic employment ("التوظيف الشكلي")**, where individuals are listed on company payrolls for legal compliance without meaningful work, skill utilization, or professional growth.

EmpowerHR addresses this by:
- Emphasizing **training and verified skills** rather than disability categories.
- Providing a direct channel for employers to advertise real, accessible roles and manage candidate pipelines.
- Giving candidates tools to showcase their profiles, skills, and CVs and track job applications transparently.

### 1.4 Main Users

1. **Candidate (Job Seeker):**
   - Individuals seeking meaningful employment.
   - Can register, log in, browse jobs, search by skill/title/location, view job specifications, submit job applications, manage profile details (full name, password, specialization, skills), upload a profile picture, and upload/manage a CV file (PDF/DOC/DOCX).

2. **Employer (Company / Recruiter):**
   - Companies looking to hire skilled professionals.
   - Can register with company name, log in, manage job postings (create, edit, activate/deactivate, delete), review applicant lists for their posted jobs, download candidate CVs, and update application statuses through five stages (`Pending`, `Reviewed`, `Interview`, `Accepted`, `Rejected`).

3. **Admin (Moderation — MVP Backend):**
   - Platform administration and compliance moderation.
   - **Current Implementation State:** Implemented at the **Backend API level only** (`/admin/*` endpoints). There is **no dedicated admin frontend UI** in the current project files.
   - Admin accounts are created/seeded directly in the database (there is intentionally no public admin registration endpoint).
   - Admins can inspect all users, deactivate/activate user accounts, inspect all job postings, and deactivate/activate any job posting globally.

### 1.5 Architecture at a Glance

```
+-----------------------------------------------------------------------------------+
|                                  EMPOWERHR SYSTEM                                 |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  [ FRONTEND - Static Web Application (HTML5 / Vanilla JS / CSS3 / RTL Arabic) ]   |
|                                                                                   |
|    - index.html (Job listings, Live Search, Details Modal)                        |
|    - login.html & register.html (Candidate Auth)                                  |
|    - profile.html (Profile management, Photo upload, CV upload)                   |
|    - applications.html (Application tracking & status badges)                     |
|    - employer-register.html & employer-dashboard.html (Employer Job & App Mgmt)   |
|                                                                                   |
+------------------------------------------+----------------------------------------+
                                           | Fetch Requests (REST API + Bearer JWT)
                                           v
+-----------------------------------------------------------------------------------+
|          [ BACKEND - FastAPI Application (Python 3.12 / ASGI / Pydantic) ]        |
|                                                                                   |
|    - Entrypoints: backend/main.py (Uvicorn) | api/index.py (Vercel Serverless)   |
|    - Middleware: CORS, Security Headers, Rate Limiting (In-Memory Fixed Window)   |
|    - Auth: PyJWT (HS256), pwdlib Argon2 password hashing                          |
|    - Storage Handlers: Public Profile Photos (/uploads) | Private CVs (/cv_uploads)|
+------------------------------------------+----------------------------------------+
                                           | SQLAlchemy ORM 2.0 (PRAGMA foreign_keys)
                                           v
+-----------------------------------------------------------------------------------+
|                     [ DATABASE - SQLite 3 (database.db) ]                         |
|                                                                                   |
|    - users (id, full_name, email, password, profile_image, role, company, active)|
|    - jobs (id, title, company, location, salary, employment_type, employer_id)    |
|    - applications (id, user_id, job_id, status, date_applied, UNIQUE(user,job))  |
|    - candidate_profiles (id, user_id, specialization, skills, cv_path, uploaded)  |
+-----------------------------------------------------------------------------------+
```

---

## 2. Current Features

### 2.1 Candidate Features

| Feature | Implementation Details | Endpoint / Asset |
|---|---|---|
| **Registration** | Creates a candidate account with `full_name`, `email`, and `password` (minimum 8 characters). The frontend form includes fields for `phone`, `city`, `birthDate`, and `accommodations`, but notes that these four fields are in development and not yet stored on the backend. Supports optional immediate photo and skills upload. | `POST /register`<br>`frontend/register.html` |
| **Login / Logout** | Authenticates via email and password (Argon2 verification). Returns a JWT Bearer token and user details stored in browser `localStorage`. Blocked if account is deactivated. Logout removes stored credentials. | `POST /login`<br>`frontend/login.html` |
| **Job Browsing** | Retrieves all active job postings (`is_active == True`). Renders job cards with company, location, and salary. | `GET /jobs`<br>`frontend/index.html` |
| **Search & Filtering** | Instantaneous, client-side search filtering over cached jobs by job title, company name, or location without repeated network requests. | `frontend/assets/js/app.js` |
| **Job Details** | Modal dialog accessible by clicking any job card. Displays full position details and direct application button. | `#dropdownModal`<br>`frontend/index.html` |
| **Applying to Jobs** | Authenticated application submission. Prevents duplicate applications via backend unique constraint and frontend validation. Employers are prohibited from applying (`403 Forbidden`). | `POST /jobs/{job_id}/apply`<br>`frontend/index.html` |
| **Applications Tracking** | Displays submitted applications newest first, complete with localized Arabic status badges (`قيد الانتظار`, `تمت المراجعة`, `مقابلة شخصية`, `مقبول`, `مرفوض`). | `GET /applications`<br>`frontend/applications.html` |
| **Profile Management** | View profile, update full name, and change account password. Email is read-only. | `GET /profile`<br>`PUT /profile`<br>`frontend/profile.html` |
| **Specialization & Skills** | Candidate profile fields (`specialization`, `skills`) stored in the dedicated `candidate_profiles` table. | `GET /profile/candidate`<br>`PUT /profile/candidate`<br>`frontend/profile.html` |
| **Profile Photo Upload** | Upload or update profile avatar. Validates file extension (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`), enforces a 5 MB maximum size, and validates actual file magic bytes. Publicly served at `/uploads/<filename>`. | `POST /profile/photo`<br>`frontend/profile.html` |
| **CV / Resume Management** | Upload, replace, or delete candidate CV. Allowed formats: PDF, DOC, DOCX. Max size: 10 MB. Validated via magic bytes and zip archive structure (`word/document.xml`). Private storage (never publicly served). | `POST /profile/cv`<br>`DELETE /profile/cv`<br>`frontend/profile.html` |

### 2.2 Employer Features

| Feature | Implementation Details | Endpoint / Asset |
|---|---|---|
| **Employer Registration** | Dedicated registration for employers requiring `full_name`, `company_name`, `email`, and `password`. The role is hardcoded server-side to `"employer"`. | `POST /employer/register`<br>`frontend/employer-register.html` |
| **Employer Authentication** | Logs in via the standard login endpoint. The user menu dynamically shows an "Employer Dashboard" link when `role === 'employer'`. | `POST /login`<br>`frontend/assets/js/authHeader.js` |
| **Employer Dashboard** | Single-page interface with 3 toggleable views: "My Jobs", "Create / Edit Job", and "Applicants". Guarded on frontend to redirect candidates or guests away. | `frontend/employer-dashboard.html`<br>`frontend/assets/js/employer-dashboard.js` |
| **Creating Jobs** | Creates a job listing. `company` is automatically derived server-side from the employer's `company_name`. `employer_id` is bound to the authenticated user. `is_active` defaults to `True`. Requires `employment_type`. | `POST /employer/jobs`<br>`frontend/employer-dashboard.html` |
| **Listing Owned Jobs** | Fetches only jobs where `employer_id == current_employer.id`. | `GET /employer/jobs`<br>`frontend/employer-dashboard.html` |
| **Editing Jobs** | Updates job title, location, salary, employment type, or active state. Ownership is strictly verified (`get_owned_job`). Company identity cannot be altered. | `PUT /employer/jobs/{job_id}`<br>`frontend/employer-dashboard.html` |
| **Toggling Job Visibility** | Quick one-click toggle to activate or deactivate a job listing. Inactive jobs are hidden from public candidate browsing and reject new applications. | `PUT /employer/jobs/{job_id}` (`is_active: bool`) |
| **Deleting Jobs** | Deletes a job posting if it has zero applications. If applications exist, the operation safely aborts with `409 Conflict` to preserve candidate application records. | `DELETE /employer/jobs/{job_id}`<br>`frontend/employer-dashboard.html` |
| **Viewing Applicants** | Lists candidates who applied to a specific owned job. Displays applicant name, email, application date, status, profile photo, and a boolean `has_cv` flag. Excludes sensitive data (passwords, tokens, internal paths). | `GET /employer/jobs/{job_id}/applicants`<br>`frontend/employer-dashboard.html` |
| **Updating Application Status** | Allows employer to progress candidates through five statuses: `Pending`, `Reviewed`, `Interview`, `Accepted`, `Rejected`. Backward status transitions are permitted. Ownership verified through Application → Job → Employer. | `PATCH /employer/applications/{application_id}/status` |
| **Downloading Applicant CV** | Secure binary stream download of candidate CV file. Verifies employer ownership of the job associated with the application. Never serves files via public URLs. | `GET /employer/applications/{application_id}/cv` |

### 2.3 Admin Features (Backend Only)

*Note: No frontend user interface exists for admin operations in the current project.*

| Feature | Implementation Details | Endpoint |
|---|---|---|
| **List All Users** | Lists all registered accounts across all roles (`candidate`, `employer`, `admin`), including moderation status (`is_active`). Passwords are never returned. | `GET /admin/users` |
| **Update User Status** | Moderation action to activate or deactivate any user account (`is_active: bool`). Deactivated users are blocked from logging in. | `PATCH /admin/users/{user_id}/status` |
| **List All Jobs** | Lists all jobs across all employers, including inactive and legacy unowned jobs. | `GET /admin/jobs` |
| **Update Job Status** | Moderation action to globally activate or deactivate any job posting (`is_active: bool`). | `PATCH /admin/jobs/{job_id}/status` |

---

## 3. User Flows

### 3.1 Candidate User Flow

```
[ Visitor ]
    │
    ▼
1. Visit register.html
    │ Submits form (full_name, email, password >= 8 chars)
    ▼
   POST /register  ──────> (Optional temp login: POST /profile/photo & PUT /profile/candidate)
    │
    ▼
2. Redirect to login.html (sees success alert from sessionStorage)
    │ Submits email & password
    ▼
   POST /login ──────────> Returns JWT access_token & User object
    │                      Saved to localStorage: 'accessToken', 'currentUser'
    ▼
3. Browse index.html
    │ Calls GET /jobs (loads active jobs into memory)
    │ Types in .search-bar to filter client-side by title/company/location
    ▼
4. Click Job Card
    │ Opens #dropdownModal with company, salary, location
    ▼
5. Click "تقديم الآن" (Apply Now)
    │ Calls POST /jobs/{job_id}/apply with Authorization: Bearer <token>
    ▼ Backend creates Application record (status: "Pending")
    │ Shows inline success message
    ▼
6. Visit applications.html
    │ Calls GET /applications with Bearer token
    ▼ Displays list of submitted applications with live status badges
    │
7. Visit profile.html
    │ Calls GET /profile and GET /profile/candidate
    │ - Upload Photo: POST /profile/photo (PNG/JPG/WEBP, <= 5MB)
    │ - Upload CV: POST /profile/cv (PDF/DOC/DOCX, <= 10MB)
    │ - Edit Info: PUT /profile (name, password) & PUT /profile/candidate (skills, field)
```

### 3.2 Employer User Flow

```
[ Recruiter ]
    │
    ▼
1. Visit employer-register.html
    │ Submits form (full_name, company_name, email, password)
    ▼
   POST /employer/register ───> Role hardcoded to "employer"
    │
    ▼
2. Redirect to login.html ───> Logs in via POST /login
    │ Header dropdown displays "Employer Dashboard" link
    ▼
3. Visit employer-dashboard.html
    │ Auth guard: Redirects to login.html if not logged in;
    │             Redirects to index.html if role !== 'employer'
    ▼
4. Calls GET /employer/jobs ───> Displays owned jobs
    │
    ├─► Click "إضافة وظيفة جديدة" (Add Job)
    │     │ Opens Create View
    │     ▼ Calls POST /employer/jobs (company derived automatically)
    │
    ├─► Click "تعديل" (Edit Job)
    │     │ Opens Edit View
    │     ▼ Calls PUT /employer/jobs/{id}
    │
    ├─► Click "إيقاف / تفعيل" (Toggle Active)
    │     ▼ Calls PUT /employer/jobs/{id} with is_active: !current
    │
    ├─► Click "حذف" (Delete Job)
    │     ▼ Calls DELETE /employer/jobs/{id} (fails with 409 if applications exist)
    │
    └─► Click "عرض المتقدمين" (View Applicants)
          │ Opens Applicants View
          ▼ Calls GET /employer/jobs/{id}/applicants
          │ Displays applicants list with date, email, and status
          │
          ├─► If applicant.has_cv == true:
          │     Click "عرض السيرة الذاتية" ──> GET /employer/applications/{app_id}/cv
          │                                  Downloads binary file blob
          │
          └─► Change status dropdown:
                Calls PATCH /employer/applications/{app_id}/status
                (Pending -> Reviewed -> Interview -> Accepted -> Rejected)
```

---

## 4. Project Structure

```
EmpowerHR/
│
├── .gitignore                     # Git ignore rules (virtualenv, cache, db, uploads)
├── DEPLOYMENT.md                  # Deployment operational runbook
├── PROJECT_DOCUMENTATION.md       # Primary technical project documentation (this file)
│
├── api/                           # Vercel serverless functions entrypoint
│   └── index.py                   # Vercel Python entrypoint; mounts backend/main.py
│
├── backend/                       # FastAPI backend application
│   ├── auth_utils.py              # JWT token generation, get_current_user, role dependencies
│   ├── conftest.py                # Pytest shared configuration / root fixtures
│   ├── database.py                # SQLAlchemy engine, session factory, DATA_DIR resolution
│   ├── database.db                # Local SQLite database file (gitignored)
│   ├── database_backup.db         # Local database backup file (gitignored)
│   ├── fix_admin_columns.py       # Migration: adds users.is_active column
│   ├── fix_employer_columns.py    # Migration: adds users.role, users.company_name, jobs columns
│   ├── fix_employment_type_column.py # Migration: adds jobs.employment_type column
│   ├── fix_profile_image_column.py   # Migration: adds users.profile_image column
│   ├── main.py                    # FastAPI app initialization, middleware, static mounts
│   ├── models.py                  # SQLAlchemy ORM models (User, Job, Application, CandidateProfile)
│   ├── requirements.txt           # Python dependencies and exact pinned versions
│   ├── routes.py                  # FastAPI route definitions and file upload logic
│   ├── schemas.py                 # Pydantic validation models and request/response schemas
│   │
│   ├── uploads/                   # Local storage for profile photos (gitignored)
│   ├── cv_uploads/                # Local storage for candidate CV documents (gitignored)
│   │
│   ├── test_admin_routes.py       # Tests: admin endpoints and moderation
│   ├── test_candidate_profile_cv.py # Tests: candidate profile and CV upload/download
│   ├── test_employer_auth_dependencies.py # Tests: employer auth checks and ownership
│   ├── test_employer_routes.py    # Tests: employer CRUD, applicants, status updates
│   ├── test_profile_auth.py       # Tests: profile endpoints and photo upload auth
│   ├── test_step12_security.py    # Tests: security controls (rate limits, magic bytes, etc.)
│   └── test_step13_deployment.py  # Tests: deployment flags, CORS, data directory
│
├── frontend/                      # Static frontend client (Vanilla HTML/CSS/JS)
│   ├── index.html                 # Homepage: active job listings, search, details modal
│   ├── login.html                 # Authentication login form
│   ├── register.html              # Candidate account registration form
│   ├── profile.html               # Candidate profile view, photo upload, CV management
│   ├── applications.html          # Candidate job application tracking
│   ├── employer-register.html     # Employer registration form
│   ├── employer-dashboard.html    # Employer portal (job CRUD, applicant list, status management)
│   │
│   └── assets/
│       ├── css/
│       │   ├── style.css          # Main responsive stylesheet, theme variables, RTL layout
│       │   └── applications.css   # Styles for application cards and status badges
│       ├── images/                # Static frontend image assets
│       └── js/
│           ├── api.js             # API client, API_BASE_URL resolution, apiFetch wrapper
│           ├── app.js             # Homepage job rendering, live search, details modal
│           ├── applications.js    # Candidate application list logic
│           ├── auth.js            # Frontend auth state (localStorage currentUser/token)
│           ├── authHeader.js      # Global header navigation and account dropdown controller
│           ├── employer-dashboard.js # Employer job and applicant management controller
│           ├── employer-register.js  # Employer registration form logic
│           ├── login.js           # Login form submission and session setup
│           ├── photoUpload.js     # Client-side FileReader preview for registration photo
│           ├── profile.js         # Profile editor, photo upload, and CV upload controller
│           └── register.js        # Candidate registration form logic
│
└── uploads/                       # Root directory placeholder for uploads
```

---

## 5. Technology Stack

### 5.1 Frontend
- **Markup:** HTML5 semantic markup with right-to-left language orientation (`lang="ar" dir="rtl"`).
- **Styling:** Vanilla CSS3 using modern CSS grid, flexbox, CSS custom properties, and responsive media queries.
- **Scripting:** Vanilla ECMAScript Modules (ESM) using native `import` / `export` syntax without build tools, bundlers, or transpilers.
- **Browser APIs:** Fetch API, FormData API, FileReader API, URL.createObjectURL, IntersectionObserver API (for animated counter statistics).
- **State & Storage:** Web Storage API (`localStorage` for persistent JWT and user state, `sessionStorage` for one-time cross-page success handoffs).

### 5.2 Backend
- **Language:** Python 3.12+
- **Framework:** FastAPI `0.115.0`
- **ASGI Web Server:** Uvicorn `0.30.6`
- **Database ORM:** SQLAlchemy `2.0.35`
- **Data Validation:** Pydantic `2.9.2`
- **Authentication & Tokens:** PyJWT `2.9.0` (JSON Web Tokens using HS256 HMAC)
- **Password Hashing:** `pwdlib[argon2] 0.3.0` (Argon2 password hashing algorithm)
- **Form & File Handling:** `python-multipart 0.0.18`

### 5.3 Automated Testing
- **Test Runner:** Pytest `8.3.3`
- **HTTP Client:** HTTPX `0.27.2` (via FastAPI `TestClient`)

### 5.4 Hosting & Deployment
- **Frontend Hosting:** Vercel Static Hosting
- **Backend Hosting:** Vercel Python Serverless Functions (via `api/index.py`)
- **Source Control & CI/CD:** GitHub (`mahmoudabdelhamid-AI/EmpowerHR`) with automatic Vercel deployment webhooks.

---

## 6. Backend Architecture

### 6.1 Application Initialization
The backend has two operational entry points:
1. **Standalone Uvicorn (`backend/main.py`):** Used during local development and containerized production deployments. Initializes the FastAPI app, attaches CORS middleware, mounts `/uploads` as static files, applies security headers, and includes the main router.
2. **Vercel Serverless Entrypoint (`api/index.py`):** Adjusts `sys.path` to load `backend/main.py`, imports `app`, and adds a middleware to strip the `/api` prefix from incoming request paths when Vercel routes traffic.

### 6.2 Middleware Stack
1. **CORS Middleware (`CORSMiddleware`):** Configured with origins parsed from the `ALLOWED_ORIGINS` environment variable. Explicitly permits credentials (`allow_credentials=True`), all HTTP methods, and all headers.
2. **Security Headers Middleware:** Minimal baseline security headers attached to every response:
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: DENY`
   - `Referrer-Policy: strict-origin-when-cross-origin`
3. **In-Memory Rate Limiter:** Protects unauthenticated endpoints (`/login`, `/register`, `/employer/register`). Restricts clients to 5 requests per 60-second window per client IP address. Exceeding this threshold raises `HTTP 429 Too Many Requests`.

### 6.3 API Endpoint Table

| HTTP Method | Route | Description | Auth Required | Authorized Roles |
|---|---|---|---|---|
| `GET` | `/health` | Liveness check (no DB dependency, no auth) | No | Public |
| `GET` | `/jobs` | List active job listings | No | Public |
| `POST` | `/register` | Register a new candidate account | No | Public (Rate-limited) |
| `POST` | `/login` | Authenticate user and issue JWT | No | Public (Rate-limited) |
| `POST` | `/employer/register` | Register a new employer account | No | Public (Rate-limited) |
| `POST` | `/jobs/{job_id}/apply` | Submit an application for an active job | Yes | Candidate only |
| `GET` | `/applications` | View all applications submitted by candidate | Yes | Candidate only |
| `GET` | `/profile` | Retrieve own user profile | Yes | Candidate, Employer, Admin |
| `PUT` | `/profile` | Update own full name and/or password | Yes | Candidate, Employer, Admin |
| `POST` | `/profile/photo` | Upload or update personal profile photo | Yes | Candidate, Employer, Admin |
| `GET` | `/profile/candidate` | Retrieve candidate specialization and skills | Yes | Candidate |
| `PUT` | `/profile/candidate` | Update candidate specialization and skills | Yes | Candidate |
| `POST` | `/profile/cv` | Upload or replace CV document | Yes | Candidate |
| `DELETE` | `/profile/cv` | Delete uploaded CV document | Yes | Candidate |
| `GET` | `/employer/jobs` | List jobs posted by authenticated employer | Yes | Employer only |
| `POST` | `/employer/jobs` | Post a new job under employer's company | Yes | Employer only |
| `PUT` | `/employer/jobs/{job_id}` | Edit an existing owned job posting | Yes | Employer (Owner only) |
| `DELETE` | `/employer/jobs/{job_id}` | Delete owned job (fails if applications exist) | Yes | Employer (Owner only) |
| `GET` | `/employer/jobs/{job_id}/applicants` | List applicants for an owned job | Yes | Employer (Owner only) |
| `PATCH` | `/employer/applications/{app_id}/status` | Update status of an application | Yes | Employer (Job Owner) |
| `GET` | `/employer/applications/{app_id}/cv` | Download an applicant's uploaded CV | Yes | Employer (Job Owner) |
| `GET` | `/admin/users` | List all users across the platform | Yes | Admin only |
| `PATCH` | `/admin/users/{user_id}/status` | Activate or deactivate a user account | Yes | Admin only |
| `GET` | `/admin/jobs` | List all jobs across all employers | Yes | Admin only |
| `PATCH` | `/admin/jobs/{job_id}/status` | Activate or deactivate any job globally | Yes | Admin only |

---

## 7. Database Architecture

### 7.1 Database Engine
- **Engine:** SQLite 3 via SQLAlchemy.
- **Connection Configuration:** `connect_args={"check_same_thread": False}`.
- **Foreign Key Enforcement:** SQLite does not enforce foreign keys by default. EmpowerHR attaches an event listener on the SQLAlchemy engine (`@event.listens_for(engine, "connect")`) that executes `PRAGMA foreign_keys=ON` on every DBAPI connection.
- **File Location:** Anchored to `DATA_DIR/database.db`. `DATA_DIR` defaults to the directory containing `database.py` (`backend/`), but can be overridden via the `EMPOWERHR_DATA_DIR` environment variable.

### 7.2 Entity-Relationship Schema

```
+-----------------------------------+        +-----------------------------------+
|               users               |        |               jobs                |
+-----------------------------------+        +-----------------------------------+
| id            INTEGER (PK)        |<---+   | id              INTEGER (PK)      |<---+
| full_name     VARCHAR (NOT NULL)  |    |   | title           VARCHAR (NOT NULL)  |    |
| email         VARCHAR (UNIQUE)    |    +---| employer_id     INTEGER (FK->users) |    |
| password      VARCHAR (NOT NULL)  |    |   | company         VARCHAR (NOT NULL)  |    |
| profile_image VARCHAR (NULLABLE)  |    |   | location        VARCHAR (NOT NULL)  |    |
| role          VARCHAR (DEFAULT)   |    |   | salary          VARCHAR (NOT NULL)  |    |
| company_name  VARCHAR (NULLABLE)  |    |   | employment_type VARCHAR (DEFAULT)   |    |
| is_active     BOOLEAN (DEFAULT 1) |    |   | is_active       BOOLEAN (DEFAULT 1) |    |
+-----------------------------------+    |   +-----------------------------------+    |
          |               ^              |                                            |
          | 1             | 1            |                                            |
          |               |              |                                            |
          v 1             |              |                                            |
+--------------------+    |              |   +-----------------------------------+    |
| candidate_profiles |    |              |   |            applications           |    |
+--------------------+    |              |   +-----------------------------------+    |
| id             (PK)|    |              |   | id            INTEGER (PK)        |    |
| user_id (FK,UNIQUE)+----+              +---| user_id       INTEGER (FK->users) |    |
| specialization     |                       | job_id        INTEGER (FK->jobs)  +----+
| skills             |                       | status        VARCHAR (DEFAULT)   |
| cv_path            |                       | date_applied  DATETIME            |
| cv_uploaded_at     |                       | CONSTRAINT uq_user_job UNIQUE     |
+--------------------+                       +-----------------------------------+
```

### 7.3 Schema Migrations
EmpowerHR uses a **non-destructive, idempotent migration script pattern** for databases carried forward across development steps:
1. `fix_profile_image_column.py`: Adds `profile_image VARCHAR` to `users`.
2. `fix_employment_type_column.py`: Adds `employment_type VARCHAR NOT NULL DEFAULT 'Full-time'` to `jobs`.
3. `fix_employer_columns.py`: Adds `role VARCHAR NOT NULL DEFAULT 'candidate'` and `company_name VARCHAR` to `users`, and `employer_id INTEGER REFERENCES users(id)` and `is_active BOOLEAN NOT NULL DEFAULT 1` to `jobs`.
4. `fix_admin_columns.py`: Adds `is_active BOOLEAN NOT NULL DEFAULT 1` to `users`.

Each script inspects `sqlite_master` and table PRAGMA metadata before modifying tables, ensuring safe repeated execution without data loss.

---

## 8. Authentication & Authorization

### 8.1 JWT Architecture
- **Token Type:** JSON Web Token (JWT) with standard Bearer authorization scheme.
- **Algorithm:** `HS256` (HMAC with SHA-256).
- **Expiration:** 24 hours (`ACCESS_TOKEN_EXPIRE_MINUTES = 1440`).
- **Claims Payload:**
  - `sub`: User ID (string integer).
  - `email`: User email address.
  - `exp`: Expiration timestamp in UTC.

### 8.2 Security Fail-Closed Design
`backend/auth_utils.py` enforces a **fail-closed security posture**:
- The `ENVIRONMENT` environment variable defaults to `"production"`.
- If `JWT_SECRET_KEY` is missing in production, the application **raises `RuntimeError` immediately** and refuses to start.
- A hardcoded fallback secret (`dev-secret-key-change-in-production`) is allowed **only if two explicit conditions are both met**:
  `ENVIRONMENT=development` AND `ALLOW_DEV_JWT_SECRET=true`.

### 8.3 Authorization Dependencies
FastAPI dependency injection enforces authorization at route execution:
1. `get_current_user`: Decodes and validates the Bearer JWT, extracts `sub`, loads the user from the database, and verifies the user exists and is active.
2. `get_current_employer`: Depends on `get_current_user`. Reads the user's role fresh from the database and raises `403 Forbidden` if `current_user.role != "employer"`.
3. `get_current_admin`: Depends on `get_current_user`. Reads the user's role fresh from the database and raises `403 Forbidden` if `current_user.role != "admin"`.
4. `get_owned_job`: Dependency matching `{job_id}` in path. Queries the job and asserts `job.employer_id == current_employer.id`. Raises `404 Not Found` if missing, or `403 Forbidden` if unowned or owned by another employer.

---

## 9. File Uploads

EmpowerHR maintains a strict separation between **public profile pictures** and **private CV documents**.

```
+--------------------------+-----------------------------------+-----------------------------------+
| Attribute                | Profile Photos                    | Candidate CVs                     |
+--------------------------+-----------------------------------+-----------------------------------+
| Storage Location         | DATA_DIR/uploads/                 | DATA_DIR/cv_uploads/              |
| Static Server Mount      | Mounted at /uploads (Public)      | NEVER MOUNTED (Private)           |
| Allowed Extensions       | .png, .jpg, .jpeg, .gif, .webp    | .pdf, .doc, .docx                 |
| Maximum File Size        | 5 MB                              | 10 MB                             |
| Size Validation          | Direct byte reading (len(content))| Direct byte reading (len(content))|
| Content Validation       | Magic bytes signature matching    | Magic bytes (.pdf/.doc) &         |
|                          |                                   | Zip structure (.docx word/doc.xml)|
| Database Field           | users.profile_image (path URL)    | candidate_profiles.cv_path (bare) |
| Access Control           | Public HTTP GET                   | Authenticated Employer Ownership  |
| Download Endpoint        | Direct static URL                 | GET /employer/applications/{id}/cv|
| Replacement Policy       | Overwrites DB pointer             | Commits new file, deletes old file|
| Deletion Endpoint        | Not exposed directly              | DELETE /profile/cv                |
+--------------------------+-----------------------------------+-----------------------------------+
```

---

## 10. Frontend Architecture

### 10.1 Page Overview

| HTML File | Primary JS Module | Purpose & Core Interactions |
|---|---|---|
| `index.html` | `assets/js/app.js`<br>`assets/js/authHeader.js` | Main landing page. Fetches `/jobs` and renders job cards. Instant client-side search filtering. Opens job details modal. Handles candidate job applications. |
| `login.html` | `assets/js/login.js` | Form for email/password authentication. Displays one-time registration success message from `sessionStorage`. Saves JWT and user details to `localStorage`. |
| `register.html` | `assets/js/register.js`<br>`assets/js/photoUpload.js` | Candidate registration form. Client-side password confirmation. Supports optional profile image preview and post-registration upload session. |
| `profile.html` | `assets/js/profile.js`<br>`assets/js/authHeader.js` | Profile management page. Edit full name, change password, upload/change profile photo, upload/delete CV, and update specialization and skills. |
| `applications.html` | `assets/js/applications.js`<br>`assets/js/authHeader.js` | Track submitted job applications. Displays company, location, salary, employment type, application date, and localized Arabic status badges. |
| `employer-register.html`| `assets/js/employer-register.js` | Employer registration form. Collects full name, company name, email, and password. Redirects to login on success. |
| `employer-dashboard.html`| `assets/js/employer-dashboard.js`<br>`assets/js/authHeader.js`| Three-in-one employer portal: "My Jobs", "Create/Edit Job", and "Applicants". Toggles active job states, deletes jobs, updates application statuses, downloads CVs. |

### 10.2 Shared JavaScript Modules

- `assets/js/api.js`: Centralized HTTP communications layer. Defines `API_BASE_URL` with inline script override support. Implements `apiFetch` wrapper providing unified error parsing for FastAPI error shapes and connection error fallbacks.
- `assets/js/auth.js`: Single source of truth for frontend auth state. Manages `localStorage` operations for `currentUser` and `accessToken`. Exposes `isLoggedIn()`, `getToken()`, and `logout()`.
- `assets/js/authHeader.js`: Manages the shared header state across all pages. Renders user avatar, full name, dropdown menu, and dynamic "Employer Dashboard" link for employer accounts. Handles logout.
- `assets/js/photoUpload.js`: Lightweight FileReader helper that updates `.photo-placeholder` background image on local image selection during candidate registration.

---

## 11. Local Development

### 11.1 Backend Setup

#### Step 1: Open Terminal and Navigate to Backend
```powershell
cd d:\projects\EmpowerHR\backend
```

#### Step 2: Activate Virtual Environment
```powershell
# Windows PowerShell
..\.venv\Scripts\Activate.ps1

# Windows CMD
..\.venv\Scripts\activate.bat

# Linux / macOS (for reference)
source ../.venv/bin/activate
```

#### Step 3: Install Dependencies
```powershell
pip install -r requirements.txt
```

#### Step 4: Configure Environment Variables
Set the development fallback flags in your terminal session:
```powershell
# PowerShell
$env:ENVIRONMENT = "development"
$env:ALLOW_DEV_JWT_SECRET = "true"
$env:SEED_DEMO_DATA = "true"

# CMD
set ENVIRONMENT=development
set ALLOW_DEV_JWT_SECRET=true
set SEED_DEMO_DATA=true
```

#### Step 5: Run Schema Migrations (If carrying forward an existing database.db)
```powershell
python fix_profile_image_column.py
python fix_employment_type_column.py
python fix_employer_columns.py
python fix_admin_columns.py
```

#### Step 6: Start the Server

**Development Mode (with auto-reload on file changes):**
```powershell
uvicorn main:app --reload
```

**Production-Style Mode (single worker process on port 8000):**
```powershell
uvicorn main:app --host 0.0.0.0 --port 8000
```

The API will be available at: `http://127.0.0.1:8000`  
Swagger API Documentation: `http://127.0.0.1:8000/docs`  
Health Check: `http://127.0.0.1:8000/health`

---

### 11.2 Frontend Setup

> **Important:** Do NOT open frontend HTML files via the file system (`file:///d:/projects/...`). Modern browsers block ECMAScript module imports (`import` / `export`) and cross-origin fetch requests when loaded over the `file://` protocol. A local HTTP server is required.

#### Option A: Python Built-in HTTP Server (Recommended)
From the project root:
```powershell
python -m http.server 5500 -d frontend
```
Local Frontend URL: `http://127.0.0.1:5500`

#### Option B: VS Code Live Server Extension
Open the `frontend/` folder in VS Code, right-click `index.html`, and select **"Open with Live Server"**.  
Default URL: `http://127.0.0.1:5500`

---

### 11.3 Local API URL Configuration

In `frontend/assets/js/api.js`, the API base URL is resolved as:
```javascript
const API_BASE_URL = (typeof window !== 'undefined' && window.EMPOWERHR_API_BASE_URL) || 'http://127.0.0.1:8000';
```

Currently, all HTML pages contain an inline `<script>` block setting the deployed backend URL:
```html
<script>
    window.EMPOWERHR_API_BASE_URL = 'https://backend-psi-neon-83.vercel.app';
</script>
```

#### Switching Frontend Local → Backend Local:
To point your local frontend to your locally running backend (`http://127.0.0.1:8000`), simply change the inline script in the HTML file you are testing (or delete the inline script, letting `api.js` fall back to `http://127.0.0.1:8000`):
```html
<script>
    window.EMPOWERHR_API_BASE_URL = 'http://127.0.0.1:8000';
</script>
```

#### Switching Frontend Local → Deployed Backend:
Keep the inline script as currently configured:
```html
<script>
    window.EMPOWERHR_API_BASE_URL = 'https://backend-psi-neon-83.vercel.app';
</script>
```

---

## 12. Environment Variables

| Variable | Required? | Purpose | Local Example | Vercel Usage |
|---|---|---|---|---|
| `JWT_SECRET_KEY` | **Yes** (in production) | Secret key used to sign and verify HMAC-SHA256 JWT tokens. | `<your-secret>` | Configured in Vercel Backend Project settings. |
| `ENVIRONMENT` | No (Defaults to `production`) | Environment mode. When set to `development`, allows local JWT secret fallback if `ALLOW_DEV_JWT_SECRET=true`. | `development` | Set to `production` (or left unset). |
| `ALLOW_DEV_JWT_SECRET` | No (Defaults to unset) | Explicit opt-in flag required to enable fallback JWT secret when `ENVIRONMENT=development`. | `true` | **Never** set in Vercel production. |
| `SEED_DEMO_DATA` | No (Defaults to `false`) | When `true`, automatically seeds two demo job listings on startup if database is empty. | `true` | Set to `true` on Vercel to populate demo jobs on cold start. |
| `ALLOWED_ORIGINS` | No (Defaults to localhost dev origins) | Comma-separated list of allowed CORS origins for browser requests. | `http://127.0.0.1:5500,http://localhost:5500` | `https://empower-hr-beta.vercel.app` |
| `EMPOWERHR_DATA_DIR` | No (Defaults to `backend/`) | Absolute directory path where `database.db`, `uploads/`, and `cv_uploads/` are stored. | `d:\projects\EmpowerHR\backend` | `/tmp/empowerhr` (ensures writable disk on serverless). |

---

## 13. Current Vercel Deployment

### 13.1 Production URLs
- **Live Frontend:** [`https://empower-hr-beta.vercel.app`](https://empower-hr-beta.vercel.app)
- **Live Backend API:** [`https://backend-psi-neon-83.vercel.app`](https://backend-psi-neon-83.vercel.app)
- **Live Backend Health Check:** [`https://backend-psi-neon-83.vercel.app/health`](https://backend-psi-neon-83.vercel.app/health)

### 13.2 Clarification on the Backend Hostname
> **Note on "neon":** The word `neon` in the URL `backend-psi-neon-83.vercel.app` is an **automatically generated random suffix** produced by Vercel's project naming generator (e.g. `psi`, `neon`, `83`). **It does NOT mean the project uses Neon Serverless Postgres.** The project uses SQLite on disk.

### 13.3 Deployment Architecture Diagram

```
[ BROWSER CLIENT ]
       │
       ├─────────────────────────────────────────┐
       ▼ (HTTPS)                                 ▼ (HTTPS Cross-Origin API Requests)
+─────────────────────────────────+       +─────────────────────────────────────────────+
|   Vercel Frontend Project       |       |   Vercel Backend Project                    |
|   https://empower-hr-beta...    |       |   https://backend-psi-neon-83...            |
+─────────────────────────────────+       +─────────────────────────────────────────────+
| - Root: frontend/               |       | - Serverless Function via api/index.py      |
| - Static CDN Edge Hosting       |       | - Python 3.12 Runtime                       |
| - window.EMPOWERHR_API_BASE_URL |       | - CORS: ALLOWED_ORIGINS=https://empower-hr..|
|   points to backend URL         |       | - DATA_DIR: /tmp/empowerhr                  |
+─────────────────────────────────+       +──────────────────────┬──────────────────────+
                                                                 │
                                                                 ▼
                                                  +─────────────────────────────+
                                                  |   Ephemeral /tmp Storage    |
                                                  |   - /tmp/empowerhr/         |
                                                  |     ├── database.db (SQLite)|
                                                  |     ├── uploads/            |
                                                  |     └── cv_uploads/         |
                                                  +─────────────────────────────+
```

### 13.4 Why Frontend and Backend are Deployed Separately
- **Frontend:** Pure static HTML, CSS, and JS files. Deploying as a static site allows Vercel to serve assets via global Content Delivery Networks (CDNs) with near-zero latency and instant caching.
- **Backend:** A dynamic Python ASGI application requiring the Vercel Python Serverless Function runtime. Vercel executes serverless functions on demand. Separating them decouples frontend deployments from backend runtime configurations.

---

## 14. Vercel Deployment Steps

A repeatable deployment procedure from local code to live production:

### Step 1: Run Automated Tests Locally
Ensure all backend tests pass before committing:
```powershell
.venv\Scripts\pytest -v backend
```
Expected output: `127 passed`.

### Step 2: Verify Git Working Tree
```powershell
git status
```
Ensure no untracked or unwanted files (such as temporary `.db` files or secret `.env` files) are staged.

### Step 3: Commit Changes
```powershell
git add .
git commit -m "Your descriptive commit message"
```

### Step 4: Push to GitHub
```powershell
git push origin main
```

### Step 5: Vercel Automatic Build & Deploy
Once pushed to `origin/main`, Vercel webhooks trigger automatic deployments for both connected projects:
1. **Frontend Project:** Pulls latest `frontend/` changes and updates the global CDN edge.
2. **Backend Project:** Builds the Python serverless function package from `api/index.py` and `backend/requirements.txt`.

### Step 6: Verify Deployment
1. Verify backend health:
   ```powershell
   curl https://backend-psi-neon-83.vercel.app/health
   ```
   Should return: `{"status": "ok"}`
2. Open [`https://empower-hr-beta.vercel.app`](https://empower-hr-beta.vercel.app) in your browser.
3. Test candidate browsing and employer dashboard flows.

---

## 15. Deployment Configuration Comparison

| Configuration Property | Local Development | Vercel Serverless Deployment |
|---|---|---|
| **Frontend Serving** | Local HTTP server (`python -m http.server 5500`) | Vercel Static Edge CDN |
| **Backend Serving** | `uvicorn main:app --reload` (port 8000) | Vercel Serverless Function via `api/index.py` |
| **Backend Root** | `d:\projects\EmpowerHR\backend` | Project root (with `sys.path` to `backend`) |
| **Data Directory (`EMPOWERHR_DATA_DIR`)** | Defaults to `backend/` directory | `/tmp/empowerhr` |
| **Database File** | `backend/database.db` (persistent on disk) | `/tmp/empowerhr/database.db` (ephemeral) |
| **File Upload Storage** | `backend/uploads/` & `backend/cv_uploads/` | `/tmp/empowerhr/uploads/` & `.../cv_uploads/` |
| **Demo Data Seeding** | Controlled by local environment (`$env:SEED_DEMO_DATA`) | Set to `true` so demo jobs re-seed if container resets |
| **CORS Origins** | `http://127.0.0.1:5500`, `http://localhost:5500` | `https://empower-hr-beta.vercel.app` |
| **Concurrency Limit** | Single Uvicorn worker process | Serverless instance scaling (see persistence notes) |

---

## 16. Database Persistence & Demo Limitations

### 16.1 Current Storage Behavior on Vercel
On Vercel serverless functions, the root file system is **read-only**. The only writable location is the `/tmp` directory.
In the current Vercel backend deployment:
```
EMPOWERHR_DATA_DIR=/tmp/empowerhr
```
This configuration allows the application to create `database.db` and upload folders dynamically without crashing with read-only file system errors.

### 16.2 Ephemeral Nature of Serverless Storage
Because the backend runs on serverless container infrastructure:
1. **Container Recycling:** Serverless instances spin down when idle. When a new instance spins up, `/tmp` starts completely empty.
2. **Multiple Instances:** Concurrent requests may be routed to distinct container instances, each possessing an isolated, non-shared `/tmp` filesystem.
3. **Redeployments:** Every new git push or redeploy creates fresh instances with new `/tmp` directories.

### 16.3 Why This Is Acceptable for the Current Demo
For demonstration and evaluation purposes, this setup is functional:
- Setting `SEED_DEMO_DATA=true` ensures that whenever a container initializes an empty database, the default demo jobs ("Frontend Developer", "Backend Developer") are automatically recreated.
- Evaluators can test user registration, job creation, application submission, photo uploading, and CV downloading in real time within their session.

### 16.4 Requirements for Production Persistence (Future Work)
To transition EmpowerHR from a demo architecture to a long-term production deployment:
1. **Managed Relational Database:** Migrate from SQLite to a managed cloud database (e.g. PostgreSQL, Neon Database, or Supabase).
2. **Cloud Object Storage:** Migrate local file uploads (`uploads/` and `cv_uploads/`) to an S3-compatible object store (e.g. AWS S3, Cloudflare R2, or Supabase Storage) with pre-signed URLs for private CV downloads.
3. **Distributed Rate Limiting:** Replace the in-memory rate limiter dictionary with a Redis-backed token bucket or fixed-window limiter.

---

## 17. Testing

### 17.1 Test Framework & Execution
The backend test suite is built on **Pytest** and uses FastAPI's `TestClient` (backed by `httpx`).

To run the full test suite from the repository root:
```powershell
.venv\Scripts\pytest -v backend
```

### 17.2 Current Test Status
- **Total Tests:** 127
- **Passed:** 127
- **Failed:** 0
- **Execution Time:** ~20 seconds

### 17.3 Test Suite Breakdown

| Test File | Areas Covered |
|---|---|
| `test_admin_routes.py` | Admin authentication (`get_current_admin`), user listing, user activation/deactivation, job listing, global job moderation, protection against unauthorized roles. |
| `test_candidate_profile_cv.py` | Candidate profile update, CV upload validation, magic byte verification (.pdf, .doc, .docx), file size limits, private CV downloading by owning employers. |
| `test_employer_auth_dependencies.py`| Role verification (`get_current_employer`), job ownership verification (`get_owned_job`), rejection of candidate access to employer endpoints. |
| `test_employer_routes.py` | Employer registration, employer job CRUD, applicant listings, application status transitions, 409 conflict on deleting jobs with active applications. |
| `test_profile_auth.py` | User profile retrieval, full name and password updating, profile photo upload validation, authentication token verification. |
| `test_step12_security.py` | Fail-closed JWT secret configuration, rate limiting enforcement on auth endpoints, minimum password length (8 characters), security response headers. |
| `test_step13_deployment.py` | Gate for demo data seeding (`SEED_DEMO_DATA`), data directory resolution (`EMPOWERHR_DATA_DIR`), DB-free health check endpoint, dynamic CORS parsing. |

---

## 18. Troubleshooting

### 18.1 Frontend Displays "Unable to connect to the server"
- **Symptom:** Submitting a form or loading jobs shows the message: *"Unable to connect to the server. Please check your connection and try again."*
- **Likely Cause:** Network connectivity failure, backend server is offline, or `window.EMPOWERHR_API_BASE_URL` points to an incorrect or unreachable host.
- **What to Check:**
  1. Open browser Developer Tools (F12) → Network tab. Inspect the failed request.
  2. Test if the backend is reachable by navigating to `/health` (e.g. `https://backend-psi-neon-83.vercel.app/health` or `http://127.0.0.1:8000/health`).
- **Safe Fix:** If developing locally, ensure Uvicorn is running. Check that the `<script> window.EMPOWERHR_API_BASE_URL </script>` block in the HTML page matches your target backend.

### 18.2 CORS Errors in Browser Console
- **Symptom:** Browser console reports: `Access to fetch at ... has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.`
- **Likely Cause:** The origin where the frontend is served (e.g. `http://localhost:5500` or `https://empower-hr-beta.vercel.app`) is not listed in the backend's `ALLOWED_ORIGINS` setting.
- **What to Check:** Check the `ALLOWED_ORIGINS` environment variable on the backend.
- **Safe Fix:** In Vercel Project Settings for the backend, ensure `ALLOWED_ORIGINS` contains `https://empower-hr-beta.vercel.app` (without trailing slash). For local development, `_DEFAULT_ALLOWED_ORIGINS` in `main.py` already permits `127.0.0.1:5500`, `localhost:5500`, `127.0.0.1:3000`, and `localhost:3000`.

### 18.3 Deployed Frontend Points to Localhost
- **Symptom:** On the live deployed site (`empower-hr-beta.vercel.app`), API requests fail because the browser attempts to contact `http://127.0.0.1:8000`.
- **Likely Cause:** The HTML page is missing the `<script> window.EMPOWERHR_API_BASE_URL = 'https://...'; </script>` definition before loading JS modules, causing `api.js` to use its default fallback.
- **What to Check:** Inspect the `<head>` or bottom of the relevant `.html` file.
- **Safe Fix:** Ensure every HTML file in `frontend/` defines `window.EMPOWERHR_API_BASE_URL = 'https://backend-psi-neon-83.vercel.app';` prior to importing application scripts.

### 18.4 Vercel Serverless Function Fails with Read-Only Filesystem
- **Symptom:** Backend returns `HTTP 500` during startup or when writing to the database with `sqlite3.OperationalError: attempt to write a readonly database` or `OSError: [Errno 30] Read-only file system`.
- **Likely Cause:** `EMPOWERHR_DATA_DIR` is not set in Vercel, causing the backend to default to its install directory (which is read-only in AWS Lambda / Vercel).
- **Safe Fix:** Add the environment variable `EMPOWERHR_DATA_DIR=/tmp/empowerhr` in the Vercel backend project settings.

### 18.5 HTTP 429 Too Many Requests on Login or Registration
- **Symptom:** The user receives an alert: *"Too many requests. Please try again later."*
- **Likely Cause:** More than 5 requests were sent to `/login`, `/register`, or `/employer/register` from the same IP address within 60 seconds.
- **Safe Fix:** Wait 60 seconds for the in-memory fixed window counter to reset.

---

## 19. Security & Protection Controls

1. **Password Security:**
   - Hashed using the modern **Argon2** password hashing algorithm via `pwdlib`. Plaintext passwords are never stored, logged, or returned in API responses.
   - Enforces a minimum password length of **8 characters** on registration and profile password updates.

2. **Authentication Isolation:**
   - JWT claims use integer `sub` IDs.
   - Account roles (`candidate`, `employer`, `admin`) are **never trusted from client payloads or JWT claims**. Roles are verified fresh from the database on every authenticated request.

3. **Job & Application Ownership:**
   - Employers can only view, edit, or delete jobs they own (`job.employer_id == current_employer.id`).
   - Employers can only download CVs or update statuses for candidates who applied to their own jobs.
   - Deleting a job with active applications is blocked (`409 Conflict`) to prevent orphan records.

4. **Upload Hardening:**
   - Uploaded files are assigned cryptographically random UUID filenames (`uuid.uuid4().hex`), preventing path traversal and name collisions.
   - File extensions are validated against strict whitelists.
   - The file payload is validated against magic-byte signatures (preventing executable files disguised as images or documents).
   - Maximum upload sizes: 5 MB for profile photos, 10 MB for CV documents.
   - CVs are stored in an unmounted private directory and are only accessible through authenticated endpoints.

5. **Rate Limiting:**
   - Fixed-window in-memory rate limiter on authentication routes protects against automated credential stuffing and brute-force attacks.

6. **HTTP Response Headers:**
   - `X-Content-Type-Options: nosniff` prevents MIME-type sniffing.
   - `X-Frame-Options: DENY` prevents clickjacking attacks.
   - `Referrer-Policy: strict-origin-when-cross-origin` protects sensitive referrer metadata.

---

## 20. Project Team

*Project team members and academic affiliations:*

- **Ahmed Mahmoud Mohamed Ahmed**  
  - Ain Shams University  
  - Faculty of Al-Alsun  
  - **Role:** Team Leader, Project Manager, Project Idea Owner

- **Mahmoud Mohamed Mahmoud Abdelhamid**  
  - Benha University  
  - Graduate of Faculty of Computers and Artificial Intelligence  
  - **Role:** Project Implementation

- **Abdelrahman Ehab Ismail**  
  - Ain Shams University  
  - Faculty of Commerce  
  - **Role:** Project Prototypes and Application

- **Noura Rafiq Anwar**  
  - Ain Shams University  
  - Faculty of Education  
  - **Role:** Project Marketing and Research

---

## 21. Current Project Status

### 21.1 IMPLEMENTED
- Complete candidate authentication, job browsing, client-side live search, job details modal, and application submission.
- Candidate profile management, avatar photo upload (with byte validation), specialization and skills storage, and CV upload/delete (with format and magic-byte checks).
- Complete employer authentication, job posting, job editing, activation toggle, safe deletion, applicant inspection, candidate status updates, and secure CV downloading.
- Admin moderation API routes (`/admin/users`, `/admin/jobs`).
- Security controls: Argon2 hashing, fail-closed JWT configuration, in-memory rate limiting, security headers, file upload hardening.
- 127 automated backend regression tests.

### 21.2 DEPLOYED
- **Frontend:** Live on Vercel at [`https://empower-hr-beta.vercel.app`](https://empower-hr-beta.vercel.app).
- **Backend:** Live on Vercel Serverless at [`https://backend-psi-neon-83.vercel.app`](https://backend-psi-neon-83.vercel.app).
- End-to-end integration verified across public endpoints.

### 21.3 LIMITATIONS
- **Serverless SQLite Ephemerality:** Because the backend runs on Vercel serverless functions with storage in `/tmp/empowerhr`, data is not persistent across cold restarts or container recycling.
- **Admin UI:** Admin moderation exists exclusively as backend API endpoints; no administrative web UI currently exists.
- **Candidate Registration Fields:** The fields for `phone`, `city`, `birthDate`, and `accommodations` in `register.html` are labeled in the UI as under development and are not yet persisted in the database schema.
- **In-Memory Rate Limiting:** The rate limiter is scoped to single process memory and resets on serverless cold starts.

### 21.4 FUTURE WORK
- Migrate database to managed cloud PostgreSQL (e.g. Neon Database, Supabase, or AWS RDS).
- Migrate file storage to an S3-compatible cloud object store (e.g. AWS S3 or Cloudflare R2).
- Build a dedicated administrative frontend dashboard for user and job moderation.
- Persist additional candidate demographic and accessibility accommodation fields in the database schema.
- Implement distributed Redis-based rate limiting.

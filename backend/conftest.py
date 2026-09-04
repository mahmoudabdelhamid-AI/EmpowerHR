"""
STEP 12 pytest bootstrap.

- Sets JWT_SECRET_KEY for the test process only, since auth_utils.py now
  fails fast (RuntimeError) unless JWT_SECRET_KEY is set, or the explicit
  ENVIRONMENT=development + ALLOW_DEV_JWT_SECRET=true opt-in is used
  (STEP 12, H-1). This lets the existing test suite import
  auth_utils/routes unchanged, with no per-test setup required.
- Resets the STEP 12 (H-2) in-memory rate-limit counters before and
  after every test. Those counters live in a module-level dict in
  routes.py shared across the whole pytest session, and TestClient
  requests from different test files all appear to come from the same
  fake client IP. Without this reset, unrelated tests that call
  /login, /register, or /employer/register would accumulate a shared
  count across tests (rather than being scoped within a single test)
  and could spuriously trip the rate limit.
"""
import os

os.environ.setdefault("JWT_SECRET_KEY", "pytest-only-test-secret-key")

import pytest


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    import routes
    routes._rate_limit_buckets.clear()
    yield
    routes._rate_limit_buckets.clear()

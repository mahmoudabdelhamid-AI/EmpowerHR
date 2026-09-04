import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from main import app


@app.middleware("http")
async def strip_api_prefix(request, call_next):
    if request.scope["path"].startswith("/api"):
        request.scope["path"] = request.scope["path"][4:] or "/"
    return await call_next(request)
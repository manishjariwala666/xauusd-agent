"""Isolated Phase 1.5 admin-auth application for temporary staging only."""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from services.admin_auth_api import router as admin_auth_router


def _staging_enabled() -> bool:
    return os.getenv("ADMIN_STAGING_ONLY", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


app = FastAPI(
    title="VenusRealm Admin Authentication Staging",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.include_router(admin_auth_router)


@app.middleware("http")
async def staging_safety_gate(request: Request, call_next: Any) -> Response:
    """Fail closed unless this process is explicitly marked staging-only."""
    if not _staging_enabled():
        return JSONResponse(
            {"detail": "Admin staging service is disabled."},
            status_code=503,
            headers={
                "X-Robots-Tag": "noindex, nofollow, noarchive",
                "Cache-Control": "no-store",
            },
        )
    response = await call_next(request)
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "admin-auth-staging"}

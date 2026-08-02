"""Dependency-free liveness and dependency-aware search readiness."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.middleware import REQUEST_ID_HEADER, get_request_id
from app.core.config import settings
from app.core.metrics import ACTIVE_SCHEDULE, DATABASE_HEALTH, DATABASE_QUERY_DURATION
from app.core.observability import log_event
from app.db.redis import get_redis
from app.db.session import get_db
from app.services.schedule_import import get_active_schedule_status

router = APIRouter(tags=["health"])


def _dependency_status(db: Session) -> tuple[str, str, dict[str, object] | None]:
    database_started = time.perf_counter()
    try:
        db.execute(text("SELECT 1"))
        database_status = "ok"
        DATABASE_HEALTH.set(1)
        schedule = get_active_schedule_status(db)
    except Exception:
        database_status = "error"
        DATABASE_HEALTH.set(0)
        schedule = None
    finally:
        DATABASE_QUERY_DURATION.labels(operation="readiness").observe(
            time.perf_counter() - database_started
        )
    try:
        get_redis().ping()
        cache_status = "ok"
    except Exception:
        cache_status = "degraded"
    ACTIVE_SCHEDULE.set(1 if schedule else 0)
    return database_status, cache_status, schedule


@router.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok", "release": settings.app_release}


@router.get("/health/ready")
def ready(request: Request, db: Session = Depends(get_db)) -> JSONResponse:  # noqa: B008
    database_status, cache_status, schedule = _dependency_status(db)
    if database_status != "ok" or schedule is None:
        request_id = get_request_id(request)
        code = "DATABASE_UNAVAILABLE" if database_status != "ok" else "NO_ACTIVE_SCHEDULE"
        message = (
            "The database is unavailable."
            if database_status != "ok"
            else "No active schedule is available."
        )
        log_event(
            "health.degraded",
            request_id=request_id,
            error_code=code,
            failure_category="database" if database_status != "ok" else "schedule",
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            headers={REQUEST_ID_HEADER: request_id},
            content={
                "error": {
                    "code": code,
                    "message": message,
                    "details": {"database": database_status, "cache": cache_status},
                    "request_id": request_id,
                }
            },
        )
    return JSONResponse(
        content={
            "status": "ok" if cache_status == "ok" else "degraded",
            "database": database_status,
            "cache": cache_status,
            "schedule_version": schedule.get("version"),
            "release": settings.app_release,
        }
    )


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, object]:  # noqa: B008
    database_status, cache_status, schedule = _dependency_status(db)
    ready_status = database_status == "ok" and schedule is not None
    return {
        "status": "ok" if ready_status and cache_status == "ok" else "degraded",
        "database": database_status,
        "cache": cache_status,
        "schedule_version": schedule.get("version") if schedule else None,
        "release": settings.app_release,
    }

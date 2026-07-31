import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text

from app.core.config import settings
from app.db.redis import get_redis
from app.db.session import SessionLocal

router = APIRouter()
logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    status: str
    database: str
    cache: str
    schedule_version: str


@router.get("/live")
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health", response_model=HealthResponse, responses={503: {"model": HealthResponse}})
def health() -> JSONResponse:
    db = None
    database_status = "error"
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        database_status = "ok"
    except Exception:
        logger.warning("health check database dependency failed", exc_info=True)
    finally:
        if db is not None:
            db.close()

    try:
        get_redis().ping()
        cache_status = "ok"
    except Exception:
        logger.warning("health check cache dependency failed", exc_info=True)
        cache_status = "error"

    healthy = database_status == "ok" and cache_status == "ok"
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={
            "status": "ok" if healthy else "degraded",
            "database": database_status,
            "cache": cache_status,
            "schedule_version": settings.schedule_version,
        },
    )

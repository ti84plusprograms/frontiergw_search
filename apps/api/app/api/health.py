from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.redis import get_redis
from app.db.session import get_db

router = APIRouter()


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:  # noqa: B008
    try:
        db.execute(text("SELECT 1"))
        database_status = "ok"
    except Exception:
        database_status = "error"

    try:
        get_redis().ping()
        cache_status = "ok"
    except Exception:
        cache_status = "error"

    return {
        "status": "ok" if database_status == "ok" and cache_status == "ok" else "degraded",
        "database": database_status,
        "cache": cache_status,
        "schedule_version": settings.schedule_version,
    }

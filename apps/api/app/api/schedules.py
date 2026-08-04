"""API-003 — schedule-status endpoint.

Reports the same active schedule source the routing engine uses. When no active
schedule exists, returns a stable typed body (active=false), not a DB error.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import cast

from fastapi import APIRouter, Depends, Request
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.cache_keys import schedule_status_key
from app.core.config import settings
from app.db.session import get_db
from app.schemas.api_common import ERROR_RESPONSES
from app.schemas.schedule_status import ScheduleStatusResponse
from app.services.cache_service import get_cache_service
from app.services.rate_limit import enforce_rate_limit
from app.services.schedule_import import get_active_schedule_status

router = APIRouter(tags=["schedules"])


@router.get("/schedules/status", response_model=ScheduleStatusResponse, responses=ERROR_RESPONSES)
def get_schedule_status(
    request: Request,
    db: Session = Depends(get_db),  # noqa: B008
) -> ScheduleStatusResponse:
    cache = get_cache_service()
    enforce_rate_limit(
        request,
        endpoint="schedule_status",
        limit=settings.schedule_status_rate_limit_per_minute,
        cache=cache,
    )
    key = schedule_status_key(settings)
    cached = cache.get_json(key, namespace="schedule_status")
    if isinstance(cached.value, dict):
        try:
            return ScheduleStatusResponse.model_validate(cached.value)
        except ValidationError:
            cache.delete(key)
    status = get_active_schedule_status(db)
    if status is None:
        response = ScheduleStatusResponse(active=False)
    else:
        response = ScheduleStatusResponse(
            active=True,
            source=cast(str, status["source"]),
            version=cast(str, status["version"]),
            retrieved_at=cast("datetime | None", status["retrieved_at"]),
            effective_start=cast("date | None", status["effective_start"]),
            effective_end=cast("date | None", status["effective_end"]),
            route_count=cast(int, status["route_count"]),
            scheduled_flight_count=cast(int, status["scheduled_flight_count"]),
        )
    cache.set_json(
        key,
        response.model_dump(mode="json"),
        settings.schedule_status_cache_ttl_seconds,
    )
    return response

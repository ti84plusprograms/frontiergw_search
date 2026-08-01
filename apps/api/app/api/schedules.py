"""API-003 — schedule-status endpoint.

Reports the same active schedule source the routing engine uses. When no active
schedule exists, returns a stable typed body (active=false), not a DB error.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import cast

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.api_common import ERROR_RESPONSES
from app.schemas.schedule_status import ScheduleStatusResponse
from app.services.schedule_import import get_active_schedule_status

router = APIRouter(tags=["schedules"])


@router.get("/schedules/status", response_model=ScheduleStatusResponse, responses=ERROR_RESPONSES)
def get_schedule_status(db: Session = Depends(get_db)) -> ScheduleStatusResponse:  # noqa: B008
    status = get_active_schedule_status(db)
    if status is None:
        return ScheduleStatusResponse(active=False)
    return ScheduleStatusResponse(
        active=True,
        source=cast(str, status["source"]),
        version=cast(str, status["version"]),
        retrieved_at=cast("datetime | None", status["retrieved_at"]),
        effective_start=cast("date | None", status["effective_start"]),
        effective_end=cast("date | None", status["effective_end"]),
        route_count=cast(int, status["route_count"]),
        scheduled_flight_count=cast(int, status["scheduled_flight_count"]),
    )

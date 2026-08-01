"""Read-only schedule queries for the routing engine.

PHASE.md §Required Database and Repository Behavior: queries are scoped to the single
active data-source version, never mix inactive versions, and must not create N+1
patterns. Airport metadata (for timezones) is fetched in bulk per search, not per row.
All operations are read-only with respect to schedule data (§Read-Only Routing).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.airport import Airport
from app.db.models.data_source import DataSource
from app.db.models.scheduled_flight import ScheduledFlight


class ScheduleRepository:
    """Active-source-scoped read access to airports and scheduled flights."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._active_source_id: uuid.UUID | None = None
        self._resolved_active = False

    def active_source(self) -> DataSource | None:
        return self._db.scalar(select(DataSource).where(DataSource.is_active.is_(True)))

    def active_source_id(self) -> uuid.UUID | None:
        if not self._resolved_active:
            source = self.active_source()
            self._active_source_id = source.id if source is not None else None
            self._resolved_active = True
        return self._active_source_id

    def find_departures(self, origin: str, operating_date: date) -> list[ScheduledFlight]:
        """Scheduled flights departing ``origin`` applicable on ``operating_date``.

        Applicability by effective-date range and weekday is filtered in SQL where
        cheap; weekday membership against an array column is re-checked in the
        resolver (``operates_on``) to stay portable across Postgres arrays and the
        SQLite/JSON test fallback.
        """
        source_id = self.active_source_id()
        if source_id is None:
            return []
        stmt = (
            select(ScheduledFlight)
            .where(
                ScheduledFlight.data_source_id == source_id,
                ScheduledFlight.origin_code == origin,
                ScheduledFlight.effective_start <= operating_date,
                (ScheduledFlight.effective_end.is_(None))
                | (ScheduledFlight.effective_end >= operating_date),
            )
            .order_by(
                ScheduledFlight.departure_local_time,
                ScheduledFlight.flight_number,
                ScheduledFlight.id,
            )
        )
        return list(self._db.scalars(stmt).all())

    def find_departures_for_dates(
        self, origin: str, operating_dates: Iterable[date]
    ) -> list[tuple[ScheduledFlight, date]]:
        """(flight, candidate_date) pairs for each applicable date, one bulk query.

        Avoids N+1 by querying once over the min/max date span, then pairing in
        Python. The resolver applies the exact per-date effective/weekday check.
        """
        dates = sorted(set(operating_dates))
        if not dates:
            return []
        source_id = self.active_source_id()
        if source_id is None:
            return []
        span_start, span_end = dates[0], dates[-1]
        stmt = (
            select(ScheduledFlight)
            .where(
                ScheduledFlight.data_source_id == source_id,
                ScheduledFlight.origin_code == origin,
                ScheduledFlight.effective_start <= span_end,
                (ScheduledFlight.effective_end.is_(None))
                | (ScheduledFlight.effective_end >= span_start),
            )
            .order_by(
                ScheduledFlight.departure_local_time,
                ScheduledFlight.flight_number,
                ScheduledFlight.id,
            )
        )
        flights = list(self._db.scalars(stmt).all())
        return [(flight, d) for flight in flights for d in dates]

    def airports_by_code(self, codes: Iterable[str]) -> dict[str, Airport]:
        """Bulk-load airport metadata keyed by code (single query, no N+1)."""
        wanted = sorted(set(codes))
        if not wanted:
            return {}
        stmt = select(Airport).where(Airport.code.in_(wanted))
        return {airport.code: airport for airport in self._db.scalars(stmt).all()}

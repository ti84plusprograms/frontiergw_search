from datetime import date, datetime, time

from sqlalchemy import (
    ARRAY,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Time,
    func,
)
from sqlalchemy.schema import CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ScheduledFlight(Base):
    __tablename__ = "scheduled_flights"
    __table_args__ = (
        CheckConstraint(
            "arrival_day_offset >= 0 AND arrival_day_offset <= 2", name="valid_arrival_day_offset"
        ),
        CheckConstraint(
            "origin_code != destination_code",
            name="flights_no_self_loop",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    carrier_code: Mapped[str] = mapped_column(String(2))
    flight_number: Mapped[str] = mapped_column(String(10))
    origin_code: Mapped[str] = mapped_column(String(3), ForeignKey("airports.code"))
    destination_code: Mapped[str] = mapped_column(String(3), ForeignKey("airports.code"))
    departure_local_time: Mapped[time]
    arrival_local_time: Mapped[time]
    arrival_day_offset: Mapped[int]
    effective_start: Mapped[date]
    effective_end: Mapped[date | None] = mapped_column(nullable=True)
    operating_days: Mapped[list[int]] = mapped_column(ARRAY(Integer), default=list)
    equipment_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    data_source_id: Mapped[str] = mapped_column(ForeignKey("data_sources.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

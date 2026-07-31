import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    UUID,
    DateTime,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import CheckConstraint, UniqueConstraint

from app.db.base import Base
from app.db.types import OperatingDaysType


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
        CheckConstraint("effective_end IS NULL OR effective_end >= effective_start"),
        UniqueConstraint(
            "carrier_code",
            "flight_number",
            "origin_code",
            "destination_code",
            "effective_start",
            "data_source_id",
            name="uq_flights_source_identity",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    carrier_code: Mapped[str] = mapped_column(String(3))
    flight_number: Mapped[str] = mapped_column(String(8))
    origin_code: Mapped[str] = mapped_column(String(3), ForeignKey("airports.code"))
    destination_code: Mapped[str] = mapped_column(String(3), ForeignKey("airports.code"))
    departure_local_time: Mapped[time]
    arrival_local_time: Mapped[time]
    arrival_day_offset: Mapped[int]
    effective_start: Mapped[date]
    effective_end: Mapped[date | None] = mapped_column(nullable=True)
    operating_days: Mapped[list[int]] = mapped_column(OperatingDaysType(), default=list)
    equipment_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    data_source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_sources.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

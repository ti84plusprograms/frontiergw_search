import uuid
from datetime import date, datetime

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


class Route(Base):
    __tablename__ = "routes"
    __table_args__ = (
        CheckConstraint("operating_days != '{}'"),
        CheckConstraint("effective_end IS NULL OR effective_end >= effective_start"),
        CheckConstraint(
            "origin_code != destination_code",
            name="routes_no_self_loop",
        ),
        UniqueConstraint(
            "origin_code",
            "destination_code",
            "effective_start",
            "data_source_id",
            name="uq_routes_source_identity",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    origin_code: Mapped[str] = mapped_column(String(3), ForeignKey("airports.code"))
    destination_code: Mapped[str] = mapped_column(String(3), ForeignKey("airports.code"))
    effective_start: Mapped[date]
    effective_end: Mapped[date | None] = mapped_column(nullable=True)
    operating_days: Mapped[list[int]] = mapped_column(OperatingDaysType(), default=list)
    data_source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_sources.id"))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

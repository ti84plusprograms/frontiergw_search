from datetime import date, datetime

from sqlalchemy import (
    ARRAY,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.schema import CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Route(Base):
    __tablename__ = "routes"
    __table_args__ = (
        CheckConstraint("operating_days != '{}'"),
        CheckConstraint(
            "origin_code != destination_code",
            name="routes_no_self_loop",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    origin_code: Mapped[str] = mapped_column(String(3), ForeignKey("airports.code"))
    destination_code: Mapped[str] = mapped_column(String(3), ForeignKey("airports.code"))
    effective_start: Mapped[date]
    effective_end: Mapped[date | None] = mapped_column(nullable=True)
    operating_days: Mapped[list[int]] = mapped_column(ARRAY(Integer), default=list)
    data_source_id: Mapped[str] = mapped_column(ForeignKey("data_sources.id"))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

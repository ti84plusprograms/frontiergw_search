from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import CheckConstraint

from app.db.base import Base


class Airport(Base):
    __tablename__ = "airports"
    __table_args__ = (
        CheckConstraint("length(code) = 3"),
        CheckConstraint("length(country_code) = 2"),
        CheckConstraint("latitude >= -90 AND latitude <= 90"),
        CheckConstraint("longitude >= -180 AND longitude <= 180"),
    )

    code: Mapped[str] = mapped_column(String(3), primary_key=True)
    name: Mapped[str]
    city: Mapped[str]
    state_or_region: Mapped[str | None] = mapped_column(nullable=True)
    country_code: Mapped[str] = mapped_column(String(2))
    latitude: Mapped[float]
    longitude: Mapped[float]
    timezone: Mapped[str]
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

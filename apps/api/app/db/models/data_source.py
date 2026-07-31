import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    UUID,
    DateTime,
    Index,
    String,
    UniqueConstraint,
    func,
    literal_column,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DataSource(Base):
    __tablename__ = "data_sources"
    __table_args__ = (
        UniqueConstraint("name", "provider_type", "version", name="uq_data_sources_identity"),
        UniqueConstraint("checksum", name="uq_data_sources_checksum"),
        Index(
            "uq_data_sources_one_active",
            literal_column("(1)"),
            unique=True,
            postgresql_where=text("is_active IS TRUE"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str]
    provider_type: Mapped[str]
    version: Mapped[str]
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON, nullable=True
    )
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

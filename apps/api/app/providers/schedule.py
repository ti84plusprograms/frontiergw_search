from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Protocol

from app.schemas.schedule_import import ProviderRejectedRow, RawScheduleRecord


@dataclass
class ScheduleImportBatch:
    """Container for a batch of raw schedule records from a provider."""

    records: list[RawScheduleRecord]
    source_name: str
    source_version: str
    provider_type: str = "static_csv"
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    effective_start: date | None = None
    effective_end: date | None = None
    rejected_rows: list[ProviderRejectedRow] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    raw_source_checksum: str | None = None


class ScheduleProvider(Protocol):
    """Protocol for schedule data providers."""

    async def fetch_schedule(self, start_date: date, end_date: date) -> ScheduleImportBatch:
        """
        Fetch a batch of schedule records from the provider.

        Returns:
            ScheduleImportBatch: Raw records and metadata.
        """
        ...

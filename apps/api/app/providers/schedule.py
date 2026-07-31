from dataclasses import dataclass
from typing import Protocol

from app.schemas.schedule_import import RawScheduleRecord


@dataclass
class ScheduleImportBatch:
    """Container for a batch of raw schedule records from a provider."""

    records: list[RawScheduleRecord]
    source_name: str
    source_version: str


class ScheduleProvider(Protocol):
    """Protocol for schedule data providers."""

    def fetch_schedule(self) -> ScheduleImportBatch:
        """
        Fetch a batch of schedule records from the provider.

        Returns:
            ScheduleImportBatch: Raw records and metadata.
        """
        ...

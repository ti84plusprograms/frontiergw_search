from datetime import date, datetime, time
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class RawScheduleRecord(BaseModel):
    """Provider-facing schedule record (raw CSV/JSON fields)."""

    carrier_code: str
    flight_number: str
    origin_code: str
    destination_code: str
    departure_local_time: str
    arrival_local_time: str
    arrival_day_offset: int
    effective_start: str
    effective_end: str | None
    operating_days: str
    equipment_code: str | None = None


class NormalizedFlightRecord(BaseModel):
    """Internal schedule record after normalization."""

    carrier_code: str
    flight_number: str
    origin_code: str
    destination_code: str
    departure_local_time: time
    arrival_local_time: time
    arrival_day_offset: int
    effective_start: date
    effective_end: date | None
    operating_days: list[int]
    equipment_code: str | None = None


class ProviderRejectedRow(BaseModel):
    row_number: int
    raw_record: dict[str, Any]
    reason: str


class QuarantinedRecord(BaseModel):
    """Record that failed validation."""

    raw_record: RawScheduleRecord | dict[str, Any]
    reason: str


class ImportResult(BaseModel):
    """Result of a schedule import attempt."""

    import_id: UUID = Field(default_factory=uuid4)
    source_id: UUID | None = Field(
        None, description="UUID of created data_source, or None if import failed"
    )
    version: str | None = Field(None, description="Version identifier (checksum or timestamp)")
    total_count: int = Field(default=0)
    accepted_count: int = Field(default=0, description="Number of successfully imported records")
    rejected_count: int = Field(default=0, description="Number of rejected records")
    duplicate_count: int = Field(default=0)
    unique_airport_count: int = Field(default=0)
    unique_route_count: int = Field(default=0)
    unique_scheduled_flight_count: int = Field(default=0)
    rejected_reasons: list[dict[str, Any]] = Field(
        default_factory=list, description="List of rejection reasons with counts"
    )
    success: bool = Field(default=False, description="Whether the import succeeded")
    error_message: str | None = Field(None, description="High-level error message if import failed")
    error_code: str | None = None
    activation_result: str = "not_attempted"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float | None = None

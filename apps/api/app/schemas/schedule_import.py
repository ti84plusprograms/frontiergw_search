from datetime import date, time
from typing import Any

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


class QuarantinedRecord(BaseModel):
    """Record that failed validation."""

    raw_record: RawScheduleRecord | dict[str, Any]
    reason: str


class ImportResult(BaseModel):
    """Result of a schedule import attempt."""

    source_id: str | None = Field(
        None, description="UUID of created data_source, or None if import failed"
    )
    version: str | None = Field(None, description="Version identifier (checksum or timestamp)")
    accepted_count: int = Field(default=0, description="Number of successfully imported records")
    rejected_count: int = Field(default=0, description="Number of rejected records")
    rejected_reasons: list[dict[str, Any]] = Field(
        default_factory=list, description="List of rejection reasons with counts"
    )
    success: bool = Field(default=False, description="Whether the import succeeded")
    error_message: str | None = Field(None, description="High-level error message if import failed")

import hashlib
import json
from datetime import date, datetime, time, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.db import DataSource, Route, ScheduledFlight
from app.providers.schedule import ScheduleImportBatch, ScheduleProvider
from app.schemas.schedule_import import ImportResult, NormalizedFlightRecord
from app.services.normalization import normalize_flight_record
from app.services.schedule_quality import (
    BatchQualityStats,
    ValidationError,
    check_batch_quality,
    validate_flight_record,
)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Provider timestamps must be timezone-aware")
    return value


def _canonical_checksum(records: list[NormalizedFlightRecord]) -> str:
    payload = [
        {
            "arrival_day_offset": record.arrival_day_offset,
            "arrival_local_time": record.arrival_local_time.isoformat(),
            "carrier_code": record.carrier_code,
            "destination_code": record.destination_code,
            "departure_local_time": record.departure_local_time.isoformat(),
            "effective_end": record.effective_end.isoformat() if record.effective_end else None,
            "effective_start": record.effective_start.isoformat(),
            "equipment_code": record.equipment_code,
            "flight_number": record.flight_number,
            "operating_days": record.operating_days,
            "origin_code": record.origin_code,
        }
        for record in records
    ]
    canonical = json.dumps(
        sorted(payload, key=lambda item: json.dumps(item, sort_keys=True)), sort_keys=True
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _effective_timestamp(batch: ScheduleImportBatch) -> datetime:
    if batch.effective_start is None:
        return _aware(batch.retrieved_at)
    return datetime.combine(batch.effective_start, time.min, tzinfo=timezone.utc)


class ScheduleImportService:
    """Validate and atomically activate provider-neutral schedule datasets."""

    @staticmethod
    async def import_schedule(
        provider: ScheduleProvider,
        db: Session,
        *,
        start_date: date = date.min,
        end_date: date = date.max,
        activate: bool = True,
    ) -> ImportResult:
        result = ImportResult(started_at=datetime.now(timezone.utc))

        try:
            batch = await provider.fetch_schedule(start_date, end_date)
            result.total_count = len(batch.records) + len(batch.rejected_rows)
            result.rejected_count = len(batch.rejected_rows)
            result.rejected_reasons = [
                {
                    "row_number": row.row_number,
                    "raw_record": row.raw_record,
                    "reason": row.reason,
                }
                for row in batch.rejected_rows
            ]

            normalized: list[NormalizedFlightRecord] = []
            for raw_record in batch.records:
                try:
                    normalized_record = normalize_flight_record(raw_record)
                    normalized.append(normalized_record)
                except (TypeError, ValueError) as exc:
                    result.rejected_count += 1
                    result.rejected_reasons.append(
                        {"flight_number": raw_record.flight_number, "reason": str(exc)}
                    )

            if not normalized:
                result.error_code = "no_valid_records"
                result.error_message = "No records passed normalization"
                return result

            # This is the service-owned transaction boundary. Callers must pass a clean Session.
            with db.begin():
                accepted: list[NormalizedFlightRecord] = []
                for record in normalized:
                    try:
                        validate_flight_record(record, db)
                        accepted.append(record)
                    except ValidationError as exc:
                        result.rejected_count += 1
                        result.rejected_reasons.append(
                            {"flight_number": record.flight_number, "reason": str(exc)}
                        )

                if not accepted:
                    result.error_code = "no_valid_records"
                    result.error_message = "No records passed validation"
                    return result

                try:
                    quality: BatchQualityStats = check_batch_quality(accepted)
                except ValidationError as exc:
                    result.error_code = "quality_gate_failed"
                    result.error_message = str(exc)
                    return result

                result.accepted_count = len(quality.records)
                result.duplicate_count = quality.duplicate_count
                result.unique_airport_count = quality.unique_airport_count
                result.unique_route_count = quality.unique_route_count
                result.unique_scheduled_flight_count = quality.unique_scheduled_flight_count
                checksum = _canonical_checksum(quality.records)

                if not activate:
                    result.success = True
                    result.activation_result = "validated"
                    return result

                existing_by_version = db.scalar(
                    select(DataSource).where(
                        DataSource.name == batch.source_name,
                        DataSource.provider_type == batch.provider_type,
                        DataSource.version == batch.source_version,
                    )
                )
                existing_by_checksum = db.scalar(
                    select(DataSource).where(DataSource.checksum == checksum)
                )
                if existing_by_version is not None or existing_by_checksum is not None:
                    existing = existing_by_version or existing_by_checksum
                    if existing is not None and existing.checksum == checksum:
                        result.source_id = existing.id
                        result.version = existing.version
                        result.success = True
                        result.activation_result = "no_op_duplicate"
                        return result
                    result.error_code = "duplicate_source_version"
                    result.error_message = (
                        "The source version already exists with different schedule content"
                    )
                    return result

                new_source = DataSource(
                    name=batch.source_name,
                    provider_type=batch.provider_type,
                    version=batch.source_version,
                    retrieved_at=_aware(batch.retrieved_at),
                    effective_at=_effective_timestamp(batch),
                    provider_metadata={
                        "import_id": str(result.import_id),
                        "warnings": batch.warnings,
                        "raw_source_checksum": batch.raw_source_checksum,
                        "requested_start_date": start_date.isoformat(),
                        "requested_end_date": end_date.isoformat(),
                    },
                    checksum=checksum,
                    is_active=False,
                )
                db.add(new_source)
                db.flush()

                db.add_all(
                    [
                        ScheduledFlight(
                            carrier_code=record.carrier_code,
                            flight_number=record.flight_number,
                            origin_code=record.origin_code,
                            destination_code=record.destination_code,
                            departure_local_time=record.departure_local_time,
                            arrival_local_time=record.arrival_local_time,
                            arrival_day_offset=record.arrival_day_offset,
                            effective_start=record.effective_start,
                            effective_end=record.effective_end,
                            operating_days=record.operating_days,
                            equipment_code=record.equipment_code,
                            data_source_id=new_source.id,
                        )
                        for record in quality.records
                    ]
                )

                route_keys: set[tuple[Any, ...]] = set()
                routes: list[Route] = []
                for record in quality.records:
                    key = (
                        record.origin_code,
                        record.destination_code,
                        record.effective_start,
                    )
                    if key in route_keys:
                        continue
                    route_keys.add(key)
                    routes.append(
                        Route(
                            origin_code=record.origin_code,
                            destination_code=record.destination_code,
                            effective_start=record.effective_start,
                            effective_end=record.effective_end,
                            operating_days=record.operating_days,
                            data_source_id=new_source.id,
                        )
                    )
                db.add_all(routes)

                result.source_id = new_source.id
                result.version = new_source.version
                active_sources = list(
                    db.scalars(
                        select(DataSource).where(DataSource.is_active.is_(True)).with_for_update()
                    )
                )
                active_ids = [source.id for source in active_sources]
                if active_ids:
                    db.execute(
                        update(Route)
                        .where(Route.data_source_id.in_(active_ids))
                        .values(is_active=False)
                    )
                    for source in active_sources:
                        source.is_active = False
                new_source.is_active = True

                result.success = True
                result.activation_result = "activated"
        # Database and provider failures are reported rather than swallowed silently.
        except Exception as exc:
            db.rollback()
            result.error_code = result.error_code or "import_failed"
            result.error_message = str(exc)
            result.activation_result = "failed"
        finally:
            result.completed_at = datetime.now(timezone.utc)
            if result.started_at is not None:
                result.duration_seconds = (result.completed_at - result.started_at).total_seconds()

        return result


def get_active_schedule_status(db: Session) -> dict[str, Any] | None:
    source = db.scalar(select(DataSource).where(DataSource.is_active.is_(True)))
    if source is None:
        return None
    route_count = db.scalar(
        select(func.count()).select_from(Route).where(Route.data_source_id == source.id)
    )
    flight_count = db.scalar(
        select(func.count())
        .select_from(ScheduledFlight)
        .where(ScheduledFlight.data_source_id == source.id)
    )
    effective_start = db.scalar(
        select(func.min(ScheduledFlight.effective_start)).where(
            ScheduledFlight.data_source_id == source.id
        )
    )
    open_ended_count = db.scalar(
        select(func.count())
        .select_from(ScheduledFlight)
        .where(
            ScheduledFlight.data_source_id == source.id,
            ScheduledFlight.effective_end.is_(None),
        )
    )
    effective_end = db.scalar(
        select(func.max(ScheduledFlight.effective_end)).where(
            ScheduledFlight.data_source_id == source.id
        )
    )
    return {
        "source": source.name,
        "version": source.version,
        "retrieved_at": source.retrieved_at,
        "effective_start": effective_start,
        "effective_end": None if open_ended_count else effective_end,
        "route_count": route_count or 0,
        "scheduled_flight_count": flight_count or 0,
    }

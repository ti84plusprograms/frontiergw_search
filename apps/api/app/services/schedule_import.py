import hashlib
from datetime import datetime

from sqlalchemy.orm import Session

from app.db import DataSource, Route, ScheduledFlight
from app.providers.schedule import ScheduleProvider
from app.schemas.schedule_import import ImportResult, NormalizedFlightRecord
from app.services.normalization import normalize_flight_record
from app.services.schedule_quality import (
    ValidationError,
    check_batch_quality,
    validate_flight_record,
)


class ScheduleImportService:
    """Service for importing schedule data through providers."""

    @staticmethod
    def import_schedule(provider: ScheduleProvider, db: Session) -> ImportResult:
        """
        Import schedule data through a provider with atomic activation.

        Pipeline (TDD §30.1–30.2):
        1. Fetch raw batch from provider
        2. Normalize each record (collect parse failures as quarantined)
        3. Validate each against row rules (split to accepted/rejected)
        4. Run batch quality checks (fail entire import if any fail)
        5. BEGIN TRANSACTION
        6. Create new data_source row
        7. Bulk-insert flights and derived routes
        8. Mark prior active data_sources inactive
        9. COMMIT

        Args:
            provider: ScheduleProvider instance
            db: SQLAlchemy session

        Returns:
            ImportResult with counts, source_id, and success status

        Raises:
            None — all errors are captured in ImportResult
        """
        result = ImportResult()

        try:
            # Step 1: Fetch raw batch
            batch = provider.fetch_schedule()

            # Step 2–3: Normalize and validate
            accepted: list[NormalizedFlightRecord] = []
            rejected_reasons: list[tuple[str, str]] = []

            for raw_record in batch.records:
                try:
                    normalized = normalize_flight_record(raw_record)
                    try:
                        validate_flight_record(normalized, db)
                        accepted.append(normalized)
                    except ValidationError as e:
                        rejected_reasons.append((raw_record.flight_number, str(e)))
                except (ValueError, ValidationError) as e:
                    rejected_reasons.append((raw_record.flight_number, str(e)))

            result.accepted_count = len(accepted)
            result.rejected_count = len(rejected_reasons)
            if rejected_reasons:
                result.rejected_reasons = [
                    {"flight_number": fn, "reason": reason} for fn, reason in rejected_reasons
                ]

            # Step 4: Batch quality checks (before any DB writes)
            try:
                check_batch_quality(accepted)
            except ValidationError as e:
                result.error_message = f"Batch quality check failed: {e}"
                return result

            if not accepted:
                result.error_message = "No records passed validation"
                return result

            # Step 5–9: Atomic activation
            try:
                # Compute checksum for idempotency detection
                checksum = hashlib.sha256(
                    "".join(
                        f"{r.carrier_code}{r.flight_number}{r.origin_code}{r.destination_code}"
                        for r in accepted
                    ).encode()
                ).hexdigest()

                version = datetime.utcnow().isoformat()

                # Create new data source
                new_source = DataSource(
                    name=batch.source_name,
                    provider_type="static_csv",
                    version=version,
                    retrieved_at=datetime.utcnow(),
                    effective_at=datetime.utcnow(),
                    checksum=checksum,
                    is_active=True,
                )
                db.add(new_source)
                db.flush()  # Get the ID without committing
                source_id = str(new_source.id)

                # Bulk-insert flights
                flights = [
                    ScheduledFlight(
                        carrier_code=r.carrier_code,
                        flight_number=r.flight_number,
                        origin_code=r.origin_code,
                        destination_code=r.destination_code,
                        departure_local_time=r.departure_local_time,
                        arrival_local_time=r.arrival_local_time,
                        arrival_day_offset=r.arrival_day_offset,
                        effective_start=r.effective_start,
                        effective_end=r.effective_end,
                        operating_days=r.operating_days,
                        equipment_code=r.equipment_code,
                        data_source_id=new_source.id,
                    )
                    for r in accepted
                ]
                db.add_all(flights)

                # Derive and insert unique routes (deduplicated by origin/destination/dates/days)
                route_key_set = set()
                routes_to_insert = []
                for r in accepted:
                    key = (
                        r.origin_code,
                        r.destination_code,
                        r.effective_start,
                        r.effective_end,
                        tuple(r.operating_days),
                    )
                    if key not in route_key_set:
                        route_key_set.add(key)
                        routes_to_insert.append(
                            Route(
                                origin_code=r.origin_code,
                                destination_code=r.destination_code,
                                effective_start=r.effective_start,
                                effective_end=r.effective_end,
                                operating_days=r.operating_days,
                                data_source_id=new_source.id,
                            )
                        )
                db.add_all(routes_to_insert)

                # Mark prior active sources for same provider_type as inactive
                prior_sources = (
                    db.query(DataSource)
                    .filter_by(provider_type="static_csv", is_active=True)
                    .filter(DataSource.id != new_source.id)
                    .all()
                )
                for src in prior_sources:
                    src.is_active = False

                # Commit atomically
                db.commit()

                result.source_id = source_id
                result.version = version
                result.success = True

            except Exception as e:
                db.rollback()
                result.error_message = f"Database operation failed: {e}"
                return result

        except Exception as e:
            result.error_message = f"Import failed: {e}"
            return result

        return result

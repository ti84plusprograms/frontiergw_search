import asyncio
from datetime import date, datetime, time, timezone
from pathlib import Path

import pytest

from app.db import DataSource
from app.providers.schedule import ScheduleImportBatch
from app.providers.static_csv import StaticCsvScheduleProvider
from app.schemas.schedule_import import NormalizedFlightRecord
from app.services.airport_import import AirportSeedImporter
from app.services.schedule_import import ScheduleImportService, get_active_schedule_status
from app.services.schedule_quality import ValidationError, check_batch_quality


class FixtureProvider:
    def __init__(self, records, version="fixture-v1", source_name="fixture"):
        self.records = records
        self.version = version
        self.source_name = source_name
        self.calls = []

    async def fetch_schedule(self, start_date, end_date):
        self.calls.append((start_date, end_date))
        await asyncio.sleep(0)
        return ScheduleImportBatch(
            records=self.records,
            source_name=self.source_name,
            source_version=self.version,
            retrieved_at=datetime.now(timezone.utc),
            effective_start=date(2026, 8, 1),
            effective_end=date(2026, 12, 31),
        )


def _seed_airports(db_session):
    AirportSeedImporter.import_csv(
        Path(__file__).parent.parent / "data" / "fixtures" / "sample_airports.csv", db_session
    )


def test_valid_import_is_atomic_and_reimport_is_noop(db_session):
    _seed_airports(db_session)
    provider = StaticCsvScheduleProvider(
        Path(__file__).parent.parent / "data" / "fixtures" / "sample_schedule.csv"
    )

    first = asyncio.run(
        ScheduleImportService.import_schedule(
            provider,
            db_session,
            start_date=date(2026, 8, 1),
            end_date=date(2026, 12, 31),
        )
    )
    second = asyncio.run(
        ScheduleImportService.import_schedule(
            provider,
            db_session,
            start_date=date(2026, 8, 1),
            end_date=date(2026, 12, 31),
        )
    )

    assert first.success is True
    assert first.activation_result == "activated"
    assert first.accepted_count == 12
    assert first.source_id is not None
    assert first.started_at.tzinfo is not None
    assert second.success is True
    assert second.activation_result == "no_op_duplicate"
    assert db_session.query(DataSource).count() == 1
    status = get_active_schedule_status(db_session)
    assert status["effective_start"] == date(2026, 8, 1)
    assert status["effective_end"] == date(2026, 12, 31)
    assert status["route_count"] == 12
    assert status["scheduled_flight_count"] == 12


@pytest.mark.asyncio
async def test_async_provider_is_awaited_through_atomic_activation(db_session):
    _seed_airports(db_session)
    csv_provider = StaticCsvScheduleProvider(
        Path(__file__).parent.parent / "data" / "fixtures" / "sample_schedule.csv"
    )
    batch = await csv_provider.fetch_schedule(date(2026, 8, 1), date(2026, 12, 31))
    provider = FixtureProvider(batch.records, version="async-v1")

    result = await ScheduleImportService.import_schedule(
        provider,
        db_session,
        start_date=date(2026, 8, 1),
        end_date=date(2026, 12, 31),
    )

    assert provider.calls == [(date(2026, 8, 1), date(2026, 12, 31))]
    assert result.success is True
    assert result.activation_result == "activated"
    assert result.completed_at is not None
    assert result.completed_at.tzinfo is not None
    assert db_session.query(DataSource).count() == 1
    status = get_active_schedule_status(db_session)
    assert status is not None
    assert status["version"] == "async-v1"
    assert status["scheduled_flight_count"] == 12


@pytest.mark.asyncio
async def test_checksum_dedup_is_order_independent_for_async_imports(db_session):
    _seed_airports(db_session)
    csv_provider = StaticCsvScheduleProvider(
        Path(__file__).parent.parent / "data" / "fixtures" / "sample_schedule.csv"
    )
    batch = await csv_provider.fetch_schedule(date.min, date.max)
    first_provider = FixtureProvider(batch.records, version="checksum-v1")
    reordered_provider = FixtureProvider(list(reversed(batch.records)), version="checksum-v2")

    first = await ScheduleImportService.import_schedule(first_provider, db_session)
    duplicate = await ScheduleImportService.import_schedule(reordered_provider, db_session)

    assert first.success is True
    assert duplicate.success is True
    assert duplicate.activation_result == "no_op_duplicate"
    assert duplicate.source_id == first.source_id
    assert duplicate.version == first.version
    assert db_session.query(DataSource).count() == 1
    assert get_active_schedule_status(db_session)["version"] == "checksum-v1"


@pytest.mark.asyncio
async def test_contradictory_duplicate_rejects_batch_without_partial_activation(db_session):
    _seed_airports(db_session)
    csv_provider = StaticCsvScheduleProvider(
        Path(__file__).parent.parent / "data" / "fixtures" / "sample_schedule.csv"
    )
    batch = await csv_provider.fetch_schedule(date.min, date.max)
    first_provider = FixtureProvider(batch.records, version="baseline-v1")
    contradictory_records = [
        record.model_copy(update={"arrival_local_time": "09:00"}) if index == 0 else record
        for index, record in enumerate(batch.records)
    ]
    contradictory_records.append(batch.records[0])
    contradictory_provider = FixtureProvider(
        contradictory_records,
        version="contradictory-v1",
    )

    first = await ScheduleImportService.import_schedule(first_provider, db_session)
    failed = await ScheduleImportService.import_schedule(contradictory_provider, db_session)

    assert first.success is True
    assert failed.success is False
    assert failed.error_code == "quality_gate_failed"
    assert failed.error_message is not None
    assert "Contradictory duplicate" in failed.error_message
    assert db_session.query(DataSource).count() == 1
    status = get_active_schedule_status(db_session)
    assert status is not None
    assert status["version"] == "baseline-v1"
    assert status["scheduled_flight_count"] == 12


def test_source_version_collision_does_not_replace_active_dataset(db_session):
    _seed_airports(db_session)
    provider = StaticCsvScheduleProvider(
        Path(__file__).parent.parent / "data" / "fixtures" / "sample_schedule.csv"
    )
    first = asyncio.run(ScheduleImportService.import_schedule(provider, db_session))

    records = asyncio.run(provider.fetch_schedule(date.min, date.max)).records
    records[0] = records[0].model_copy(update={"arrival_local_time": "09:00"})
    collision = asyncio.run(
        ScheduleImportService.import_schedule(
            FixtureProvider(records, "sample_schedule.csv", source_name="static_csv"), db_session
        )
    )

    assert first.success is True
    assert collision.success is False
    assert collision.error_code == "duplicate_source_version"
    status = get_active_schedule_status(db_session)
    assert status["version"] == first.version


def test_validation_failure_leaves_previous_active_dataset_unchanged(db_session):
    _seed_airports(db_session)
    provider = StaticCsvScheduleProvider(
        Path(__file__).parent.parent / "data" / "fixtures" / "sample_schedule.csv"
    )
    first = asyncio.run(ScheduleImportService.import_schedule(provider, db_session))
    records = asyncio.run(provider.fetch_schedule(date.min, date.max)).records
    records = [record.model_copy(update={"origin_code": "XXX"}) for record in records]
    failed = asyncio.run(
        ScheduleImportService.import_schedule(FixtureProvider(records, "invalid-v1"), db_session)
    )

    assert first.success is True
    assert failed.success is False
    assert failed.error_code == "no_valid_records"
    assert get_active_schedule_status(db_session)["version"] == first.version


@pytest.mark.asyncio
async def test_activation_failure_rolls_back_new_source(db_session, monkeypatch):
    _seed_airports(db_session)
    provider = StaticCsvScheduleProvider(
        Path(__file__).parent.parent / "data" / "fixtures" / "sample_schedule.csv"
    )
    first = await ScheduleImportService.import_schedule(provider, db_session)

    def fail_flush(*args, **kwargs):
        raise RuntimeError("simulated activation failure")

    monkeypatch.setattr(db_session, "flush", fail_flush)
    batch = await provider.fetch_schedule(date.min, date.max)
    failed = await ScheduleImportService.import_schedule(
        FixtureProvider(batch.records, version="v2"),
        db_session,
    )

    assert first.success is True
    assert failed.success is False
    assert failed.activation_result == "failed"
    monkeypatch.undo()
    status = get_active_schedule_status(db_session)
    assert status is not None
    assert status["version"] == first.version
    assert status["scheduled_flight_count"] == first.accepted_count
    assert db_session.query(DataSource).count() == 1


def _record(number: str, departure: time = time(6, 0)) -> NormalizedFlightRecord:
    return NormalizedFlightRecord(
        carrier_code="F9",
        flight_number=number,
        origin_code="ATL",
        destination_code="DEN",
        departure_local_time=departure,
        arrival_local_time=time(8, 0),
        arrival_day_offset=0,
        effective_start=date(2026, 8, 1),
        effective_end=date(2026, 12, 31),
        operating_days=[1, 2, 3],
    )


def test_duplicate_records_are_deduplicated_and_contradictions_rejected():
    records = [_record(str(number)) for number in range(20)]
    stats = check_batch_quality(records + [records[0]])

    assert stats.duplicate_count == 1
    assert len(stats.records) == 20

    with pytest.raises(ValidationError, match="Contradictory duplicate"):
        check_batch_quality(records + [_record("0", time(7, 0))])

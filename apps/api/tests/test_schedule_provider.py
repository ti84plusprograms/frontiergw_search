"""Test schedule provider implementations."""

import asyncio
from datetime import date
from pathlib import Path

import pytest

from app.providers.static_csv import StaticCsvScheduleProvider


def test_static_csv_provider_reads_fixture():
    """Test that StaticCsvScheduleProvider can read the sample fixture."""
    fixture_path = Path(__file__).parent.parent / "data" / "fixtures" / "sample_schedule.csv"
    provider = StaticCsvScheduleProvider(fixture_path)

    batch = asyncio.run(provider.fetch_schedule(date.min, date.max))

    assert batch.source_name == "static_csv"
    assert batch.source_version == "sample_schedule.csv"
    assert len(batch.records) == 12  # 12 flights in the fixture
    assert all(r.carrier_code == "F9" for r in batch.records)
    assert batch.records[0].flight_number == "100"
    assert batch.records[0].origin_code == "ATL"
    assert batch.records[0].destination_code == "DEN"


def test_static_csv_provider_normalizes_codes():
    """Test that airport codes are uppercased."""
    fixture_path = Path(__file__).parent.parent / "data" / "fixtures" / "sample_schedule.csv"
    provider = StaticCsvScheduleProvider(fixture_path)

    batch = asyncio.run(provider.fetch_schedule(date.min, date.max))

    # All codes should be uppercase (they are in the fixture)
    for record in batch.records:
        assert record.origin_code.isupper()
        assert record.destination_code.isupper()
        assert len(record.origin_code) == 3
        assert len(record.destination_code) == 3


def test_static_csv_provider_file_not_found():
    """Test that provider raises FileNotFoundError for missing file."""
    provider = StaticCsvScheduleProvider("/nonexistent/file.csv")

    with pytest.raises(FileNotFoundError):
        asyncio.run(provider.fetch_schedule(date.min, date.max))

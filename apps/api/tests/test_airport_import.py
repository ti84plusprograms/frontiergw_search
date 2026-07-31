from pathlib import Path

import pytest

from app.db import Airport
from app.schemas.airport_import import AirportRecord
from app.services.airport_import import (
    AirportSeedImporter,
    AirportValidationError,
    validate_airport_record,
)


def test_airport_seed_import_is_idempotent(db_session):
    fixture = Path(__file__).parent.parent / "data" / "fixtures" / "sample_airports.csv"

    first = AirportSeedImporter.import_csv(fixture, db_session)
    second = AirportSeedImporter.import_csv(fixture, db_session)

    assert first.inserted_count == 6
    assert first.rejected_count == 0
    assert second.inserted_count == 0
    assert second.updated_count == 0
    assert second.skipped_count == 6
    assert db_session.query(Airport).count() == 6


def test_invalid_airport_data_is_rejected():
    with pytest.raises(AirportValidationError, match="three uppercase"):
        validate_airport_record(
            AirportRecord(
                code="ATL1",
                name="Atlanta",
                city="Atlanta",
                country_code="US",
                latitude=33.6,
                longitude=-84.4,
                timezone="America/New_York",
            )
        )

    with pytest.raises(AirportValidationError, match="IANA timezone"):
        validate_airport_record(
            AirportRecord(
                code="ATL",
                name="Atlanta",
                city="Atlanta",
                country_code="US",
                latitude=33.6,
                longitude=-84.4,
                timezone="Not/A_Timezone",
            )
        )


def test_airport_seed_import_reports_rejected_rows(db_session, tmp_path):
    path = tmp_path / "airports.csv"
    path.write_text(
        "code,name,city,state_or_region,country_code,latitude,longitude,timezone\n"
        "ATL,Atlanta,Atlanta,Georgia,US,33.6,-84.4,America/New_York\n"
        "BAD1,Invalid,Invalid,State,US,0,0,America/New_York\n"
    )

    result = AirportSeedImporter.import_csv(path, db_session)

    assert result.inserted_count == 1
    assert result.rejected_count == 1
    assert result.rejected_reasons[0]["row_number"] == 3

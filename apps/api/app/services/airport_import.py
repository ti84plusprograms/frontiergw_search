import csv
import re
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.db import Airport
from app.schemas.airport_import import AirportImportResult, AirportRecord


class AirportValidationError(ValueError):
    pass


def validate_airport_record(record: AirportRecord) -> AirportRecord:
    code = record.code.upper()
    country_code = record.country_code.upper()
    if not re.fullmatch(r"[A-Z]{3}", code):
        raise AirportValidationError("Airport code must be exactly three uppercase letters")
    if not re.fullmatch(r"[A-Z]{2}", country_code):
        raise AirportValidationError("Country code must be exactly two uppercase letters")
    if not -90 <= record.latitude <= 90:
        raise AirportValidationError("Latitude must be between -90 and 90")
    if not -180 <= record.longitude <= 180:
        raise AirportValidationError("Longitude must be between -180 and 180")
    try:
        ZoneInfo(record.timezone)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise AirportValidationError(f"Invalid IANA timezone: {record.timezone}") from exc
    if not record.name or not record.city:
        raise AirportValidationError("Airport name and city are required")
    return record.model_copy(update={"code": code, "country_code": country_code})


class AirportSeedImporter:
    @staticmethod
    def import_csv(path: str | Path, db: Session) -> AirportImportResult:
        result = AirportImportResult()
        seen: dict[str, AirportRecord] = {}
        parsed: list[tuple[int, AirportRecord]] = []

        with Path(path).open(newline="") as handle:
            reader = csv.DictReader(handle)
            required = {
                "code",
                "name",
                "city",
                "state_or_region",
                "country_code",
                "latitude",
                "longitude",
                "timezone",
            }
            if not reader.fieldnames or required - set(reader.fieldnames):
                missing = sorted(required - set(reader.fieldnames or []))
                raise AirportValidationError(f"Missing required airport columns: {missing}")

            for row_number, row in enumerate(reader, start=2):
                try:
                    record = validate_airport_record(
                        AirportRecord(
                            code=row["code"],
                            name=row["name"],
                            city=row["city"],
                            state_or_region=row.get("state_or_region") or None,
                            country_code=row["country_code"],
                            latitude=float(row["latitude"]),
                            longitude=float(row["longitude"]),
                            timezone=row["timezone"],
                        )
                    )
                    if record.code in seen:
                        if seen[record.code] == record:
                            result.skipped_count += 1
                            continue
                    seen[record.code] = record
                    parsed.append((row_number, record))
                except (KeyError, TypeError, ValueError) as exc:
                    result.rejected_count += 1
                    result.rejected_reasons.append({"row_number": row_number, "reason": str(exc)})

        with db.begin():
            for _, record in parsed:
                existing = db.get(Airport, record.code)
                values = record.model_dump()
                if existing is None:
                    db.add(Airport(**values))
                    result.inserted_count += 1
                    continue
                if any(getattr(existing, key) != value for key, value in values.items()):
                    for key, value in values.items():
                        setattr(existing, key, value)
                    result.updated_count += 1
                else:
                    result.skipped_count += 1
        return result

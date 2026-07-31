import csv
from pathlib import Path

from app.providers.schedule import ScheduleImportBatch
from app.schemas.schedule_import import RawScheduleRecord


class StaticCsvScheduleProvider:
    """Static CSV provider for fixture or offline schedule data."""

    def __init__(self, file_path: str | Path) -> None:
        self.file_path = Path(file_path)

    def fetch_schedule(self) -> ScheduleImportBatch:
        """
        Read schedule data from a CSV file.

        CSV format (header row required):
        carrier_code,flight_number,origin_code,destination_code,
        departure_local_time,arrival_local_time,arrival_day_offset,
        effective_start,effective_end,operating_days,equipment_code

        operating_days: comma-separated weekday numbers (1-7, ISO: 1=Monday, 7=Sunday)
        departure_local_time, arrival_local_time: HH:MM format

        Returns:
            ScheduleImportBatch: Raw records parsed from CSV.

        Raises:
            FileNotFoundError: If file does not exist.
            ValueError: If CSV header is invalid or row parsing fails.
        """
        if not self.file_path.exists():
            raise FileNotFoundError(f"Schedule file not found: {self.file_path}")

        records: list[RawScheduleRecord] = []
        with open(self.file_path, newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise ValueError("CSV file is empty or has no header")

            for row_num, row in enumerate(reader, start=2):  # Start at 2 (1 = header)
                try:
                    record = RawScheduleRecord(
                        carrier_code=row["carrier_code"].strip(),
                        flight_number=row["flight_number"].strip(),
                        origin_code=row["origin_code"].strip().upper(),
                        destination_code=row["destination_code"].strip().upper(),
                        departure_local_time=row["departure_local_time"].strip(),
                        arrival_local_time=row["arrival_local_time"].strip(),
                        arrival_day_offset=int(row["arrival_day_offset"].strip()),
                        effective_start=row["effective_start"].strip(),
                        effective_end=row.get("effective_end", "").strip() or None,
                        operating_days=row["operating_days"].strip(),
                        equipment_code=row.get("equipment_code", "").strip() or None,
                    )
                    records.append(record)
                except (KeyError, ValueError) as e:
                    raise ValueError(
                        f"Invalid row {row_num} in {self.file_path}: {e}"
                    ) from e

        return ScheduleImportBatch(
            records=records,
            source_name="static_csv",
            source_version=self.file_path.name,
        )

import csv
import hashlib
from datetime import date
from pathlib import Path

from app.providers.schedule import ScheduleImportBatch
from app.schemas.schedule_import import ProviderRejectedRow, RawScheduleRecord


class StaticCsvScheduleProvider:
    """Static CSV provider for fixture or offline schedule data."""

    def __init__(self, file_path: str | Path) -> None:
        self.file_path = Path(file_path)

    async def fetch_schedule(self, start_date: date, end_date: date) -> ScheduleImportBatch:
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
        rejected_rows: list[ProviderRejectedRow] = []
        raw_source = self.file_path.read_bytes()
        with self.file_path.open(newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise ValueError("CSV file is empty or has no header")

            required = {
                "carrier_code",
                "flight_number",
                "origin_code",
                "destination_code",
                "departure_local_time",
                "arrival_local_time",
                "arrival_day_offset",
                "effective_start",
                "effective_end",
                "operating_days",
            }
            missing = required - set(reader.fieldnames)
            if missing:
                raise ValueError(f"Missing required CSV columns: {sorted(missing)}")

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
                    record_start = date.fromisoformat(record.effective_start)
                    record_end = (
                        date.fromisoformat(record.effective_end)
                        if record.effective_end
                        else date.max
                    )
                    if record_end >= start_date and record_start <= end_date:
                        records.append(record)
                except (KeyError, ValueError) as e:
                    rejected_rows.append(
                        ProviderRejectedRow(row_number=row_num, raw_record=dict(row), reason=str(e))
                    )

        effective_dates = [
            date.fromisoformat(record.effective_start)
            for record in records
            if record.effective_start
        ]

        return ScheduleImportBatch(
            records=records,
            source_name="static_csv",
            source_version=self.file_path.name,
            provider_type="static_csv",
            effective_start=min(effective_dates) if effective_dates else None,
            effective_end=max(
                [
                    date.fromisoformat(record.effective_end)
                    for record in records
                    if record.effective_end
                ],
                default=None,
            ),
            rejected_rows=rejected_rows,
            raw_source_checksum=hashlib.sha256(raw_source).hexdigest(),
        )

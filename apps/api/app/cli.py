import argparse
import asyncio
import json
from datetime import date
from pathlib import Path

from app.db.session import SessionLocal
from app.providers.static_csv import StaticCsvScheduleProvider
from app.services.airport_import import AirportSeedImporter
from app.services.schedule_import import ScheduleImportService, get_active_schedule_status


def _date(value: str) -> date:
    return date.fromisoformat(value)


def main() -> int:
    parser = argparse.ArgumentParser(description="GoWild Phase 2 data commands")
    subparsers = parser.add_subparsers(dest="command", required=True)

    airport_parser = subparsers.add_parser("airport-seed")
    airport_parser.add_argument("path", type=Path)

    for command in ("schedule-validate", "schedule-import"):
        schedule_parser = subparsers.add_parser(command)
        schedule_parser.add_argument("path", type=Path)
        schedule_parser.add_argument("--start-date", type=_date, default=date.min)
        schedule_parser.add_argument("--end-date", type=_date, default=date.max)

    subparsers.add_parser("schedule-status")
    args = parser.parse_args()

    with SessionLocal() as db:
        if args.command == "airport-seed":
            airport_result = AirportSeedImporter.import_csv(args.path, db)
            print(airport_result.model_dump_json())
            return 1 if airport_result.rejected_count else 0

        if args.command == "schedule-status":
            print(json.dumps(get_active_schedule_status(db), default=str))
            return 0

        provider = StaticCsvScheduleProvider(args.path)
        schedule_result = asyncio.run(
            ScheduleImportService.import_schedule(
                provider,
                db,
                start_date=args.start_date,
                end_date=args.end_date,
                activate=args.command == "schedule-import",
            )
        )
        print(schedule_result.model_dump_json())
        return 0 if schedule_result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())

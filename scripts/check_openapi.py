import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.main import app


def main() -> None:
    checked_in_path = ROOT / "apps" / "api" / "openapi.json"
    checked_in = json.loads(checked_in_path.read_text())
    generated = app.openapi()
    if checked_in != generated:
        raise SystemExit(
            "apps/api/openapi.json is stale; regenerate it from app.main:app before committing"
        )
    print(f"OpenAPI contract is current: {checked_in_path}")


if __name__ == "__main__":
    main()

"""Export the FastAPI OpenAPI schema to apps/api/openapi.json (deterministic).

Run: python scripts/export_openapi.py
The output is stable (sorted keys, trailing newline) so CI can detect drift with
`git diff --exit-status`. The frontend generates its TS types from this file.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.main import app

OUTPUT = Path(__file__).resolve().parent.parent / "openapi.json"


def main() -> None:
    schema = app.openapi()
    OUTPUT.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_initial_migration_is_a_forward_head_with_airport_seed_data():
    api_root = Path(__file__).parents[1]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("script_location", str(api_root / "migrations"))
    script = ScriptDirectory.from_config(config)
    heads = script.get_heads()

    assert heads == ["0001_create_airports"]
    migration = api_root / "migrations" / "versions" / "0001_create_airports.py"
    migration_text = migration.read_text()
    assert 'op.create_table(\n        "airports"' in migration_text
    assert '"code": "ATL"' in migration_text

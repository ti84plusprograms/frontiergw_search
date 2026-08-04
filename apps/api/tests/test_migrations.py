from pathlib import Path

from alembic import command
from alembic.config import Config


def test_phase_2_migrations_generate_safe_postgres_upgrade_sql(capsys):
    api_root = Path(__file__).parent.parent
    config = Config(str(api_root / "alembic.ini"))
    command.upgrade(config, "head", sql=True)
    captured = capsys.readouterr()
    sql = captured.out

    assert "0004" in sql
    assert "ALTER TABLE routes ALTER COLUMN id DROP DEFAULT" in sql
    assert "ALTER TABLE routes ALTER COLUMN id TYPE UUID" in sql
    assert "UPDATE data_sources SET retrieved_at = created_at" in sql
    assert "ALTER TABLE data_sources RENAME provider_metadata TO metadata" in sql
    assert "uq_data_sources_one_active" in sql
    assert "routes_operating_days_valid" in sql


def test_alembic_console_entrypoint_adds_project_root_to_import_path():
    api_root = Path(__file__).parent.parent
    config = Config(str(api_root / "alembic.ini"))
    assert config.get_main_option("prepend_sys_path") == "."

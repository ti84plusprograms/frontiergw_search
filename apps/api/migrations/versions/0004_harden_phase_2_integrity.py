"""harden phase 2 integrity and source activation

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-31

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE data_sources SET retrieved_at = created_at WHERE retrieved_at IS NULL")
    op.alter_column("data_sources", "retrieved_at", nullable=False)
    op.alter_column(
        "data_sources",
        "provider_metadata",
        new_column_name="metadata",
        existing_type=sa.JSON(),
    )

    op.create_check_constraint(
        "airports_code_iata_format",
        "airports",
        "code ~ '^[A-Z]{3}$'",
    )
    op.create_check_constraint(
        "airports_country_format",
        "airports",
        "country_code ~ '^[A-Z]{2}$'",
    )
    op.create_check_constraint(
        "airports_latitude_range",
        "airports",
        "latitude >= -90 AND latitude <= 90",
    )
    op.create_check_constraint(
        "airports_longitude_range",
        "airports",
        "longitude >= -180 AND longitude <= 180",
    )

    for table in ("routes", "scheduled_flights"):
        op.alter_column(table, "id", server_default=None)
        op.alter_column(
            table,
            "id",
            existing_type=sa.Integer(),
            type_=postgresql.UUID(as_uuid=True),
            existing_nullable=False,
            server_default=sa.text("gen_random_uuid()"),
            postgresql_using=("('00000000-0000-0000-0000-' || lpad(to_hex(id), 12, '0'))::uuid"),
        )
        op.create_check_constraint(
            f"{table}_effective_date_range",
            table,
            "effective_end IS NULL OR effective_end >= effective_start",
        )
        op.create_check_constraint(
            f"{table}_operating_days_valid",
            table,
            "array_length(operating_days, 1) > 0",
        )

    op.create_check_constraint(
        "scheduled_flights_carrier_format",
        "scheduled_flights",
        "carrier_code ~ '^[A-Z0-9]{2,3}$'",
    )
    op.alter_column(
        "scheduled_flights",
        "carrier_code",
        existing_type=sa.String(2),
        type_=sa.String(3),
        existing_nullable=False,
    )
    op.alter_column(
        "scheduled_flights",
        "flight_number",
        existing_type=sa.String(10),
        type_=sa.String(8),
        existing_nullable=False,
    )
    op.create_check_constraint(
        "scheduled_flights_number_format",
        "scheduled_flights",
        "flight_number ~ '^[A-Z0-9]{1,8}$'",
    )

    op.create_unique_constraint(
        "uq_data_sources_identity", "data_sources", ["name", "provider_type", "version"]
    )
    op.create_unique_constraint("uq_data_sources_checksum", "data_sources", ["checksum"])
    op.execute(
        """
        CREATE UNIQUE INDEX uq_data_sources_one_active
        ON data_sources ((1))
        WHERE is_active IS TRUE
        """
    )
    op.create_unique_constraint(
        "uq_routes_source_identity",
        "routes",
        ["origin_code", "destination_code", "effective_start", "data_source_id"],
    )
    op.create_unique_constraint(
        "uq_flights_source_identity",
        "scheduled_flights",
        [
            "carrier_code",
            "flight_number",
            "origin_code",
            "destination_code",
            "effective_start",
            "data_source_id",
        ],
    )
    op.drop_index("idx_flights_number", table_name="scheduled_flights")
    op.create_index(
        "idx_flights_number",
        "scheduled_flights",
        ["carrier_code", "flight_number"],
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM routes
                WHERE id::text !~ '^00000000-0000-0000-0000-[0-9a-f]{12}$'
            ) OR EXISTS (
                SELECT 1 FROM scheduled_flights
                WHERE id::text !~ '^00000000-0000-0000-0000-[0-9a-f]{12}$'
            ) THEN
                RAISE EXCEPTION 'Cannot downgrade generated UUID identifiers safely';
            END IF;
        END $$;
        """
    )
    op.drop_index("idx_flights_number", table_name="scheduled_flights")
    op.create_index("idx_flights_number", "scheduled_flights", ["flight_number"])
    op.drop_constraint("uq_flights_source_identity", "scheduled_flights", type_="unique")
    op.drop_constraint("uq_routes_source_identity", "routes", type_="unique")
    op.drop_index("uq_data_sources_one_active", table_name="data_sources")
    op.drop_constraint("uq_data_sources_checksum", "data_sources", type_="unique")
    op.drop_constraint("uq_data_sources_identity", "data_sources", type_="unique")
    op.drop_constraint("scheduled_flights_number_format", "scheduled_flights", type_="check")
    op.drop_constraint("scheduled_flights_carrier_format", "scheduled_flights", type_="check")
    op.alter_column(
        "scheduled_flights",
        "flight_number",
        existing_type=sa.String(8),
        type_=sa.String(10),
        existing_nullable=False,
    )
    op.alter_column(
        "scheduled_flights",
        "carrier_code",
        existing_type=sa.String(3),
        type_=sa.String(2),
        existing_nullable=False,
    )

    for table in ("scheduled_flights", "routes"):
        op.alter_column(table, "id", server_default=None)
        op.drop_constraint(f"{table}_operating_days_valid", table, type_="check")
        op.drop_constraint(f"{table}_effective_date_range", table, type_="check")
        op.alter_column(
            table,
            "id",
            existing_type=postgresql.UUID(as_uuid=True),
            type_=sa.Integer(),
            existing_nullable=False,
            postgresql_using="(('x' || right(id::text, 12))::bit(48))::bigint",
            server_default=sa.text(f"nextval('{table}_id_seq'::regclass)"),
        )

    op.drop_constraint("airports_longitude_range", "airports", type_="check")
    op.drop_constraint("airports_latitude_range", "airports", type_="check")
    op.drop_constraint("airports_country_format", "airports", type_="check")
    op.drop_constraint("airports_code_iata_format", "airports", type_="check")
    op.alter_column("data_sources", "retrieved_at", nullable=True)
    op.alter_column(
        "data_sources",
        "metadata",
        new_column_name="provider_metadata",
        existing_type=sa.JSON(),
    )

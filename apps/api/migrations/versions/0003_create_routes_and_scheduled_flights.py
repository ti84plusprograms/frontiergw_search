"""create_routes_and_scheduled_flights

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-31

"""

from alembic import op
import sqlalchemy as sa


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "routes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("origin_code", sa.String(3), nullable=False),
        sa.Column("destination_code", sa.String(3), nullable=False),
        sa.Column("effective_start", sa.Date(), nullable=False),
        sa.Column("effective_end", sa.Date(), nullable=True),
        sa.Column("operating_days", sa.ARRAY(sa.Integer()), nullable=False, server_default="{}"),
        sa.Column("data_source_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.literal(True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("origin_code != destination_code", name="routes_no_self_loop"),
        sa.CheckConstraint("operating_days != '{}'"),
        sa.ForeignKeyConstraint(["destination_code"], ["airports.code"]),
        sa.ForeignKeyConstraint(["origin_code"], ["airports.code"]),
        sa.ForeignKeyConstraint(["data_source_id"], ["data_sources.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_routes_destination", "routes", ["destination_code"])
    op.create_index("idx_routes_origin_dates", "routes", ["origin_code", "effective_start", "effective_end"])

    op.create_table(
        "scheduled_flights",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("carrier_code", sa.String(2), nullable=False),
        sa.Column("flight_number", sa.String(10), nullable=False),
        sa.Column("origin_code", sa.String(3), nullable=False),
        sa.Column("destination_code", sa.String(3), nullable=False),
        sa.Column("departure_local_time", sa.Time(), nullable=False),
        sa.Column("arrival_local_time", sa.Time(), nullable=False),
        sa.Column("arrival_day_offset", sa.Integer(), nullable=False),
        sa.Column("effective_start", sa.Date(), nullable=False),
        sa.Column("effective_end", sa.Date(), nullable=True),
        sa.Column("operating_days", sa.ARRAY(sa.Integer()), nullable=False, server_default="{}"),
        sa.Column("equipment_code", sa.String(10), nullable=True),
        sa.Column("data_source_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("arrival_day_offset >= 0 AND arrival_day_offset <= 2", name="valid_arrival_day_offset"),
        sa.CheckConstraint("origin_code != destination_code", name="flights_no_self_loop"),
        sa.ForeignKeyConstraint(["destination_code"], ["airports.code"]),
        sa.ForeignKeyConstraint(["origin_code"], ["airports.code"]),
        sa.ForeignKeyConstraint(["data_source_id"], ["data_sources.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_flights_destination", "scheduled_flights", ["destination_code"])
    op.create_index("idx_flights_number", "scheduled_flights", ["flight_number"])
    op.create_index("idx_flights_origin_effective", "scheduled_flights", ["origin_code", "effective_start", "effective_end"])


def downgrade() -> None:
    op.drop_index("idx_flights_origin_effective", table_name="scheduled_flights")
    op.drop_index("idx_flights_number", table_name="scheduled_flights")
    op.drop_index("idx_flights_destination", table_name="scheduled_flights")
    op.drop_table("scheduled_flights")
    op.drop_index("idx_routes_origin_dates", table_name="routes")
    op.drop_index("idx_routes_destination", table_name="routes")
    op.drop_table("routes")

"""Create the airport catalog and seed initial airports.

Revision ID: 0001_create_airports
Revises:
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_create_airports"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


airports = sa.table(
    "airports",
    sa.column("code", sa.String(3)),
    sa.column("name", sa.Text),
    sa.column("city", sa.Text),
    sa.column("state_or_region", sa.Text),
    sa.column("country_code", sa.String(2)),
    sa.column("latitude", sa.Float),
    sa.column("longitude", sa.Float),
    sa.column("timezone", sa.Text),
    sa.column("is_active", sa.Boolean),
)


def upgrade() -> None:
    op.create_table(
        "airports",
        sa.Column("code", sa.String(length=3), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("city", sa.Text(), nullable=False),
        sa.Column("state_or_region", sa.Text(), nullable=True),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("timezone", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("code"),
    )
    op.bulk_insert(
        airports,
        [
            {
                "code": "ATL",
                "name": "Hartsfield-Jackson Atlanta International Airport",
                "city": "Atlanta",
                "state_or_region": "Georgia",
                "country_code": "US",
                "latitude": 33.6407,
                "longitude": -84.4277,
                "timezone": "America/New_York",
                "is_active": True,
            },
            {
                "code": "DEN",
                "name": "Denver International Airport",
                "city": "Denver",
                "state_or_region": "Colorado",
                "country_code": "US",
                "latitude": 39.8561,
                "longitude": -104.6737,
                "timezone": "America/Denver",
                "is_active": True,
            },
            {
                "code": "LAS",
                "name": "Harry Reid International Airport",
                "city": "Las Vegas",
                "state_or_region": "Nevada",
                "country_code": "US",
                "latitude": 36.0840,
                "longitude": -115.1537,
                "timezone": "America/Los_Angeles",
                "is_active": True,
            },
            {
                "code": "MCO",
                "name": "Orlando International Airport",
                "city": "Orlando",
                "state_or_region": "Florida",
                "country_code": "US",
                "latitude": 28.4312,
                "longitude": -81.3081,
                "timezone": "America/New_York",
                "is_active": True,
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("airports")

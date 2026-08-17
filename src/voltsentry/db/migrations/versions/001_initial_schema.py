"""
FILE: src/voltsentry/db/migrations/versions/001_initial_schema.py
PATH: voltsentry/src/voltsentry/db/migrations/versions/001_initial_schema.py
DESCRIPTION: Initial database schema migration
"""

"""Initial database schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-08-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply the migration - create all tables."""

    # Create battery_readings table
    op.create_table(
        "battery_readings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("percent", sa.Integer(), nullable=False),
        sa.Column("is_charging", sa.Boolean(), nullable=False),
        sa.Column("power_draw_watts", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("percent >= 0 AND percent <= 100"),
    )
    op.create_index(
        "ix_battery_readings_timestamp_percent",
        "battery_readings",
        ["timestamp", "percent"],
    )
    op.create_index(
        "ix_battery_readings_timestamp", "battery_readings", ["timestamp"]
    )

    # Create charge_cycle_events table
    op.create_table(
        "charge_cycle_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("cycle_fraction", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create alarm_events table
    op.create_table(
        "alarm_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("alarm_type", sa.String(length=20), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
        sa.Column("snoozed", sa.Boolean(), nullable=False),
        sa.Column("snooze_until", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_alarm_events_timestamp_type",
        "alarm_events",
        ["timestamp", "alarm_type"],
    )
    op.create_index("ix_alarm_events_timestamp", "alarm_events", ["timestamp"])

    # Create calibration_records table
    op.create_table(
        "calibration_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("result_health_score", sa.Integer(), nullable=True),
        sa.Column("state", sa.String(length=30), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create automation_hook_log table
    op.create_table(
        "automation_hook_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("hook_type", sa.String(length=20), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("detail", sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_automation_hook_log_timestamp_type",
        "automation_hook_log",
        ["timestamp", "hook_type"],
    )
    op.create_index(
        "ix_automation_hook_log_timestamp",
        "automation_hook_log",
        ["timestamp"],
    )


def downgrade() -> None:
    """Revert the migration - drop all tables."""
    op.drop_table("automation_hook_log")
    op.drop_table("calibration_records")
    op.drop_table("alarm_events")
    op.drop_table("charge_cycle_events")
    op.drop_table("battery_readings")
"""Add gateway_devices table for device identity and approval workflow.

Revision ID: d4e5f6a1b2c3
Revises: a9b1c2d3e4f7
Create Date: 2026-04-10 08:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d4e5f6a1b2c3"
down_revision = "b2a1d3c4e5f6"
branch_labels = None
depends_on = None


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {item["name"] for item in inspector.get_indexes(table_name)}


def upgrade() -> None:
    """Create gateway_devices table for device pairing identity and approval lifecycle."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("gateway_devices"):
        op.create_table(
            "gateway_devices",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("gateway_id", sa.Uuid(), nullable=False),
            sa.Column("device_id", sa.String(), nullable=False),
            sa.Column("public_key_pem", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("first_seen_at", sa.DateTime(), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(), nullable=False),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("approved_by", sa.Uuid(), nullable=True),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["gateway_id"], ["gateways.id"]),
            sa.ForeignKeyConstraint(["approved_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    inspector = sa.inspect(bind)
    device_indexes = _index_names(inspector, "gateway_devices")
    if "ix_gateway_devices_gateway_id" not in device_indexes:
        op.create_index("ix_gateway_devices_gateway_id", "gateway_devices", ["gateway_id"])
    if "ix_gateway_devices_device_id" not in device_indexes:
        op.create_index("ix_gateway_devices_device_id", "gateway_devices", ["device_id"])
    if "ix_gateway_devices_status" not in device_indexes:
        op.create_index("ix_gateway_devices_status", "gateway_devices", ["status"])
    if "ix_gateway_devices_approved_by" not in device_indexes:
        op.create_index("ix_gateway_devices_approved_by", "gateway_devices", ["approved_by"])
    if "ix_gateway_devices_gateway_device" not in device_indexes:
        op.create_index(
            "ix_gateway_devices_gateway_device",
            "gateway_devices",
            ["gateway_id", "device_id"],
        )


def downgrade() -> None:
    """Drop gateway_devices table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("gateway_devices"):
        device_indexes = _index_names(inspector, "gateway_devices")
        for idx in [
            "ix_gateway_devices_gateway_device",
            "ix_gateway_devices_approved_by",
            "ix_gateway_devices_status",
            "ix_gateway_devices_device_id",
            "ix_gateway_devices_gateway_id",
        ]:
            if idx in device_indexes:
                op.drop_index(idx, table_name="gateway_devices")
        op.drop_table("gateway_devices")

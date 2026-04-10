"""Add board_outbound_webhooks table for outbound event notification.

Revision ID: b2a1d3c4e5f6
Revises: a9b1c2d3e4f7
Create Date: 2026-04-10 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b2a1d3c4e5f6"
down_revision = "a9b1c2d3e4f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create board_outbound_webhooks table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    if "board_outbound_webhooks" not in tables:
        op.create_table(
            "board_outbound_webhooks",
            sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
            sa.Column(
                "board_id",
                sa.UUID(),
                sa.ForeignKey("boards.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "organization_id",
                sa.UUID(),
                sa.ForeignKey("organizations.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("target_url", sa.String(), nullable=False),
            sa.Column("secret", sa.String(), nullable=True),
            sa.Column("event_types", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column(
                "enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
                index=True,
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade() -> None:
    """Drop board_outbound_webhooks table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    if "board_outbound_webhooks" in tables:
        op.drop_table("board_outbound_webhooks")

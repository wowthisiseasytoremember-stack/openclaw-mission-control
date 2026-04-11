"""add task_fingerprints task_id index

Revision ID: e5f6a1b2c3d4
Revises: d4e5f6a1b2c3
Create Date: 2026-04-10 08:30:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e5f6a1b2c3d4"
down_revision = "d4e5f6a1b2c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {item["name"] for item in inspector.get_indexes("task_fingerprints")}
    if "ix_task_fingerprints_task_id" not in existing:
        op.create_index("ix_task_fingerprints_task_id", "task_fingerprints", ["task_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {item["name"] for item in inspector.get_indexes("task_fingerprints")}
    if "ix_task_fingerprints_task_id" in existing:
        op.drop_index("ix_task_fingerprints_task_id", table_name="task_fingerprints")

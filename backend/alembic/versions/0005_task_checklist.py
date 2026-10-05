"""task checklist items

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-05

"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "checklist_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "task_id",
            sa.Uuid(),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.String(length=500), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("is_done", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_checklist_items_task_id", "checklist_items", ["task_id"])


def downgrade() -> None:
    op.drop_index("ix_checklist_items_task_id", table_name="checklist_items")
    op.drop_table("checklist_items")

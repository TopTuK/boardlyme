"""checklist created_at not null

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-05

"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "checklist_items",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "checklist_items",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
    )

"""done stage is always the last column

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-08

"""
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Renumber every project's stages so Backlog is first, Done is last and
    # the regular stages keep their relative order in between.
    op.execute(
        """
        UPDATE stages AS s
        SET position = r.new_pos
        FROM (
            SELECT id, ROW_NUMBER() OVER (
                PARTITION BY project_id
                ORDER BY is_backlog DESC, is_done ASC, position, id
            ) - 1 AS new_pos
            FROM stages
        ) AS r
        WHERE s.id = r.id
        """
    )


def downgrade() -> None:
    # The previous arbitrary order cannot be reconstructed; keep current positions.
    pass

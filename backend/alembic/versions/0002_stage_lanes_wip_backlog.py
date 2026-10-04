"""stage sub-lanes, WIP limits and the Backlog stage

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-05

"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("stages", sa.Column("wip_limit", sa.Integer(), nullable=True))
    op.add_column("stages", sa.Column("is_backlog", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("stages", sa.Column("is_split", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("tasks", sa.Column("stage_done", sa.Boolean(), nullable=False, server_default=sa.false()))

    # Give every existing project a Backlog as its first stage.
    op.execute("UPDATE stages SET position = position + 1")
    op.execute(
        """
        INSERT INTO stages (id, project_id, name, position, is_done, is_hidden, is_backlog, is_split, wip_limit)
        SELECT gen_random_uuid(), id, 'Backlog', 0, false, false, true, false, NULL
        FROM projects
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM stages WHERE is_backlog = true")
    op.execute("UPDATE stages SET position = position - 1")
    op.drop_column("tasks", "stage_done")
    op.drop_column("stages", "is_split")
    op.drop_column("stages", "is_backlog")
    op.drop_column("stages", "wip_limit")

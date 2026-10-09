"""task complexity and stage transition history

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-09

"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("complexity", sa.String(length=20), nullable=False, server_default="normal"),
    )

    op.create_table(
        "task_transitions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", sa.Uuid(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stage_id", sa.Uuid(), sa.ForeignKey("stages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stage_done", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("entered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("backfilled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_task_transitions_task_id", "task_transitions", ["task_id"])
    op.create_index("ix_task_transitions_project_entered", "task_transitions", ["project_id", "entered_at"])

    # Reconstruct approximate history for existing tasks. The real path is
    # unknown, so every task enters the Backlog when created, tasks in a work
    # stage reach it at their last update, and done tasks reach Done when
    # completed. Rows are flagged so cycle time can skip them.
    op.execute(
        """
        INSERT INTO task_transitions (id, project_id, task_id, stage_id, stage_done, entered_at, backfilled)
        SELECT gen_random_uuid(), t.project_id, t.id, b.id, false, t.created_at, true
        FROM tasks AS t
        JOIN stages AS b ON b.project_id = t.project_id AND b.is_backlog
        """
    )
    op.execute(
        """
        INSERT INTO task_transitions (id, project_id, task_id, stage_id, stage_done, entered_at, backfilled)
        SELECT gen_random_uuid(), t.project_id, t.id, s.id, t.stage_done, GREATEST(t.updated_at, t.created_at), true
        FROM tasks AS t
        JOIN stages AS s ON s.id = t.stage_id
        WHERE NOT s.is_backlog AND NOT s.is_done
        """
    )
    op.execute(
        """
        INSERT INTO task_transitions (id, project_id, task_id, stage_id, stage_done, entered_at, backfilled)
        SELECT gen_random_uuid(), t.project_id, t.id, s.id, false, t.completed_at, true
        FROM tasks AS t
        JOIN stages AS s ON s.id = t.stage_id
        WHERE s.is_done AND t.completed_at IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_task_transitions_project_entered", table_name="task_transitions")
    op.drop_index("ix_task_transitions_task_id", table_name="task_transitions")
    op.drop_table("task_transitions")
    op.drop_column("tasks", "complexity")

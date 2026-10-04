"""reminder runs (daily digest dedup)

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-05

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reminder_runs",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column(
            "user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("run_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_unique_constraint("uq_reminder_runs_kind_user_date", "reminder_runs", ["kind", "user_id", "run_date"])


def downgrade() -> None:
    op.drop_constraint("uq_reminder_runs_kind_user_date", "reminder_runs", type_="unique")
    op.drop_table("reminder_runs")

"""google oauth identity on users

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-09

"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("users", "telegram_id", existing_type=sa.BigInteger(), nullable=True)
    op.add_column("users", sa.Column("google_sub", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("email", sa.String(length=320), nullable=True))
    op.create_index("ix_users_google_sub", "users", ["google_sub"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_google_sub", table_name="users")
    op.drop_column("users", "email")
    op.drop_column("users", "google_sub")
    op.execute("DELETE FROM users WHERE telegram_id IS NULL")
    op.alter_column("users", "telegram_id", existing_type=sa.BigInteger(), nullable=False)

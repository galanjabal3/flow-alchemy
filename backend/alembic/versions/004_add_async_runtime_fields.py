"""Add async runtime fields to executions table

Revision ID: 004
Revises: b9e1fdb6f482
Create Date: 2026-09-15
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "004"
down_revision = "b9e1fdb6f482"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add async runtime fields to executions table
    op.add_column("executions", sa.Column("idempotency_key", sa.String(255), unique=True, nullable=True))
    op.add_column("executions", sa.Column("retry_count", sa.Integer(), server_default="0"))
    op.add_column("executions", sa.Column("max_retries", sa.Integer(), server_default="3"))
    op.add_column("executions", sa.Column("worker_id", sa.String(100), nullable=True))
    op.add_column("executions", sa.Column("queued_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("executions", "queued_at")
    op.drop_column("executions", "worker_id")
    op.drop_column("executions", "max_retries")
    op.drop_column("executions", "retry_count")
    op.drop_column("executions", "idempotency_key")

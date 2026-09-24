"""Add definition_snapshot to executions table

Revision ID: 008
Revises: 007
Create Date: 2026-09-19
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add definition_snapshot column to executions table
    op.add_column(
        "executions",
        sa.Column("definition_snapshot", sa.JSON(), nullable=True),
    )
    op.add_column(
        "executions",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("executions", "updated_at")
    op.drop_column("executions", "definition_snapshot")

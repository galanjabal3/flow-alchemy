"""Add workflow versions and replay support

Revision ID: 005
Revises: 004
Create Date: 2026-09-15
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create workflow_versions table
    op.create_table(
        "workflow_versions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("workflow_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workflow_id", "version"),
    )


def downgrade() -> None:
    op.drop_table("workflow_versions")

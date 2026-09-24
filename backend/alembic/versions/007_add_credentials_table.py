"""Add credentials table for secure credential storage

Revision ID: 007
Revises: 006
Create Date: 2026-09-19
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create credentials table
    op.create_table(
        "credentials",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("credential_type", sa.String(50), nullable=False),
        sa.Column("encrypted_value", sa.Text(), nullable=False),
        sa.Column("encryption_version", sa.Integer(), nullable=True, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Add index for faster lookups by user_id
    op.create_index("ix_credentials_user_id", "credentials", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_credentials_user_id")
    op.drop_table("credentials")

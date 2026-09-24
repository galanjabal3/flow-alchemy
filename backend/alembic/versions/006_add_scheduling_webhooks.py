"""Add scheduling and webhook fields

Revision ID: 006
Revises: 005
Create Date: 2026-09-15
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add webhook fields to workflows
    op.add_column("workflows", sa.Column("webhook_key", sa.String(255), nullable=True))
    op.add_column("workflows", sa.Column("webhook_secret", sa.String(255), nullable=True))
    op.create_unique_constraint("uq_workflows_webhook_key", "workflows", ["webhook_key"])


def downgrade() -> None:
    op.drop_constraint("uq_workflows_webhook_key", "workflows", type_="unique")
    op.drop_column("workflows", "webhook_secret")
    op.drop_column("workflows", "webhook_key")

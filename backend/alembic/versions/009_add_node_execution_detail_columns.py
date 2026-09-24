"""add_node_execution_detail_columns

Add node_ref + node_type to node_executions so per-node execution
history can be persisted for arbitrary workflows (not only seeded demo
workflows that have workflow_nodes rows). node_id becomes nullable —
some executions reference nodes that have no workflow_nodes row.

Revision ID: 009
Revises: 008
Create Date: 2026-09-24 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("node_executions", sa.Column("node_ref", sa.String(100), nullable=True))
    op.add_column("node_executions", sa.Column("node_type", sa.String(100), nullable=True))
    # node_id may point to a workflow_nodes row (seeded demo workflows) or be
    # NULL when the executing workflow has no relational node row yet.
    op.alter_column("node_executions", "node_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    op.alter_column("node_executions", "node_id", existing_type=sa.Integer(), nullable=False)
    op.drop_column("node_executions", "node_type")
    op.drop_column("node_executions", "node_ref")
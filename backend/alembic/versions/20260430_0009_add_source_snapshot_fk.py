"""Add source_snapshot_id foreign key to review_items.

Revision ID: 20260430_0009
Revises: 20260430_0008
Create Date: 2026-04-30 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260430_0009"
down_revision: Union[str, None] = "20260430_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add source_snapshot_id column (nullable FK)
    op.add_column(
        "review_items",
        sa.Column(
            "source_snapshot_id",
            sa.Integer(),
            sa.ForeignKey("source_snapshots.id"),
            nullable=True,
            index=True,
        ),
    )


def downgrade() -> None:
    # Drop the column and index
    op.drop_column("review_items", "source_snapshot_id")

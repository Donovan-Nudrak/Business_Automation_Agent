"""add stripe_event_id to events

Revision ID: a3b8c1d2e4f5
Revises: fb8612f3423d
Create Date: 2026-06-02 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a3b8c1d2e4f5"
down_revision: Union[str, None] = "fb8612f3423d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("events", sa.Column("stripe_event_id", sa.String(length=255), nullable=True))
    op.create_unique_constraint(
        "uq_events_stripe_event_id",
        "events",
        ["stripe_event_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_events_stripe_event_id", "events", type_="unique")
    op.drop_column("events", "stripe_event_id")

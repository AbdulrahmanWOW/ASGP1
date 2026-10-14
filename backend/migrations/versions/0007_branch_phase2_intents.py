"""Branch phase 2: intent drafts, human confirmation, intent-token sessions."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_intents"
down_revision: str | None = "0006_hardening"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column(
            "requires_intent_token", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.add_column("intent_anchors", sa.Column("confirmed_by", sa.String(120), nullable=True))
    op.create_table(
        "intent_drafts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("intent", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, index=True),
        sa.Column("proposal", sa.JSON(), nullable=False),
        sa.Column("drafted_by", sa.String(120), nullable=False),
        sa.Column("created_by", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=True),
        sa.Column("resolved_by", sa.String(120), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("intent_drafts")
    op.drop_column("intent_anchors", "confirmed_by")
    op.drop_column("sessions", "requires_intent_token")

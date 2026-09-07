"""Phase 5 semantic and behavioral security findings."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_phase5"
down_revision: str | None = "0003_phase4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("decisions", sa.Column("intent_alignment", sa.Float(), nullable=True))
    op.create_table(
        "security_findings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("action_id", sa.String(36), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence", sa.String(500), nullable=False),
        sa.Column("risk_delta", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_security_findings_action_id", "security_findings", ["action_id"])
    op.create_index("ix_security_findings_session_id", "security_findings", ["session_id"])


def downgrade() -> None:
    op.drop_table("security_findings")
    op.drop_column("decisions", "intent_alignment")

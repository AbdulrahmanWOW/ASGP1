"""Phase 3 risk state and approval workflow."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_phase3"
down_revision: str | None = "0001_phase2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "sessions", sa.Column("risk_score", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column(
        "tools", sa.Column("sensitivity", sa.String(20), nullable=False, server_default="low")
    )
    op.add_column(
        "decisions", sa.Column("risk_before", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column(
        "decisions", sa.Column("risk_delta", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column(
        "decisions", sa.Column("risk_after", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column("decisions", sa.Column("approval_id", sa.String(36), nullable=True))
    op.create_table(
        "risk_changes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("action_id", sa.String(36), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("previous_score", sa.Integer(), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("new_score", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_risk_changes_action_id", "risk_changes", ["action_id"])
    op.create_index("ix_risk_changes_session_id", "risk_changes", ["session_id"])
    op.create_table(
        "approvals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("action_id", sa.String(36), nullable=False, unique=True),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("tool_name", sa.String(120), nullable=False),
        sa.Column("action_digest", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_approvals_action_id", "approvals", ["action_id"])
    op.create_index("ix_approvals_session_id", "approvals", ["session_id"])
    op.create_index("ix_approvals_status", "approvals", ["status"])


def downgrade() -> None:
    op.drop_table("approvals")
    op.drop_table("risk_changes")
    op.drop_column("decisions", "approval_id")
    op.drop_column("decisions", "risk_after")
    op.drop_column("decisions", "risk_delta")
    op.drop_column("decisions", "risk_before")
    op.drop_column("tools", "sensitivity")
    op.drop_column("sessions", "risk_score")

"""Branch phase 1: tool declarations, traceability, session termination reason."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_hardening"
down_revision: str | None = "0005_phase6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("status_reason", sa.String(120), nullable=True))

    op.add_column(
        "tools",
        sa.Column("category", sa.String(20), nullable=False, server_default="other"),
    )
    op.add_column("tools", sa.Column("path_parameters", sa.JSON(), nullable=True))
    op.add_column("tools", sa.Column("destination_parameters", sa.JSON(), nullable=True))

    op.add_column("actions", sa.Column("intent_anchor_version", sa.Integer(), nullable=True))
    op.add_column("actions", sa.Column("intent_anchor_hash", sa.String(64), nullable=True))
    op.add_column("actions", sa.Column("actor", sa.String(120), nullable=True))

    op.add_column("decisions", sa.Column("action_risk", sa.Integer(), nullable=True))
    op.add_column("decisions", sa.Column("decided_by", sa.String(40), nullable=True))

    op.add_column("audit_events", sa.Column("intent_anchor_hash", sa.String(64), nullable=True))
    op.add_column("audit_events", sa.Column("decided_by", sa.String(40), nullable=True))
    op.add_column("audit_events", sa.Column("actor", sa.String(120), nullable=True))

    op.add_column("approvals", sa.Column("resolved_by", sa.String(120), nullable=True))
    op.add_column("approvals", sa.Column("reason_codes", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("approvals", "reason_codes")
    op.drop_column("approvals", "resolved_by")
    op.drop_column("audit_events", "actor")
    op.drop_column("audit_events", "decided_by")
    op.drop_column("audit_events", "intent_anchor_hash")
    op.drop_column("decisions", "decided_by")
    op.drop_column("decisions", "action_risk")
    op.drop_column("actions", "actor")
    op.drop_column("actions", "intent_anchor_hash")
    op.drop_column("actions", "intent_anchor_version")
    op.drop_column("tools", "destination_parameters")
    op.drop_column("tools", "path_parameters")
    op.drop_column("tools", "category")
    op.drop_column("sessions", "status_reason")

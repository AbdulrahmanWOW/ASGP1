"""Phase 4 agent identities and signed request replay state."""

import hashlib
import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

revision: str = "0003_phase4"
down_revision: str | None = "0002_phase3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _anchor_hash(row: object) -> str:
    payload = {
        "allowed_destinations": sorted(row.allowed_destinations),
        "allowed_paths": sorted(row.allowed_paths),
        "allowed_tools": sorted(row.allowed_tools),
        "forbidden_tools": sorted(row.forbidden_tools),
        "intent": row.intent,
        "session_id": row.session_id,
        "version": row.version,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def upgrade() -> None:
    with op.batch_alter_table("intent_anchors") as batch:
        batch.add_column(sa.Column("canonical_hash", sa.String(64), nullable=True))
    anchors = sa.table(
        "intent_anchors",
        sa.column("id", sa.String),
        sa.column("session_id", sa.String),
        sa.column("version", sa.Integer),
        sa.column("intent", sa.Text),
        sa.column("allowed_tools", sa.JSON),
        sa.column("forbidden_tools", sa.JSON),
        sa.column("allowed_paths", sa.JSON),
        sa.column("allowed_destinations", sa.JSON),
        sa.column("canonical_hash", sa.String),
    )
    if context.is_offline_mode():
        # Offline SQL cannot read and hash existing rows. The sentinel deliberately
        # invalidates old signed scopes until an online re-anchor is performed.
        op.execute("UPDATE intent_anchors SET canonical_hash = " + repr("0" * 64))
    else:
        connection = op.get_bind()
        for row in connection.execute(sa.select(anchors)).all():
            connection.execute(
                anchors.update()
                .where(anchors.c.id == row.id)
                .values(canonical_hash=_anchor_hash(row))
            )
    with op.batch_alter_table("intent_anchors") as batch:
        batch.alter_column("canonical_hash", existing_type=sa.String(64), nullable=False)

    op.add_column(
        "tools",
        sa.Column("requires_signature", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "agents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("public_key", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("last_sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agents_status", "agents", ["status"])
    op.create_table(
        "request_nonces",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "agent_id",
            sa.String(36),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("nonce", sa.String(120), nullable=False),
        sa.Column("action_id", sa.String(36), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("agent_id", "nonce"),
    )
    op.create_index("ix_request_nonces_agent_id", "request_nonces", ["agent_id"])


def downgrade() -> None:
    op.drop_table("request_nonces")
    op.drop_table("agents")
    op.drop_column("tools", "requires_signature")
    op.drop_column("intent_anchors", "canonical_hash")

"""Phase 6 tamper-evident audit chain and pipeline timings."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op
from app.core.canonical import audit_entry_hash

revision: str = "0005_phase6"
down_revision: str | None = "0004_phase5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "decisions",
        sa.Column("stage_timings_ms", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.add_column(
        "decisions",
        sa.Column("total_latency_ms", sa.Float(), nullable=False, server_default="0"),
    )
    with op.batch_alter_table("audit_events") as batch:
        batch.add_column(sa.Column("sequence", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("previous_hash", sa.String(64), nullable=True))
        batch.add_column(sa.Column("entry_hash", sa.String(64), nullable=True))
        batch.add_column(sa.Column("risk_before", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("risk_after", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("finding_codes", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("stage_timings_ms", sa.JSON(), nullable=True))

    op.create_table(
        "audit_heads",
        sa.Column("session_id", sa.String(36), primary_key=True),
        sa.Column("last_sequence", sa.Integer(), nullable=False),
        sa.Column("last_hash", sa.String(64), nullable=False),
        sa.Column("event_count", sa.Integer(), nullable=False),
    )
    audit = sa.table(
        "audit_events",
        sa.column("id", sa.String),
        sa.column("action_id", sa.String),
        sa.column("session_id", sa.String),
        sa.column("tool_name", sa.String),
        sa.column("safe_parameters", sa.JSON),
        sa.column("outcome", sa.String),
        sa.column("reason_codes", sa.JSON),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("sequence", sa.Integer),
        sa.column("previous_hash", sa.String),
        sa.column("entry_hash", sa.String),
        sa.column("risk_before", sa.Integer),
        sa.column("risk_after", sa.Integer),
        sa.column("finding_codes", sa.JSON),
        sa.column("stage_timings_ms", sa.JSON),
    )
    heads = sa.table(
        "audit_heads",
        sa.column("session_id", sa.String),
        sa.column("last_sequence", sa.Integer),
        sa.column("last_hash", sa.String),
        sa.column("event_count", sa.Integer),
    )
    if context.is_offline_mode():
        sentinel = "0" * 64
        op.execute(
            "WITH ranked AS (SELECT id, row_number() OVER "
            "(PARTITION BY session_id ORDER BY created_at, id) AS seq FROM audit_events) "
            "UPDATE audit_events SET sequence = ranked.seq, previous_hash = "
            f"'{sentinel}', entry_hash = '{sentinel}', risk_before = 0, risk_after = 0, "
            "finding_codes = '[]'::json, stage_timings_ms = '{}'::json "
            "FROM ranked WHERE audit_events.id = ranked.id"
        )
        op.execute(
            "INSERT INTO audit_heads (session_id, last_sequence, last_hash, event_count) "
            f"SELECT session_id, max(sequence), '{sentinel}', count(*) "
            "FROM audit_events GROUP BY session_id"
        )
    else:
        connection = op.get_bind()
        session_ids = connection.execute(sa.select(audit.c.session_id).distinct()).scalars()
        for session_id in session_ids:
            previous_hash = "0" * 64
            sequence = 0
            rows = connection.execute(
                sa.select(audit)
                .where(audit.c.session_id == session_id)
                .order_by(audit.c.created_at, audit.c.id)
            ).all()
            for row in rows:
                sequence += 1
                entry_hash = audit_entry_hash(
                    event_id=row.id,
                    action_id=row.action_id,
                    session_id=row.session_id,
                    sequence=sequence,
                    tool_name=row.tool_name,
                    safe_parameters=row.safe_parameters,
                    outcome=row.outcome,
                    reason_codes=row.reason_codes,
                    risk_before=0,
                    risk_after=0,
                    finding_codes=[],
                    stage_timings_ms={},
                    previous_hash=previous_hash,
                    created_at=row.created_at,
                )
                connection.execute(
                    audit.update()
                    .where(audit.c.id == row.id)
                    .values(
                        sequence=sequence,
                        previous_hash=previous_hash,
                        entry_hash=entry_hash,
                        risk_before=0,
                        risk_after=0,
                        finding_codes=[],
                        stage_timings_ms={},
                    )
                )
                previous_hash = entry_hash
            connection.execute(
                heads.insert().values(
                    session_id=session_id,
                    last_sequence=sequence,
                    last_hash=previous_hash,
                    event_count=sequence,
                )
            )
    with op.batch_alter_table("audit_events") as batch:
        batch.alter_column("sequence", existing_type=sa.Integer(), nullable=False)
        batch.alter_column("previous_hash", existing_type=sa.String(64), nullable=False)
        batch.alter_column("entry_hash", existing_type=sa.String(64), nullable=False)
        batch.alter_column("risk_before", existing_type=sa.Integer(), nullable=False)
        batch.alter_column("risk_after", existing_type=sa.Integer(), nullable=False)
        batch.alter_column("finding_codes", existing_type=sa.JSON(), nullable=False)
        batch.alter_column("stage_timings_ms", existing_type=sa.JSON(), nullable=False)
        batch.create_unique_constraint(
            "uq_audit_events_session_sequence", ["session_id", "sequence"]
        )


def downgrade() -> None:
    op.drop_table("audit_heads")
    with op.batch_alter_table("audit_events") as batch:
        batch.drop_constraint("uq_audit_events_session_sequence", type_="unique")
        batch.drop_column("stage_timings_ms")
        batch.drop_column("finding_codes")
        batch.drop_column("risk_after")
        batch.drop_column("risk_before")
        batch.drop_column("entry_hash")
        batch.drop_column("previous_hash")
        batch.drop_column("sequence")
    op.drop_column("decisions", "total_latency_ms")
    op.drop_column("decisions", "stage_timings_ms")

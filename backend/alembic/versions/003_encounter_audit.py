"""Create encounter_audit table for the encounter audit trail (ADR-4).

Tracks model usage, token counts, costs, and reasoning snapshots for
every node execution within a triage encounter.

Revision ID: 003
Revises: 002
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS encounter_audit (
            id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            encounter_id         UUID NOT NULL,
            patient_id_encrypted TEXT NOT NULL,
            node_name            TEXT NOT NULL,
            model_used           TEXT NOT NULL,
            input_tokens         INT,
            output_tokens        INT,
            cost_usd             DECIMAL(10, 8),
            reasoning_snapshot   JSONB,
            compliance_flags     TEXT[],
            duration_ms          INT,
            created_at           TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_encounter_audit_encounter_id
            ON encounter_audit (encounter_id);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_encounter_audit_created_at
            ON encounter_audit (created_at DESC);
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_encounter_audit_created_at;")
    op.execute("DROP INDEX IF EXISTS idx_encounter_audit_encounter_id;")
    op.execute("DROP TABLE IF EXISTS encounter_audit;")

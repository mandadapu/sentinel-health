"""Create triage_approvals table for the clinician approval workflow (ADR-4).

Stores triage decisions, confidence scores, and clinician review status
for the human-in-the-loop approval process.

Revision ID: 004
Revises: 003
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS triage_approvals (
            id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            encounter_id      UUID NOT NULL UNIQUE,
            triage_level      TEXT NOT NULL,
            confidence_score  DECIMAL(4, 3),
            reasoning_summary TEXT,
            status            TEXT NOT NULL DEFAULT 'pending'
                              CHECK (status IN ('pending', 'approved', 'rejected', 'escalated')),
            clinician_id      UUID,
            clinician_notes   TEXT,
            submitted_at      TIMESTAMPTZ DEFAULT NOW(),
            reviewed_at       TIMESTAMPTZ,
            sla_deadline      TIMESTAMPTZ
        );
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_triage_approvals_status_submitted
            ON triage_approvals (status, submitted_at);
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_triage_approvals_status_submitted;")
    op.execute("DROP TABLE IF EXISTS triage_approvals;")

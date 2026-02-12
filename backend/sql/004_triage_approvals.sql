-- Triage approval workflow (ADR-4)
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

CREATE INDEX IF NOT EXISTS idx_triage_approvals_status_submitted
    ON triage_approvals (status, submitted_at);

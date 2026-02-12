-- Encounter audit trail (ADR-4)
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

CREATE INDEX IF NOT EXISTS idx_encounter_audit_encounter_id
    ON encounter_audit (encounter_id);

CREATE INDEX IF NOT EXISTS idx_encounter_audit_created_at
    ON encounter_audit (created_at DESC);

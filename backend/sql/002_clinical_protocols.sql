-- Clinical protocols table for RAG retrieval (ADR-4)
CREATE TABLE IF NOT EXISTS clinical_protocols (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           TEXT NOT NULL,
    content         TEXT NOT NULL,
    embedding       vector(1536),
    source_type     TEXT NOT NULL CHECK (source_type IN ('hospital_curated', 'fhir_public')),
    specialty       TEXT,
    effective_date  DATE,
    expiry_date     DATE,
    version         INT DEFAULT 1,
    hospital_id     UUID,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- IVFFlat index for cosine similarity search on embeddings
CREATE INDEX IF NOT EXISTS idx_clinical_protocols_embedding
    ON clinical_protocols USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);

-- Composite index for filtered lookups
CREATE INDEX IF NOT EXISTS idx_clinical_protocols_source_specialty
    ON clinical_protocols (source_type, specialty);

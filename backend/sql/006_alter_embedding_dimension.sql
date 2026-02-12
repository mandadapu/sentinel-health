-- Migration: Change embedding dimension from 1536 to 1024 (Voyage-3 native)
-- Vertex AI text-embedding-004 (768-dim) is zero-padded to 1024 at the application layer.

-- Step 1: Drop the existing IVFFlat index (dimension-specific)
DROP INDEX IF EXISTS idx_clinical_protocols_embedding;

-- Step 2: Alter the embedding column dimension
ALTER TABLE clinical_protocols
    ALTER COLUMN embedding TYPE vector(1024)
    USING embedding::vector(1024);

-- Step 3: Recreate the IVFFlat index with new dimension
CREATE INDEX IF NOT EXISTS idx_clinical_protocols_embedding
    ON clinical_protocols USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);

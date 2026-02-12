"""Create clinical_protocols table for RAG retrieval (ADR-4).

Includes IVFFlat index for cosine similarity search and a composite index
for filtered lookups by source_type and specialty.

Revision ID: 002
Revises: 001
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
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
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_clinical_protocols_embedding
            ON clinical_protocols USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_clinical_protocols_source_specialty
            ON clinical_protocols (source_type, specialty);
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_clinical_protocols_source_specialty;")
    op.execute("DROP INDEX IF EXISTS idx_clinical_protocols_embedding;")
    op.execute("DROP TABLE IF EXISTS clinical_protocols;")

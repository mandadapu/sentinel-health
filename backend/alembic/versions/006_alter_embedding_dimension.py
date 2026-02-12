"""Change embedding column dimension from 1536 to 1024 (Voyage-3 native).

Vertex AI text-embedding-004 (768-dim) is zero-padded to 1024 at the
application layer, so all embeddings stored in the database are 1024-dim.
The IVFFlat index must be dropped and recreated because it is
dimension-specific.

Revision ID: 006
Revises: 005
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Drop the existing IVFFlat index (dimension-specific)
    op.execute("DROP INDEX IF EXISTS idx_clinical_protocols_embedding;")

    # Step 2: Alter the embedding column dimension
    op.execute("""
        ALTER TABLE clinical_protocols
            ALTER COLUMN embedding TYPE vector(1024)
            USING embedding::vector(1024);
    """)

    # Step 3: Recreate the IVFFlat index with new dimension
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_clinical_protocols_embedding
            ON clinical_protocols USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);
    """)


def downgrade() -> None:
    # Reverse: restore to 1536-dim
    op.execute("DROP INDEX IF EXISTS idx_clinical_protocols_embedding;")

    op.execute("""
        ALTER TABLE clinical_protocols
            ALTER COLUMN embedding TYPE vector(1536)
            USING embedding::vector(1536);
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_clinical_protocols_embedding
            ON clinical_protocols USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);
    """)

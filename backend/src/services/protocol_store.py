import logging
from typing import Any

import asyncpg

logger = logging.getLogger(__name__)


class ProtocolStore:
    """pgvector-backed clinical protocol retrieval (RAG)."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(self._dsn, min_size=2, max_size=10)
        async with self._pool.acquire() as conn:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        logger.info("ProtocolStore connected to Cloud SQL")

    async def retrieve(
        self,
        embedding: list[float],
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Retrieve similar clinical protocols using pgvector cosine distance.

        Uses layered retrieval: hospital-curated protocols first, then
        public FHIR guidelines as backfill (per ADR-4).
        """
        if not self._pool:
            return []

        rows = await self._pool.fetch(
            """
            SELECT title, content, source_type, specialty,
                   1 - (embedding <=> $1::vector) AS similarity
            FROM clinical_protocols
            WHERE (expiry_date IS NULL OR expiry_date > NOW())
            ORDER BY
                CASE WHEN source_type = 'hospital_curated' THEN 0 ELSE 1 END,
                embedding <=> $1::vector
            LIMIT $2
            """,
            str(embedding),
            top_k,
        )
        return [dict(r) for r in rows]

    async def health_check(self) -> bool:
        """Verify Cloud SQL connectivity with a lightweight query."""
        if not self._pool:
            return False
        try:
            async with self._pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception:
            return False

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
            logger.info("ProtocolStore connection closed")

"""Re-embed all clinical protocols with real embedding vectors.

Usage:
    python -m scripts.embed_protocols

Requires VOYAGE_API_KEY (or GCP credentials for Vertex AI fallback)
and CLOUDSQL_DSN environment variables.
"""

import asyncio
import logging

import asyncpg

from src.config import get_settings
from src.services.embedding_service import EmbeddingService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()

    if not settings.cloudsql_dsn:
        logger.error("CLOUDSQL_DSN is not set — cannot connect to database")
        return

    service = EmbeddingService(settings)
    conn = await asyncpg.connect(settings.cloudsql_dsn)

    try:
        rows = await conn.fetch("SELECT id, title, content FROM clinical_protocols")
        logger.info("Found %d protocols to embed", len(rows))

        for i, row in enumerate(rows):
            text = f"{row['title']}. {row['content']}"
            embedding = await service.embed(text)
            await conn.execute(
                "UPDATE clinical_protocols SET embedding = $1::vector, updated_at = NOW() WHERE id = $2",
                str(embedding),
                row["id"],
            )
            logger.info("Embedded %d/%d: %s", i + 1, len(rows), row["title"])

        logger.info("Done — all protocols re-embedded with %d-dim vectors.", settings.embedding_dimension)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

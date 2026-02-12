"""Generate real embeddings for clinical protocols.

Usage:
    VOYAGE_API_KEY=voy-xxx python -m scripts.generate_embeddings \
        --dsn postgresql://sentinel:localdev@localhost:5432/sentinel_health

Reads all clinical_protocols rows, generates embeddings via Voyage AI,
and updates the embedding column in-place.
"""

import argparse
import asyncio
import logging
import sys

import asyncpg

sys.path.insert(0, ".")
from src.config import Settings
from src.services.embedding_service import EmbeddingService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def main(dsn: str, batch_size: int = 5) -> None:
    settings = Settings()
    embedding_service = EmbeddingService(settings)

    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=3)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, title, content FROM clinical_protocols ORDER BY id"
        )
        logger.info("Found %d protocols to embed", len(rows))

        for i, row in enumerate(rows):
            text = f"{row['title']}\n\n{row['content']}"
            try:
                vector = await embedding_service.embed(text)
                await conn.execute(
                    "UPDATE clinical_protocols SET embedding = $1::vector WHERE id = $2",
                    str(vector),
                    row["id"],
                )
                logger.info(
                    "[%d/%d] Embedded: %s (dim=%d)",
                    i + 1,
                    len(rows),
                    row["title"][:60],
                    len(vector),
                )
            except Exception:
                logger.error("Failed to embed: %s", row["title"], exc_info=True)

            if (i + 1) % batch_size == 0:
                await asyncio.sleep(1.0)

    await pool.close()
    logger.info("Done. All protocols embedded.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate embeddings for clinical protocols"
    )
    parser.add_argument("--dsn", required=True, help="PostgreSQL connection string")
    parser.add_argument("--batch-size", type=int, default=5)
    args = parser.parse_args()
    asyncio.run(main(args.dsn, args.batch_size))

"""Embedding service with Voyage AI primary and Vertex AI fallback."""

import asyncio
import logging

from src.config import Settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Text embeddings via Voyage AI (primary) with Vertex AI fallback.

    Both providers normalize to a fixed dimension (default 1024) for
    pgvector storage. Voyage-3 produces 1024 natively; Vertex AI
    text-embedding-004 produces 768 and is zero-padded to match.
    """

    def __init__(self, settings: Settings) -> None:
        self._dimension = settings.embedding_dimension
        self._primary_model = settings.embedding_model
        self._fallback_model = settings.embedding_fallback_model
        self._gcp_project = settings.gcp_project_id
        self._gcp_location = settings.vertex_ai_location
        self._voyage_api_key = settings.voyage_api_key

        # Lazy-init clients
        self._voyage_client = None
        self._vertex_initialized = False

    async def embed(self, text: str) -> list[float]:
        """Generate a text embedding of fixed dimension.

        Tries Voyage AI first, falls back to Vertex AI on failure.
        Raises on total failure (caller handles graceful degradation).
        """
        try:
            return await self._embed_voyage(text)
        except Exception:
            logger.warning(
                "Voyage AI embedding failed — falling back to Vertex AI",
                exc_info=True,
            )

        try:
            return await self._embed_vertex(text)
        except Exception:
            logger.error("Both embedding providers failed", exc_info=True)
            raise

    async def _embed_voyage(self, text: str) -> list[float]:
        """Call Voyage AI async endpoint."""
        if self._voyage_client is None:
            import voyageai

            self._voyage_client = voyageai.AsyncClient(api_key=self._voyage_api_key)

        result = await self._voyage_client.embed(
            texts=[text],
            model=self._primary_model,
            input_type="query",
        )
        vector = result.embeddings[0]

        if len(vector) != self._dimension:
            vector = self._normalize_dimension(vector)

        return vector

    async def _embed_vertex(self, text: str) -> list[float]:
        """Call Vertex AI text-embedding-004 (sync SDK wrapped in executor)."""
        if not self._vertex_initialized:
            import vertexai

            vertexai.init(project=self._gcp_project, location=self._gcp_location)
            self._vertex_initialized = True

        from vertexai.language_models import TextEmbeddingModel

        model = TextEmbeddingModel.from_pretrained(self._fallback_model)

        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            lambda: model.get_embeddings([text]),
        )
        vector = embeddings[0].values

        if len(vector) != self._dimension:
            vector = self._normalize_dimension(vector)

        return vector

    def _normalize_dimension(self, vector: list[float]) -> list[float]:
        """Pad or truncate vector to target dimension."""
        current = len(vector)
        if current < self._dimension:
            return list(vector) + [0.0] * (self._dimension - current)
        if current > self._dimension:
            return list(vector[: self._dimension])
        return list(vector)

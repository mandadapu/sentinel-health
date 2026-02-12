"""Tests for the EmbeddingService with Voyage AI primary and Vertex AI fallback."""

import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.config import Settings
from src.services.embedding_service import EmbeddingService


@pytest.fixture
def embedding_settings():
    return Settings(
        gcp_project_id="test-project",
        env="test",
        anthropic_api_key="test-key",
        embedding_model="voyage-3",
        embedding_dimension=1024,
        embedding_fallback_model="text-embedding-004",
        voyage_api_key="test-voyage-key",
        vertex_ai_location="us-central1",
    )


@pytest.fixture
def service(embedding_settings):
    return EmbeddingService(embedding_settings)


@pytest.fixture
def mock_voyage_module():
    """Mock the voyageai module for tests without the real SDK installed."""
    mock_result = MagicMock()
    mock_result.embeddings = [[0.5] * 1024]

    mock_client = AsyncMock()
    mock_client.embed = AsyncMock(return_value=mock_result)

    mock_module = ModuleType("voyageai")
    mock_module.AsyncClient = MagicMock(return_value=mock_client)

    with patch.dict(sys.modules, {"voyageai": mock_module}):
        yield mock_client, mock_result


@pytest.fixture
def mock_vertex_modules():
    """Mock the vertexai modules for tests without the real SDK installed."""
    mock_embedding = MagicMock()
    mock_embedding.values = [0.3] * 768

    mock_model = MagicMock()
    mock_model.get_embeddings = MagicMock(return_value=[mock_embedding])

    mock_vertexai = ModuleType("vertexai")
    mock_vertexai.init = MagicMock()

    mock_lang = ModuleType("vertexai.language_models")
    mock_lang.TextEmbeddingModel = MagicMock()
    mock_lang.TextEmbeddingModel.from_pretrained = MagicMock(return_value=mock_model)

    with patch.dict(
        sys.modules,
        {"vertexai": mock_vertexai, "vertexai.language_models": mock_lang},
    ):
        yield mock_model, mock_embedding


class TestVoyagePrimary:
    @pytest.mark.asyncio
    async def test_voyage_returns_vector(self, service, mock_voyage_module):
        """Voyage AI returns a 1024-dim vector successfully."""
        mock_client, _ = mock_voyage_module

        vector = await service.embed("test text")

        assert len(vector) == 1024
        mock_client.embed.assert_called_once_with(
            texts=["test text"],
            model="voyage-3",
            input_type="query",
        )

    @pytest.mark.asyncio
    async def test_voyage_only_called_once_on_success(
        self, service, mock_voyage_module, mock_vertex_modules
    ):
        """When Voyage succeeds, Vertex AI is never called."""
        _, _ = mock_voyage_module
        mock_vertex_model, _ = mock_vertex_modules

        await service.embed("test text")

        mock_vertex_model.get_embeddings.assert_not_called()


class TestVertexFallback:
    @pytest.mark.asyncio
    async def test_falls_back_to_vertex_on_voyage_failure(
        self, service, mock_vertex_modules
    ):
        """When Voyage fails, Vertex AI is used as fallback."""
        mock_client = AsyncMock()
        mock_client.embed = AsyncMock(side_effect=Exception("Voyage down"))

        mock_voyage = ModuleType("voyageai")
        mock_voyage.AsyncClient = MagicMock(return_value=mock_client)

        with patch.dict(sys.modules, {"voyageai": mock_voyage}):
            vector = await service.embed("test text")

        # Vertex 768 → padded to 1024
        assert len(vector) == 1024
        assert vector[0] == 0.3
        assert vector[767] == 0.3
        assert vector[768] == 0.0
        assert vector[1023] == 0.0

    @pytest.mark.asyncio
    async def test_both_fail_raises(self, service):
        """When both providers fail, exception propagates."""
        mock_voyage_client = AsyncMock()
        mock_voyage_client.embed = AsyncMock(side_effect=Exception("Voyage down"))

        mock_voyage = ModuleType("voyageai")
        mock_voyage.AsyncClient = MagicMock(return_value=mock_voyage_client)

        mock_vertex_model = MagicMock()
        mock_vertex_model.get_embeddings = MagicMock(side_effect=Exception("Vertex down"))

        mock_vertexai = ModuleType("vertexai")
        mock_vertexai.init = MagicMock()

        mock_lang = ModuleType("vertexai.language_models")
        mock_lang.TextEmbeddingModel = MagicMock()
        mock_lang.TextEmbeddingModel.from_pretrained = MagicMock(return_value=mock_vertex_model)

        with (
            patch.dict(
                sys.modules,
                {"voyageai": mock_voyage, "vertexai": mock_vertexai, "vertexai.language_models": mock_lang},
            ),
            pytest.raises(Exception, match="Vertex down"),
        ):
            await service.embed("test text")


class TestDimensionNormalization:
    def test_pads_short_vector(self, service):
        """Vectors shorter than target are zero-padded."""
        short = [1.0] * 768
        result = service._normalize_dimension(short)
        assert len(result) == 1024
        assert result[:768] == [1.0] * 768
        assert result[768:] == [0.0] * 256

    def test_truncates_long_vector(self, service):
        """Vectors longer than target are truncated."""
        long = [1.0] * 1536
        result = service._normalize_dimension(long)
        assert len(result) == 1024

    def test_passthrough_correct_dimension(self, service):
        """Vectors matching target dimension pass through unchanged."""
        exact = [0.5] * 1024
        result = service._normalize_dimension(exact)
        assert result == exact

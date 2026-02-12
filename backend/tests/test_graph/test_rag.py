"""Tests for the RAG retriever node and protocol store integration."""

from unittest.mock import AsyncMock

import pytest

from src.graph.nodes.rag_retriever import rag_retriever_node
from src.graph.pipeline import build_pipeline
from src.routing.classifier import ClinicalClassifier
from src.routing.router import ModelRouter


def _build_base_state(encounter_text: str = "Patient has a cough"):
    return {
        "raw_input": encounter_text,
        "encounter_id": "enc-rag-001",
        "patient_id": "pat-001",
        "audit_trail": [],
        "compliance_flags": [],
        "circuit_breaker_tripped": False,
        "error": None,
    }


@pytest.fixture
def mock_protocol_store():
    store = AsyncMock()
    store.retrieve.return_value = [
        {
            "title": "Respiratory Infection Protocol",
            "content": "For febrile patients with cough >3 days, order CXR and CBC.",
            "source_type": "hospital_curated",
            "specialty": "emergency",
            "similarity": 0.89,
        },
        {
            "title": "FHIR Cough Assessment Guideline",
            "content": "Evaluate for pneumonia indicators: fever, productive cough, tachypnea.",
            "source_type": "fhir_public",
            "specialty": "pulmonology",
            "similarity": 0.75,
        },
    ]
    return store


class TestRAGRetrieverNode:
    @pytest.mark.asyncio
    async def test_retriever_returns_empty_when_no_store(self, mock_embedding_service):
        """When protocol_store is None, returns empty rag_context."""
        state = _build_base_state()
        state["clinical_context"] = {
            "chief_complaint": "persistent cough",
            "symptoms": [{"description": "cough", "onset": "3 days", "severity": "moderate"}],
        }

        result = await rag_retriever_node(
            state, protocol_store=None, embedding_service=mock_embedding_service
        )

        assert result["rag_context"] == []

    @pytest.mark.asyncio
    async def test_retriever_returns_empty_when_no_embedding_service(self, mock_protocol_store):
        """When embedding_service is None, returns empty rag_context."""
        state = _build_base_state()
        state["clinical_context"] = {
            "chief_complaint": "persistent cough",
            "symptoms": [],
        }

        result = await rag_retriever_node(
            state, protocol_store=mock_protocol_store, embedding_service=None
        )

        assert result["rag_context"] == []

    @pytest.mark.asyncio
    async def test_retriever_returns_empty_when_no_clinical_context(
        self, mock_embedding_service, mock_protocol_store
    ):
        """When clinical_context has no useful query text, returns empty."""
        state = _build_base_state()
        state["clinical_context"] = {"chief_complaint": "", "symptoms": []}

        result = await rag_retriever_node(
            state,
            protocol_store=mock_protocol_store,
            embedding_service=mock_embedding_service,
        )

        assert result["rag_context"] == []
        mock_protocol_store.retrieve.assert_not_called()

    @pytest.mark.asyncio
    async def test_retriever_fetches_protocols(self, mock_embedding_service, mock_protocol_store):
        """When store and service are available, retrieves protocols."""
        state = _build_base_state()
        state["clinical_context"] = {
            "chief_complaint": "persistent cough for 3 days",
            "symptoms": [
                {"description": "cough", "onset": "3 days", "severity": "moderate"},
                {"description": "fever", "onset": "2 days", "severity": "mild"},
            ],
        }

        result = await rag_retriever_node(
            state,
            protocol_store=mock_protocol_store,
            embedding_service=mock_embedding_service,
        )

        assert len(result["rag_context"]) == 2
        assert result["rag_context"][0]["title"] == "Respiratory Infection Protocol"
        assert result["rag_context"][1]["source_type"] == "fhir_public"

        # Verify embed was called with combined query
        mock_embedding_service.embed.assert_called_once()
        embed_arg = mock_embedding_service.embed.call_args[0][0]
        assert "persistent cough" in embed_arg
        assert "fever" in embed_arg

        # Verify retrieve was called with embedding and top_k
        mock_protocol_store.retrieve.assert_called_once()

    @pytest.mark.asyncio
    async def test_retriever_handles_embed_failure(
        self, mock_embedding_service, mock_protocol_store
    ):
        """When embedding fails, returns empty rag_context gracefully."""
        state = _build_base_state()
        state["clinical_context"] = {
            "chief_complaint": "chest pain",
            "symptoms": [{"description": "chest pain", "onset": "1 hour", "severity": "severe"}],
        }

        mock_embedding_service.embed = AsyncMock(side_effect=Exception("Embedding API error"))

        result = await rag_retriever_node(
            state,
            protocol_store=mock_protocol_store,
            embedding_service=mock_embedding_service,
        )

        assert result["rag_context"] == []
        mock_protocol_store.retrieve.assert_not_called()

    @pytest.mark.asyncio
    async def test_retriever_handles_store_failure(
        self, mock_embedding_service, mock_protocol_store
    ):
        """When protocol store query fails, returns empty rag_context gracefully."""
        state = _build_base_state()
        state["clinical_context"] = {
            "chief_complaint": "headache",
            "symptoms": [{"description": "headache", "onset": "2 days", "severity": "moderate"}],
        }

        mock_protocol_store.retrieve.side_effect = Exception("Database connection lost")

        result = await rag_retriever_node(
            state,
            protocol_store=mock_protocol_store,
            embedding_service=mock_embedding_service,
        )

        assert result["rag_context"] == []


class TestPipelineWithRAG:
    @pytest.mark.asyncio
    async def test_pipeline_without_protocol_store(
        self,
        mock_anthropic,
        mock_audit_writer,
        settings,
        sample_extracted_data,
        sample_triage_decision,
        sample_sentinel_response,
    ):
        """Pipeline works without protocol_store — RAG node returns empty context."""
        classify_response = mock_anthropic._make_response(
            {"category": "symptom_assessment", "confidence": 0.88, "reason": "Cough"}
        )
        extract_response = mock_anthropic._make_response(
            sample_extracted_data, model="claude-sonnet-4-5-20250929"
        )
        reason_response = mock_anthropic._make_response(
            sample_triage_decision, model="claude-sonnet-4-5-20250929"
        )
        sentinel_response = mock_anthropic._make_response(
            sample_sentinel_response
        )

        mock_anthropic.complete.side_effect = [
            classify_response,
            extract_response,
            reason_response,
            sentinel_response,
        ]

        classifier = ClinicalClassifier(mock_anthropic, "claude-haiku-4-5-20241022")
        router = ModelRouter(min_confidence=0.70)

        pipeline = build_pipeline(
            anthropic_client=mock_anthropic,
            audit_writer=mock_audit_writer,
            classifier=classifier,
            router=router,
            settings=settings,
        )

        initial_state = {
            "raw_input": "45-year-old with cough for 3 days",
            "encounter_id": "enc-rag-pipeline-001",
            "patient_id": "pat-001",
            "audit_trail": [],
            "compliance_flags": [],
            "circuit_breaker_tripped": False,
            "error": None,
        }

        result = await pipeline.ainvoke(initial_state)

        # Pipeline completes normally
        assert result["triage_decision"]["level"] == "Semi-Urgent"
        assert result["sentinel_check"]["passed"] is True

        # RAG context should be empty (no protocol store)
        assert result.get("rag_context", []) == []

        # LLM called 4 times (classifier + extractor + reasoner + sentinel)
        assert mock_anthropic.complete.call_count == 4

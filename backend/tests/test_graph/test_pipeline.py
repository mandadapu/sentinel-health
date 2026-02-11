"""Integration tests for the LangGraph triage pipeline with mocked services."""

import json
from unittest.mock import AsyncMock

import pytest

from src.graph.nodes.extractor import extractor_node
from src.graph.nodes.reasoner import reasoner_node
from src.graph.nodes.sentinel import sentinel_node
from src.graph.pipeline import build_pipeline
from src.routing.classifier import ClinicalClassifier
from src.routing.router import ModelRouter


@pytest.fixture
def mock_classifier(mock_anthropic):
    classifier = ClinicalClassifier(mock_anthropic, "claude-haiku-4-5-20241022")
    mock_anthropic.complete.return_value = mock_anthropic._make_response(
        {"category": "symptom_assessment", "confidence": 0.88, "reason": "Cough with fever"}
    )
    return classifier


@pytest.fixture
def mock_router():
    return ModelRouter(min_confidence=0.70)


def _build_base_state(encounter_text: str = "Patient has a cough"):
    return {
        "raw_input": encounter_text,
        "encounter_id": "enc-001",
        "patient_id": "pat-001",
        "audit_trail": [],
        "compliance_flags": [],
        "circuit_breaker_tripped": False,
        "error": None,
    }


class TestExtractorNode:
    @pytest.mark.asyncio
    async def test_extractor_extracts_data(
        self, mock_anthropic, mock_audit_writer, sample_extracted_data
    ):
        mock_anthropic.complete.return_value = mock_anthropic._make_response(
            sample_extracted_data
        )
        state = _build_base_state()
        state["routing_metadata"] = {
            "category": "symptom_assessment",
            "classifier_confidence": 0.88,
            "selected_model": "claude-sonnet-4-5-20250929",
            "escalation_reason": None,
            "safety_override": False,
        }

        result = await extractor_node(
            state, anthropic_client=mock_anthropic, audit_writer=mock_audit_writer
        )

        assert "fhir_data" in result
        assert result["fhir_data"]["vitals"]["heart_rate"] == 88
        assert len(result["audit_trail"]) == 1
        assert result["audit_trail"][0]["node"] == "extractor"
        mock_audit_writer.write_node_audit.assert_called_once()

    @pytest.mark.asyncio
    async def test_extractor_uses_routed_model(
        self, mock_anthropic, mock_audit_writer, sample_extracted_data
    ):
        mock_anthropic.complete.return_value = mock_anthropic._make_response(
            sample_extracted_data, model="claude-opus-4-6-20250929"
        )
        state = _build_base_state()
        state["routing_metadata"] = {
            "category": "critical_emergency",
            "classifier_confidence": 0.95,
            "selected_model": "claude-opus-4-6-20250929",
            "escalation_reason": None,
            "safety_override": True,
        }

        result = await extractor_node(
            state, anthropic_client=mock_anthropic, audit_writer=mock_audit_writer
        )

        mock_anthropic.complete.assert_called_once()
        call_kwargs = mock_anthropic.complete.call_args
        assert call_kwargs.kwargs["model"] == "claude-opus-4-6-20250929"


class TestReasonerNode:
    @pytest.mark.asyncio
    async def test_reasoner_produces_decision(
        self, mock_anthropic, mock_audit_writer, sample_extracted_data, sample_triage_decision
    ):
        mock_anthropic.complete.return_value = mock_anthropic._make_response(
            sample_triage_decision
        )
        state = _build_base_state()
        state["routing_metadata"] = {
            "category": "symptom_assessment",
            "classifier_confidence": 0.88,
            "selected_model": "claude-sonnet-4-5-20250929",
            "escalation_reason": None,
            "safety_override": False,
        }
        state["clinical_context"] = sample_extracted_data

        result = await reasoner_node(
            state, anthropic_client=mock_anthropic, audit_writer=mock_audit_writer
        )

        assert result["triage_decision"]["level"] == "Semi-Urgent"
        assert result["triage_decision"]["confidence"] == 0.82
        assert "model_used" in result["triage_decision"]
        assert len(result["audit_trail"]) == 1
        assert result["audit_trail"][0]["node"] == "reasoner"


class TestSentinelNode:
    @pytest.mark.asyncio
    async def test_sentinel_passes_good_decision(
        self,
        mock_anthropic,
        mock_audit_writer,
        settings,
        sample_extracted_data,
        sample_triage_decision,
        sample_sentinel_response,
    ):
        mock_anthropic.complete.return_value = mock_anthropic._make_response(
            sample_sentinel_response
        )
        state = _build_base_state()
        state["routing_metadata"] = {
            "category": "symptom_assessment",
            "classifier_confidence": 0.88,
            "selected_model": "claude-sonnet-4-5-20250929",
            "escalation_reason": None,
            "safety_override": False,
        }
        state["clinical_context"] = sample_extracted_data
        state["triage_decision"] = sample_triage_decision

        result = await sentinel_node(
            state,
            anthropic_client=mock_anthropic,
            audit_writer=mock_audit_writer,
            settings=settings,
        )

        assert result["sentinel_check"]["passed"] is True
        assert result["circuit_breaker_tripped"] is False
        assert result["sentinel_check"]["hallucination_score"] == 0.05

    @pytest.mark.asyncio
    async def test_sentinel_trips_circuit_breaker_on_high_hallucination(
        self,
        mock_anthropic,
        mock_audit_writer,
        settings,
        sample_extracted_data,
        sample_triage_decision,
    ):
        bad_response = {
            "hallucination_score": 0.30,
            "confidence_assessment": 0.90,
            "vitals_consistent": True,
            "medication_safe": True,
            "issues_found": ["Referenced non-existent lab results"],
        }
        mock_anthropic.complete.return_value = mock_anthropic._make_response(
            bad_response
        )
        state = _build_base_state()
        state["routing_metadata"] = {
            "category": "symptom_assessment",
            "classifier_confidence": 0.88,
            "selected_model": "claude-sonnet-4-5-20250929",
            "escalation_reason": None,
            "safety_override": False,
        }
        state["clinical_context"] = sample_extracted_data
        state["triage_decision"] = sample_triage_decision

        result = await sentinel_node(
            state,
            anthropic_client=mock_anthropic,
            audit_writer=mock_audit_writer,
            settings=settings,
        )

        assert result["sentinel_check"]["passed"] is False
        assert result["circuit_breaker_tripped"] is True
        assert any("Hallucination" in r for r in result["sentinel_check"]["failure_reasons"])

    @pytest.mark.asyncio
    async def test_sentinel_trips_on_low_confidence(
        self,
        mock_anthropic,
        mock_audit_writer,
        settings,
        sample_extracted_data,
        sample_triage_decision,
    ):
        low_conf_response = {
            "hallucination_score": 0.05,
            "confidence_assessment": 0.60,
            "vitals_consistent": True,
            "medication_safe": True,
            "issues_found": ["Insufficient evidence for triage level"],
        }
        mock_anthropic.complete.return_value = mock_anthropic._make_response(
            low_conf_response
        )
        state = _build_base_state()
        state["routing_metadata"] = {
            "category": "symptom_assessment",
            "classifier_confidence": 0.88,
            "selected_model": "claude-sonnet-4-5-20250929",
            "escalation_reason": None,
            "safety_override": False,
        }
        state["clinical_context"] = sample_extracted_data
        state["triage_decision"] = sample_triage_decision

        result = await sentinel_node(
            state,
            anthropic_client=mock_anthropic,
            audit_writer=mock_audit_writer,
            settings=settings,
        )

        assert result["circuit_breaker_tripped"] is True
        assert any("Confidence" in r for r in result["sentinel_check"]["failure_reasons"])


class TestFullPipeline:
    @pytest.mark.asyncio
    async def test_pipeline_end_to_end(
        self,
        mock_anthropic,
        mock_audit_writer,
        settings,
        sample_extracted_data,
        sample_triage_decision,
        sample_sentinel_response,
    ):
        """Full pipeline: classify → extract → reason → sentinel."""
        # Set up sequential responses for each LLM call
        classify_response = mock_anthropic._make_response(
            {"category": "symptom_assessment", "confidence": 0.88, "reason": "Cough with fever"}
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
            "raw_input": "45-year-old with persistent cough for 3 days, temp 38.2C",
            "encounter_id": "enc-integration-001",
            "patient_id": "pat-001",
            "audit_trail": [],
            "compliance_flags": [],
            "circuit_breaker_tripped": False,
            "error": None,
        }

        result = await pipeline.ainvoke(initial_state)

        # Verify routing happened
        assert result["routing_metadata"]["category"] == "symptom_assessment"
        assert result["routing_metadata"]["selected_model"] == "claude-sonnet-4-5-20250929"

        # Verify extraction
        assert result["fhir_data"]["vitals"]["heart_rate"] == 88

        # Verify triage decision
        assert result["triage_decision"]["level"] == "Semi-Urgent"
        assert result["triage_decision"]["confidence"] == 0.82

        # Verify sentinel
        assert result["sentinel_check"]["passed"] is True
        assert result["circuit_breaker_tripped"] is False

        # Verify 3 audit entries (extractor, reasoner, sentinel)
        assert len(result["audit_trail"]) == 3
        nodes_audited = [e["node"] for e in result["audit_trail"]]
        assert nodes_audited == ["extractor", "reasoner", "sentinel"]

        # Verify LLM was called 4 times (classifier + 3 nodes)
        assert mock_anthropic.complete.call_count == 4

    @pytest.mark.asyncio
    async def test_pipeline_with_critical_keyword_routes_to_opus(
        self,
        mock_anthropic,
        mock_audit_writer,
        settings,
        sample_extracted_data,
        sample_triage_decision,
        sample_sentinel_response,
    ):
        """Critical keyword in input → Opus for all nodes."""
        classify_response = mock_anthropic._make_response(
            {"category": "acute_presentation", "confidence": 0.92, "reason": "Chest pain"}
        )
        extract_response = mock_anthropic._make_response(
            sample_extracted_data, model="claude-opus-4-6-20250929"
        )
        reason_response = mock_anthropic._make_response(
            sample_triage_decision, model="claude-opus-4-6-20250929"
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
            "raw_input": "Patient with severe chest pain radiating to left arm",
            "encounter_id": "enc-critical-001",
            "patient_id": "pat-002",
            "audit_trail": [],
            "compliance_flags": [],
            "circuit_breaker_tripped": False,
            "error": None,
        }

        result = await pipeline.ainvoke(initial_state)

        # Critical keyword → Opus
        assert result["routing_metadata"]["selected_model"] == "claude-opus-4-6-20250929"
        assert result["routing_metadata"]["safety_override"] is True

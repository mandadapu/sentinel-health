import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.config import Settings


@pytest.fixture
def settings():
    return Settings(
        gcp_project_id="test-project",
        env="test",
        anthropic_api_key="test-key",
        firestore_collection="test_sessions",
        hallucination_threshold=0.15,
        confidence_threshold=0.85,
        min_routing_confidence=0.70,
    )


@pytest.fixture
def mock_anthropic():
    """AnthropicClient mock that returns configurable LLM responses."""
    client = AsyncMock()

    def _make_response(content: str | dict, model: str = "claude-haiku-4-5-20241022"):
        if isinstance(content, dict):
            content = json.dumps(content)
        return {
            "content": content,
            "model": model,
            "tokens": {"in": 100, "out": 50},
            "cost_usd": 0.00015,
            "duration_ms": 200,
            "stop_reason": "end_turn",
        }

    client._make_response = _make_response
    return client


@pytest.fixture
def mock_firestore():
    svc = AsyncMock()
    svc.write_audit.return_value = "test_sessions/enc-001/audit/extractor"
    svc.write_session.return_value = "test_sessions/enc-001"
    return svc


@pytest.fixture
def mock_pubsub():
    return AsyncMock()


@pytest.fixture
def mock_audit_writer(mock_firestore, mock_pubsub):
    from src.audit.writer import AuditWriter

    writer = AuditWriter(mock_firestore, mock_pubsub)
    # Patch write_node_audit to avoid real Firestore/PubSub
    writer.write_node_audit = AsyncMock(
        return_value="test_sessions/enc-001/audit/test"
    )
    writer.publish_triage_completed = AsyncMock()
    return writer


@pytest.fixture
def sample_encounter_text():
    return (
        "45-year-old male presents with persistent cough for 3 days. "
        "Temperature 38.2C, blood pressure 130/85, heart rate 88. "
        "History of type 2 diabetes. Currently on metformin 500mg BID. "
        "No known drug allergies. Reports mild chest discomfort with coughing."
    )


@pytest.fixture
def sample_extracted_data():
    return {
        "vitals": {
            "heart_rate": 88,
            "blood_pressure": "130/85",
            "temperature": 38.2,
            "respiratory_rate": None,
            "spo2": None,
        },
        "symptoms": [
            {
                "description": "persistent cough",
                "onset": "3 days",
                "severity": "moderate",
            },
            {
                "description": "mild chest discomfort with coughing",
                "onset": "unspecified",
                "severity": "mild",
            },
        ],
        "medications": [
            {"name": "metformin", "dose": "500mg", "frequency": "BID"}
        ],
        "history": {
            "conditions": ["type 2 diabetes"],
            "allergies": [],
            "surgeries": [],
        },
        "chief_complaint": "persistent cough for 3 days",
        "assessment_notes": "Febrile patient with cough and mild chest discomfort",
    }


@pytest.fixture
def sample_triage_decision():
    return {
        "level": "Semi-Urgent",
        "confidence": 0.82,
        "reasoning_summary": "Febrile patient with cough and chest discomfort. Diabetic comorbidity increases risk.",
        "recommended_actions": [
            "Chest X-ray",
            "CBC and CRP",
            "Blood glucose check",
        ],
        "key_findings": [
            "Fever 38.2C",
            "Productive cough 3 days",
            "Diabetic comorbidity",
        ],
    }


@pytest.fixture
def sample_sentinel_response():
    return {
        "hallucination_score": 0.05,
        "confidence_assessment": 0.90,
        "vitals_consistent": True,
        "medication_safe": True,
        "issues_found": [],
    }


@pytest.fixture
def mock_embedding_service():
    """EmbeddingService mock that returns configurable embeddings."""
    service = AsyncMock()
    service.embed = AsyncMock(return_value=[0.1] * 1024)
    return service


@pytest.fixture
def mock_sidecar_client():
    """SidecarClient mock that returns pass-through validation results."""
    from src.services.sidecar_client import SidecarValidationResult

    client = AsyncMock()

    def _make_result(content: str = "", flags: list[str] | None = None):
        return SidecarValidationResult(
            {
                "validated": True,
                "content": content,
                "compliance_flags": flags or ["PII_CLEAN"],
                "redactions": [],
                "errors": [],
                "should_retry": False,
                "latency_ms": 1.0,
            }
        )

    client._make_result = _make_result
    # Default: return pass-through result with the content from the call
    client.validate = AsyncMock(
        side_effect=lambda content, **kwargs: _make_result(content)
    )
    return client

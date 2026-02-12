from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api import triage
from src.main import app


@pytest.fixture
def mock_pipeline(sample_extracted_data, sample_triage_decision, sample_sentinel_response):
    """Mock compiled LangGraph pipeline returning full AgentState."""
    pipeline = AsyncMock()
    pipeline.ainvoke.return_value = {
        "encounter_id": "enc-001",
        "patient_id": "pat-001",
        "raw_input": "45-year-old male with persistent cough",
        "routing_metadata": {
            "category": "symptom_assessment",
            "classifier_confidence": 0.92,
            "selected_model": "claude-sonnet-4-5-20250929",
            "escalation_reason": None,
            "safety_override": False,
        },
        "fhir_data": sample_extracted_data,
        "triage_decision": {
            **sample_triage_decision,
            "model_used": "claude-sonnet-4-5-20250929",
            "routing_reason": "symptom_assessment",
        },
        "sentinel_check": {
            "passed": True,
            "hallucination_score": sample_sentinel_response["hallucination_score"],
            "confidence_score": sample_sentinel_response["confidence_assessment"],
            "vitals_consistent": True,
            "medication_safe": True,
            "issues_found": [],
        },
        "audit_trail": [
            {
                "encounter_id": "enc-001",
                "node": "sentinel",
                "model": "claude-haiku-4-5-20241022",
                "tokens": {"in": 100, "out": 50},
                "cost_usd": 0.00015,
                "duration_ms": 200,
                "audit_ref": "test_sessions/enc-001/audit/sentinel",
            },
        ],
        "compliance_flags": ["PII_REDACTED", "FHIR_VALID"],
        "circuit_breaker_tripped": False,
        "error": None,
    }
    return pipeline


@pytest_asyncio.fixture
async def client(mock_pipeline, mock_audit_writer, mock_firestore):
    triage.set_dependencies(mock_pipeline, mock_audit_writer, mock_firestore)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    triage.set_dependencies(None, None, None)

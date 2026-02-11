"""Tests for the audit consumer endpoints and transform logic."""

import base64
import json

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.transform import transform_audit_event


def _encode_message(data: dict) -> str:
    return base64.b64encode(json.dumps(data).encode()).decode()


@pytest.fixture
def sample_audit_event():
    return {
        "encounter_id": "enc-001",
        "node": "extractor",
        "model": "claude-sonnet-4-5-20250929",
        "routing_decision": {
            "category": "symptom_assessment",
            "confidence": 0.92,
        },
        "tokens": {"in": 1200, "out": 450},
        "cost_usd": 0.0034,
        "compliance_flags": ["PII_REDACTED", "FHIR_VALID"],
        "sentinel_check": {
            "hallucination_score": 0.05,
            "confidence_score": 0.91,
            "circuit_breaker_tripped": False,
        },
        "duration_ms": 1540,
        "timestamp": "2025-01-15T10:30:00Z",
    }


@pytest.fixture
async def client(mock_bigquery):
    app.state.bigquery = mock_bigquery
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestHealth:
    async def test_health_returns_200(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"


class TestPushAuditEvent:
    async def test_processes_valid_audit_event(self, client, mock_bigquery, sample_audit_event):
        envelope = {
            "message": {
                "data": _encode_message(sample_audit_event),
                "message_id": "msg-001",
                "publish_time": "2025-01-15T10:30:00Z",
            },
            "subscription": "projects/sentinel-health-dev/subscriptions/audit-events-sub",
        }

        response = await client.post("/push/audit-event", json=envelope)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["encounter_id"] == "enc-001"

        mock_bigquery.insert.assert_called_once()
        row = mock_bigquery.insert.call_args[0][0]
        assert row["encounter_id"] == "enc-001"
        assert row["node_name"] == "extractor"
        assert row["model_used"] == "claude-sonnet-4-5-20250929"
        assert row["input_tokens"] == 1200
        assert row["output_tokens"] == 450

    async def test_rejects_invalid_payload(self, client):
        envelope = {
            "message": {
                "data": "not-base64!!!",
                "message_id": "msg-002",
                "publish_time": "",
            },
            "subscription": "",
        }

        response = await client.post("/push/audit-event", json=envelope)
        assert response.status_code == 400

    async def test_rejects_missing_encounter_id(self, client):
        message = {"node": "extractor", "model": "claude-sonnet-4-5-20250929"}
        envelope = {
            "message": {
                "data": _encode_message(message),
                "message_id": "msg-003",
                "publish_time": "",
            },
            "subscription": "",
        }

        response = await client.post("/push/audit-event", json=envelope)
        assert response.status_code == 400
        assert "encounter_id" in response.json()["detail"]


class TestTransform:
    def test_full_transform(self, sample_audit_event):
        row = transform_audit_event(sample_audit_event)
        assert row["encounter_id"] == "enc-001"
        assert row["node_name"] == "extractor"
        assert row["model_used"] == "claude-sonnet-4-5-20250929"
        assert row["routing_category"] == "symptom_assessment"
        assert row["routing_confidence"] == 0.92
        assert row["input_tokens"] == 1200
        assert row["output_tokens"] == 450
        assert row["cost_usd"] == 0.0034
        assert row["compliance_flags"] == ["PII_REDACTED", "FHIR_VALID"]
        assert row["sentinel_hallucination_score"] == 0.05
        assert row["sentinel_confidence_score"] == 0.91
        assert row["circuit_breaker_tripped"] is False
        assert row["duration_ms"] == 1540
        assert row["created_at"] == "2025-01-15T10:30:00Z"
        # reasoning_snapshot is the full doc as JSON
        snapshot = json.loads(row["reasoning_snapshot"])
        assert snapshot["encounter_id"] == "enc-001"

    def test_transform_minimal_event(self):
        doc = {
            "encounter_id": "enc-002",
            "timestamp": "2025-01-15T11:00:00Z",
        }
        row = transform_audit_event(doc)
        assert row["encounter_id"] == "enc-002"
        assert row["node_name"] == ""
        assert row["model_used"] == ""
        assert row["routing_category"] is None
        assert row["input_tokens"] is None
        assert row["compliance_flags"] == []
        assert row["sentinel_hallucination_score"] is None
        assert row["circuit_breaker_tripped"] is None

    def test_transform_null_sentinel(self):
        doc = {
            "encounter_id": "enc-003",
            "sentinel_check": None,
            "timestamp": "2025-01-15T11:00:00Z",
        }
        row = transform_audit_event(doc)
        assert row["sentinel_hallucination_score"] is None
        assert row["sentinel_confidence_score"] is None
        assert row["circuit_breaker_tripped"] is None

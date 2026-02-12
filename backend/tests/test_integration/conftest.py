"""Fixtures for integration tests that bridge the backend and approval-worker services."""

import base64
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

# ---------------------------------------------------------------------------
# Path manipulation — make approval-worker and audit-consumer importable
# ---------------------------------------------------------------------------
_repo_root = Path(__file__).resolve().parents[3]

_approval_worker_path = str(_repo_root / "approval-worker")
if _approval_worker_path not in sys.path:
    sys.path.insert(0, _approval_worker_path)

_audit_consumer_path = str(_repo_root / "audit-consumer")
if _audit_consumer_path not in sys.path:
    sys.path.insert(0, _audit_consumer_path)

from src.main import app as approval_app  # noqa: E402
from src.services.firestore import ApprovalFirestore  # noqa: E402
from src.services.pubsub import ApprovalPubSub  # noqa: E402


# ---------------------------------------------------------------------------
# Sample data — mirrors what AuditWriter.publish_triage_completed produces
# ---------------------------------------------------------------------------
@pytest.fixture
def triage_completed_event():
    """Sample event dict matching the shape emitted by AuditWriter.publish_triage_completed."""
    return {
        "encounter_id": "enc-integration-001",
        "patient_id": "pat-integration-001",
        "triage_result": {
            "level": "Semi-Urgent",
            "confidence": 0.88,
            "reasoning_summary": "Persistent cough with fever in diabetic patient",
            "recommended_actions": ["Chest X-ray", "CBC and CRP"],
            "key_findings": ["Fever 38.2C", "Productive cough 3 days"],
        },
        "sentinel_check": {
            "hallucination_score": 0.05,
            "confidence_assessment": 0.90,
            "vitals_consistent": True,
            "medication_safe": True,
            "issues_found": [],
        },
        "timestamp": "2025-01-15T10:30:00+00:00",
        "audit_ref": "triage_sessions/enc-integration-001/audit/sentinel",
    }


# ---------------------------------------------------------------------------
# Pub/Sub push envelope factory
# ---------------------------------------------------------------------------
@pytest.fixture
def push_envelope_data():
    """Factory that converts a dict into Pub/Sub push POST body format.

    Usage::

        body = push_envelope_data(some_event_dict)
        response = await client.post("/push/triage-completed", json=body)
    """

    def _factory(data: dict) -> dict:
        encoded = base64.b64encode(json.dumps(data).encode("utf-8")).decode("utf-8")
        return {
            "message": {
                "data": encoded,
                "message_id": "integration-msg-001",
                "publish_time": "2025-01-15T10:30:00Z",
            },
            "subscription": "projects/sentinel-health-dev/subscriptions/triage-completed-sub",
        }

    return _factory


# ---------------------------------------------------------------------------
# Approval-worker mocks
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_approval_firestore():
    """AsyncMock for the approval-worker's Firestore service."""
    store = AsyncMock(spec=ApprovalFirestore)
    store.write_approval_entry.return_value = "approval_queue/enc-integration-001"
    store.update_approval_status.return_value = None
    store.update_triage_session_status.return_value = None
    store.get_approval.return_value = {
        "encounter_id": "enc-integration-001",
        "patient_id": "pat-integration-001",
        "status": "pending_approval",
        "triage_result": {
            "level": "Semi-Urgent",
            "confidence": 0.88,
            "reasoning_summary": "Persistent cough with fever in diabetic patient",
            "recommended_actions": ["Chest X-ray", "CBC and CRP"],
            "key_findings": ["Fever 38.2C", "Productive cough 3 days"],
        },
        "sentinel_check": {
            "hallucination_score": 0.05,
            "confidence_assessment": 0.90,
            "vitals_consistent": True,
            "medication_safe": True,
            "issues_found": [],
        },
        "audit_ref": "triage_sessions/enc-integration-001/audit/sentinel",
    }
    store.close.return_value = None
    return store


@pytest.fixture
def mock_approval_pubsub():
    """AsyncMock for the approval-worker's Pub/Sub service."""
    pub = AsyncMock(spec=ApprovalPubSub)
    pub.publish_triage_approved.return_value = None
    return pub


# ---------------------------------------------------------------------------
# HTTPX test client wired to the approval-worker FastAPI app
# ---------------------------------------------------------------------------
@pytest.fixture
async def approval_client(mock_approval_firestore, mock_approval_pubsub):
    """httpx AsyncClient for the approval-worker app with mocked Firestore and Pub/Sub."""
    approval_app.state.firestore = mock_approval_firestore
    approval_app.state.pubsub = mock_approval_pubsub
    transport = ASGITransport(app=approval_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

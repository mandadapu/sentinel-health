"""Fixtures for integration tests that bridge the backend and approval-worker services."""

import base64
import importlib
import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

_repo_root = Path(__file__).resolve().parents[3]


def _load_approval_worker():
    """Load the approval-worker app using sys.path manipulation with module cache isolation.

    Both backend and approval-worker use 'src' as their package name, so we must
    temporarily swap the sys.path and clear cached 'src' modules.
    """
    # Save current src modules
    saved_modules = {k: v for k, v in sys.modules.items() if k == "src" or k.startswith("src.")}

    # Remove cached src modules
    for key in list(saved_modules.keys()):
        del sys.modules[key]

    # Temporarily add approval-worker to front of sys.path
    approval_path = str(_repo_root / "approval-worker")
    sys.path.insert(0, approval_path)

    try:
        import src.main as approval_main
        import src.middleware.auth as approval_auth
        import src.services.firestore as approval_firestore
        import src.services.pubsub as approval_pubsub

        # Capture references before restoring
        result = {
            "app": approval_main.app,
            "verify_firebase_token": approval_auth.verify_firebase_token,
            "ApprovalFirestore": approval_firestore.ApprovalFirestore,
            "ApprovalPubSub": approval_pubsub.ApprovalPubSub,
        }
    finally:
        # Remove approval-worker src modules from cache
        for key in list(sys.modules.keys()):
            if key == "src" or key.startswith("src."):
                del sys.modules[key]

        # Restore original src modules
        sys.modules.update(saved_modules)

        # Remove approval-worker from sys.path
        if approval_path in sys.path:
            sys.path.remove(approval_path)

    return result


# Lazy-loaded to avoid import collision at collection time
_approval_refs = None


def _get_approval_refs():
    global _approval_refs
    if _approval_refs is None:
        _approval_refs = _load_approval_worker()
    return _approval_refs


async def _mock_firebase_user():
    return {"uid": "test-user-001", "email": "test@example.com"}


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
    """Factory that converts a dict into Pub/Sub push POST body format."""

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
    refs = _get_approval_refs()
    store = AsyncMock(spec=refs["ApprovalFirestore"])
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
    store.health_check.return_value = True
    store.close.return_value = None
    return store


@pytest.fixture
def mock_approval_pubsub():
    """AsyncMock for the approval-worker's Pub/Sub service."""
    refs = _get_approval_refs()
    pub = AsyncMock(spec=refs["ApprovalPubSub"])
    pub.publish_triage_approved.return_value = None
    pub.publish_classifier_feedback.return_value = None
    return pub


# ---------------------------------------------------------------------------
# HTTPX test client wired to the approval-worker FastAPI app
# ---------------------------------------------------------------------------
@pytest.fixture
async def approval_client(mock_approval_firestore, mock_approval_pubsub):
    """httpx AsyncClient for the approval-worker app with mocked Firestore and Pub/Sub."""
    refs = _get_approval_refs()
    app = refs["app"]
    app.state.firestore = mock_approval_firestore
    app.state.pubsub = mock_approval_pubsub
    app.dependency_overrides[refs["verify_firebase_token"]] = _mock_firebase_user
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()

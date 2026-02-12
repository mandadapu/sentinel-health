import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.firestore import ApprovalFirestore
from src.services.pubsub import ApprovalPubSub


@pytest.fixture
def mock_firestore():
    store = AsyncMock(spec=ApprovalFirestore)
    store.write_approval_entry.return_value = "approval_queue/enc-001"
    store.update_approval_status.return_value = None
    store.update_triage_session_status.return_value = None
    store.get_approval.return_value = {
        "encounter_id": "enc-001",
        "patient_id": "pat-001",
        "status": "pending_approval",
        "triage_result": {"level": "Semi-Urgent", "confidence": 0.88},
        "sentinel_check": {"passed": True},
    }
    store.close.return_value = None
    return store


@pytest.fixture
def mock_pubsub():
    pub = AsyncMock(spec=ApprovalPubSub)
    pub.publish_triage_approved.return_value = None
    pub.publish_classifier_feedback.return_value = None
    return pub

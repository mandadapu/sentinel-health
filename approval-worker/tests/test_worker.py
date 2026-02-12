"""Tests for the approval worker endpoints."""

import base64
import json

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


def _encode_message(data: dict) -> str:
    return base64.b64encode(json.dumps(data).encode()).decode()


@pytest.fixture
def sample_triage_message():
    return {
        "encounter_id": "enc-001",
        "patient_id": "pat-001",
        "triage_result": {
            "level": "Semi-Urgent",
            "confidence": 0.88,
            "reasoning_summary": "Persistent cough with fever",
            "model_used": "claude-sonnet-4-5-20250929",
            "routing_reason": "symptom_assessment",
        },
        "sentinel_check": {
            "passed": True,
            "hallucination_score": 0.05,
            "confidence_score": 0.92,
        },
        "timestamp": "2025-01-15T10:30:00Z",
        "audit_ref": "triage_sessions/enc-001/audit/sentinel",
    }


@pytest.fixture
async def client(mock_firestore, mock_pubsub):
    app.state.firestore = mock_firestore
    app.state.pubsub = mock_pubsub
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestHealth:
    @pytest.mark.asyncio
    async def test_health_returns_200(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"


class TestPushTriageCompleted:
    @pytest.mark.asyncio
    async def test_creates_approval_entry(self, client, mock_firestore, sample_triage_message):
        envelope = {
            "message": {
                "data": _encode_message(sample_triage_message),
                "message_id": "msg-001",
                "publish_time": "2025-01-15T10:30:00Z",
            },
            "subscription": "projects/sentinel-health-dev/subscriptions/triage-completed-sub",
        }

        response = await client.post("/push/triage-completed", json=envelope)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        mock_firestore.write_approval_entry.assert_called_once()
        call_args = mock_firestore.write_approval_entry.call_args
        assert call_args[0][0] == "enc-001"
        entry = call_args[0][1]
        assert entry["status"] == "pending_approval"
        assert entry["patient_id"] == "pat-001"
        assert entry["triage_result"]["level"] == "Semi-Urgent"

    @pytest.mark.asyncio
    async def test_rejects_invalid_payload(self, client):
        envelope = {
            "message": {
                "data": "not-base64!!!",
                "message_id": "msg-002",
                "publish_time": "",
            },
            "subscription": "",
        }

        response = await client.post("/push/triage-completed", json=envelope)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_rejects_missing_encounter_id(self, client):
        message = {"patient_id": "pat-001"}
        envelope = {
            "message": {
                "data": _encode_message(message),
                "message_id": "msg-003",
                "publish_time": "",
            },
            "subscription": "",
        }

        response = await client.post("/push/triage-completed", json=envelope)
        assert response.status_code == 400
        assert "encounter_id" in response.json()["detail"]


class TestApproveEndpoint:
    @pytest.mark.asyncio
    async def test_approve_success(self, client, mock_firestore, mock_pubsub):
        request = {
            "encounter_id": "enc-001",
            "status": "approved",
            "reviewer_id": "dr-smith",
            "notes": "Looks correct",
        }

        response = await client.post("/api/approve", json=request)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        mock_firestore.update_approval_status.assert_called_once_with(
            "enc-001", "approved", "dr-smith", "Looks correct", None
        )
        mock_firestore.update_triage_session_status.assert_called_once_with(
            "enc-001", "approved", "dr-smith", "Looks correct"
        )
        mock_pubsub.publish_triage_approved.assert_called_once()
        approved_event = mock_pubsub.publish_triage_approved.call_args[0][0]
        assert approved_event["encounter_id"] == "enc-001"
        assert approved_event["reviewer_id"] == "dr-smith"

    @pytest.mark.asyncio
    async def test_reject_does_not_publish(self, client, mock_firestore, mock_pubsub):
        request = {
            "encounter_id": "enc-001",
            "status": "rejected",
            "reviewer_id": "dr-smith",
            "notes": "Triage level too low",
        }

        response = await client.post("/api/approve", json=request)
        assert response.status_code == 200

        mock_firestore.update_approval_status.assert_called_once_with(
            "enc-001", "rejected", "dr-smith", "Triage level too low", None
        )
        mock_firestore.update_triage_session_status.assert_called_once_with(
            "enc-001", "rejected", "dr-smith", "Triage level too low"
        )
        mock_pubsub.publish_triage_approved.assert_not_called()

    @pytest.mark.asyncio
    async def test_approve_not_found(self, client, mock_firestore):
        mock_firestore.get_approval.return_value = None

        request = {
            "encounter_id": "enc-999",
            "status": "approved",
            "reviewer_id": "dr-smith",
        }

        response = await client.post("/api/approve", json=request)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_approve_already_processed(self, client, mock_firestore):
        mock_firestore.get_approval.return_value = {
            "encounter_id": "enc-001",
            "status": "approved",
        }

        request = {
            "encounter_id": "enc-001",
            "status": "approved",
            "reviewer_id": "dr-jones",
        }

        response = await client.post("/api/approve", json=request)
        assert response.status_code == 409


class TestClassifierFeedback:
    @pytest.mark.asyncio
    async def test_corrected_category_publishes_feedback(
        self, client, mock_firestore, mock_pubsub
    ):
        """When corrected_category differs from original, feedback is published."""
        mock_firestore.get_approval.return_value = {
            "encounter_id": "enc-001",
            "status": "pending_approval",
            "triage_result": {
                "routing_reason": "routine_vitals",
                "confidence": 0.75,
            },
        }

        request = {
            "encounter_id": "enc-001",
            "status": "approved",
            "reviewer_id": "dr-smith",
            "notes": "This is actually acute",
            "corrected_category": "acute_presentation",
        }

        response = await client.post("/api/approve", json=request)
        assert response.status_code == 200

        mock_pubsub.publish_classifier_feedback.assert_called_once()
        feedback = mock_pubsub.publish_classifier_feedback.call_args[0][0]
        assert feedback["event_type"] == "classifier_feedback"
        assert feedback["original_category"] == "routine_vitals"
        assert feedback["corrected_category"] == "acute_presentation"
        assert feedback["classifier_confidence"] == 0.75
        assert feedback["reviewer_id"] == "dr-smith"

    @pytest.mark.asyncio
    async def test_no_correction_does_not_publish_feedback(
        self, client, mock_firestore, mock_pubsub
    ):
        """When corrected_category is not provided, no feedback is published."""
        request = {
            "encounter_id": "enc-001",
            "status": "approved",
            "reviewer_id": "dr-smith",
        }

        response = await client.post("/api/approve", json=request)
        assert response.status_code == 200
        mock_pubsub.publish_classifier_feedback.assert_not_called()

    @pytest.mark.asyncio
    async def test_same_category_does_not_publish_feedback(
        self, client, mock_firestore, mock_pubsub
    ):
        """When corrected_category matches original, no feedback is published."""
        mock_firestore.get_approval.return_value = {
            "encounter_id": "enc-001",
            "status": "pending_approval",
            "triage_result": {
                "routing_reason": "symptom_assessment",
                "confidence": 0.88,
            },
        }

        request = {
            "encounter_id": "enc-001",
            "status": "approved",
            "reviewer_id": "dr-smith",
            "corrected_category": "symptom_assessment",
        }

        response = await client.post("/api/approve", json=request)
        assert response.status_code == 200
        mock_pubsub.publish_classifier_feedback.assert_not_called()

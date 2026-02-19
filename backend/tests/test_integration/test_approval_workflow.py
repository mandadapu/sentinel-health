"""Integration tests for the sentinel-health approval workflow.

These tests verify the cross-service flow:
  Backend (AuditWriter) -> Pub/Sub -> Approval Worker -> Firestore/Pub/Sub

Each test class validates a different aspect of the workflow:
  - End-to-end triage-to-approval flow
  - Cross-service data integrity
  - Double-approval prevention (idempotency)
  - Error propagation across service boundaries
  - Audit consumer batch flush to BigQuery
"""

import base64
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

_repo_root = Path(__file__).resolve().parents[3]


def _load_audit_consumer():
    """Load audit-consumer modules with sys.modules isolation."""
    saved_modules = {k: v for k, v in sys.modules.items() if k == "src" or k.startswith("src.")}
    for key in list(saved_modules.keys()):
        del sys.modules[key]

    audit_path = str(_repo_root / "audit-consumer")
    sys.path.insert(0, audit_path)

    try:
        import src.main as audit_main
        import src.services.bigquery as audit_bq

        result = {
            "app": audit_main.app,
            "AuditBigQuery": audit_bq.AuditBigQuery,
        }
    finally:
        for key in list(sys.modules.keys()):
            if key == "src" or key.startswith("src."):
                del sys.modules[key]
        sys.modules.update(saved_modules)
        if audit_path in sys.path:
            sys.path.remove(audit_path)

    return result


_audit_refs = None


def _get_audit_refs():
    global _audit_refs
    if _audit_refs is None:
        _audit_refs = _load_audit_consumer()
    return _audit_refs


# ---------------------------------------------------------------------------
# Class 1: End-to-end triage -> approval flow
# ---------------------------------------------------------------------------
class TestEndToEndTriageToApproval:
    """Verify the full lifecycle: Pub/Sub push creates an approval entry,
    then clinician approve/reject triggers the correct downstream effects."""

    @pytest.mark.asyncio
    async def test_triage_completed_creates_approval_entry(
        self,
        approval_client,
        mock_approval_firestore,
        triage_completed_event,
        push_envelope_data,
    ):
        """POST a push envelope to /push/triage-completed and verify
        that write_approval_entry is called with the correct data."""
        body = push_envelope_data(triage_completed_event)

        response = await approval_client.post("/push/triage-completed", json=body)

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        mock_approval_firestore.write_approval_entry.assert_called_once()
        call_args = mock_approval_firestore.write_approval_entry.call_args
        assert call_args[0][0] == "enc-integration-001"

        entry = call_args[0][1]
        assert entry["status"] == "pending_approval"
        assert entry["encounter_id"] == "enc-integration-001"
        assert entry["patient_id"] == "pat-integration-001"
        assert entry["triage_result"]["level"] == "Semi-Urgent"
        assert entry["sentinel_check"]["hallucination_score"] == 0.05
        assert entry["audit_ref"] == "triage_sessions/enc-integration-001/audit/sentinel"

    @pytest.mark.asyncio
    async def test_full_flow_approve(
        self,
        approval_client,
        mock_approval_firestore,
        mock_approval_pubsub,
        triage_completed_event,
        push_envelope_data,
    ):
        """End-to-end: create entry via push, then approve it.
        Verify update_approval_status, update_triage_session_status,
        and publish_triage_approved are all called."""
        # Step 1: create approval entry via push
        body = push_envelope_data(triage_completed_event)
        response = await approval_client.post("/push/triage-completed", json=body)
        assert response.status_code == 200

        # Step 2: approve the entry
        approve_request = {
            "encounter_id": "enc-integration-001",
            "status": "approved",
            "reviewer_id": "dr-integration-reviewer",
            "notes": "Triage assessment is accurate",
        }
        response = await approval_client.post("/api/approve", json=approve_request)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["encounter_id"] == "enc-integration-001"

        # Verify Firestore updates
        mock_approval_firestore.update_approval_status.assert_called_once_with(
            "enc-integration-001",
            "approved",
            "dr-integration-reviewer",
            "Triage assessment is accurate",
            None,
        )
        mock_approval_firestore.update_triage_session_status.assert_called_once_with(
            "enc-integration-001",
            "approved",
            "dr-integration-reviewer",
            "Triage assessment is accurate",
        )

        # Verify Pub/Sub publish for approved triage
        mock_approval_pubsub.publish_triage_approved.assert_called_once()
        approved_event = mock_approval_pubsub.publish_triage_approved.call_args[0][0]
        assert approved_event["encounter_id"] == "enc-integration-001"
        assert approved_event["reviewer_id"] == "dr-integration-reviewer"
        assert "approved_at" in approved_event

    @pytest.mark.asyncio
    async def test_full_flow_reject(
        self,
        approval_client,
        mock_approval_firestore,
        mock_approval_pubsub,
        triage_completed_event,
        push_envelope_data,
    ):
        """End-to-end: create entry via push, then reject it.
        Verify publish_triage_approved is NOT called on rejection."""
        # Step 1: create approval entry via push
        body = push_envelope_data(triage_completed_event)
        response = await approval_client.post("/push/triage-completed", json=body)
        assert response.status_code == 200

        # Step 2: reject the entry
        reject_request = {
            "encounter_id": "enc-integration-001",
            "status": "rejected",
            "reviewer_id": "dr-integration-reviewer",
            "notes": "Triage level should be Urgent, not Semi-Urgent",
        }
        response = await approval_client.post("/api/approve", json=reject_request)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        # Verify Firestore updates still happen for rejection
        mock_approval_firestore.update_approval_status.assert_called_once_with(
            "enc-integration-001",
            "rejected",
            "dr-integration-reviewer",
            "Triage level should be Urgent, not Semi-Urgent",
            None,
        )
        mock_approval_firestore.update_triage_session_status.assert_called_once_with(
            "enc-integration-001",
            "rejected",
            "dr-integration-reviewer",
            "Triage level should be Urgent, not Semi-Urgent",
        )

        # Pub/Sub should NOT be called for rejection
        mock_approval_pubsub.publish_triage_approved.assert_not_called()


# ---------------------------------------------------------------------------
# Class 2: Cross-service data integrity
# ---------------------------------------------------------------------------
class TestCrossServiceDataIntegrity:
    """Verify that data flowing from the backend through Pub/Sub to the
    approval worker is preserved without mutation."""

    @pytest.mark.asyncio
    async def test_encounter_id_preserved(
        self,
        approval_client,
        mock_approval_firestore,
        triage_completed_event,
        push_envelope_data,
    ):
        """encounter_id from the triage_completed event must flow through
        to the approval entry unchanged."""
        body = push_envelope_data(triage_completed_event)
        await approval_client.post("/push/triage-completed", json=body)

        call_args = mock_approval_firestore.write_approval_entry.call_args
        # First positional arg is encounter_id
        assert call_args[0][0] == triage_completed_event["encounter_id"]
        # Also inside the entry dict
        entry = call_args[0][1]
        assert entry["encounter_id"] == triage_completed_event["encounter_id"]

    @pytest.mark.asyncio
    async def test_triage_result_preserved(
        self,
        approval_client,
        mock_approval_firestore,
        triage_completed_event,
        push_envelope_data,
    ):
        """triage_result and sentinel_check dicts must be preserved without
        mutation through the Pub/Sub push handler."""
        body = push_envelope_data(triage_completed_event)
        await approval_client.post("/push/triage-completed", json=body)

        entry = mock_approval_firestore.write_approval_entry.call_args[0][1]

        # Deep equality — dicts must match the original event exactly
        assert entry["triage_result"] == triage_completed_event["triage_result"]
        assert entry["sentinel_check"] == triage_completed_event["sentinel_check"]

    @pytest.mark.asyncio
    async def test_audit_ref_preserved(
        self,
        approval_client,
        mock_approval_firestore,
        triage_completed_event,
        push_envelope_data,
    ):
        """audit_ref from the triage_completed event must flow through
        to the approval entry unchanged."""
        body = push_envelope_data(triage_completed_event)
        await approval_client.post("/push/triage-completed", json=body)

        entry = mock_approval_firestore.write_approval_entry.call_args[0][1]
        assert entry["audit_ref"] == triage_completed_event["audit_ref"]


# ---------------------------------------------------------------------------
# Class 3: Double-approval prevention (idempotency)
# ---------------------------------------------------------------------------
class TestDoubleApprovalPrevention:
    """Verify that the approval workflow prevents double-processing
    of the same encounter."""

    @pytest.mark.asyncio
    async def test_second_approval_returns_409(
        self,
        approval_client,
        mock_approval_firestore,
    ):
        """First approval succeeds, second returns 409.

        Uses side_effect on get_approval: first call returns pending,
        second call returns already-approved entry."""
        mock_approval_firestore.get_approval.side_effect = [
            # First call — entry is pending
            {
                "encounter_id": "enc-integration-001",
                "status": "pending_approval",
            },
            # Second call — entry has already been approved
            {
                "encounter_id": "enc-integration-001",
                "status": "approved",
                "reviewer_id": "dr-first-reviewer",
            },
        ]

        approve_request = {
            "encounter_id": "enc-integration-001",
            "status": "approved",
            "reviewer_id": "dr-first-reviewer",
            "notes": "Approved",
        }

        # First approval succeeds
        response = await approval_client.post("/api/approve", json=approve_request)
        assert response.status_code == 200

        # Second approval returns 409
        second_request = {
            "encounter_id": "enc-integration-001",
            "status": "approved",
            "reviewer_id": "dr-second-reviewer",
            "notes": "Also approved",
        }
        response = await approval_client.post("/api/approve", json=second_request)
        assert response.status_code == 409
        assert "already processed" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_reject_after_approval_returns_409(
        self,
        approval_client,
        mock_approval_firestore,
    ):
        """After an approval, a reject attempt should also return 409."""
        mock_approval_firestore.get_approval.side_effect = [
            # First call — entry is pending (for approve)
            {
                "encounter_id": "enc-integration-001",
                "status": "pending_approval",
            },
            # Second call — entry is already approved (for reject)
            {
                "encounter_id": "enc-integration-001",
                "status": "approved",
                "reviewer_id": "dr-first-reviewer",
            },
        ]

        # Approve first
        approve_request = {
            "encounter_id": "enc-integration-001",
            "status": "approved",
            "reviewer_id": "dr-first-reviewer",
            "notes": "Approved",
        }
        response = await approval_client.post("/api/approve", json=approve_request)
        assert response.status_code == 200

        # Then try to reject
        reject_request = {
            "encounter_id": "enc-integration-001",
            "status": "rejected",
            "reviewer_id": "dr-second-reviewer",
            "notes": "Should have been rejected",
        }
        response = await approval_client.post("/api/approve", json=reject_request)
        assert response.status_code == 409
        assert "already processed" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Class 4: Error propagation across service boundaries
# ---------------------------------------------------------------------------
class TestErrorPropagation:
    """Verify that service-layer failures propagate as proper HTTP error
    responses rather than being silently swallowed."""

    @pytest.mark.asyncio
    async def test_firestore_write_failure_returns_500(
        self,
        approval_client,
        mock_approval_firestore,
        triage_completed_event,
        push_envelope_data,
    ):
        """If write_approval_entry raises, the push endpoint should return 500."""
        mock_approval_firestore.write_approval_entry.side_effect = RuntimeError(
            "Firestore unavailable"
        )

        body = push_envelope_data(triage_completed_event)
        response = await approval_client.post("/push/triage-completed", json=body)

        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_firestore_update_failure_returns_500(
        self,
        approval_client,
        mock_approval_firestore,
    ):
        """If update_approval_status raises, the approve endpoint should return 500."""
        mock_approval_firestore.update_approval_status.side_effect = RuntimeError(
            "Firestore write conflict"
        )

        approve_request = {
            "encounter_id": "enc-integration-001",
            "status": "approved",
            "reviewer_id": "dr-error-test",
            "notes": "",
        }
        response = await approval_client.post("/api/approve", json=approve_request)

        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_pubsub_publish_failure_returns_500(
        self,
        approval_client,
        mock_approval_firestore,
        mock_approval_pubsub,
    ):
        """If publish_triage_approved raises, the approve endpoint should return 500."""
        mock_approval_pubsub.publish_triage_approved.side_effect = RuntimeError(
            "Pub/Sub topic not found"
        )

        approve_request = {
            "encounter_id": "enc-integration-001",
            "status": "approved",
            "reviewer_id": "dr-error-test",
            "notes": "",
        }
        response = await approval_client.post("/api/approve", json=approve_request)

        assert response.status_code == 500


# ---------------------------------------------------------------------------
# Class 5: Audit consumer batch flush
# ---------------------------------------------------------------------------
class TestAuditConsumerBatchFlush:
    """Verify that audit events pushed to the audit consumer reach BigQuery."""

    @pytest.fixture
    def mock_bigquery(self):
        """AsyncMock for AuditBigQuery."""
        refs = _get_audit_refs()
        bq = AsyncMock(spec=refs["AuditBigQuery"])
        bq.insert.return_value = None
        bq.flush.return_value = None
        bq.close.return_value = None
        return bq

    @pytest.fixture
    async def audit_client(self, mock_bigquery):
        """httpx AsyncClient wired to the audit-consumer app with mocked BigQuery."""
        refs = _get_audit_refs()
        audit_app = refs["app"]

        audit_app.state.bigquery = mock_bigquery
        transport = ASGITransport(app=audit_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest.mark.asyncio
    async def test_batch_flush_invokes_bigquery_insert(
        self,
        audit_client,
        mock_bigquery,
    ):
        """Feed an audit event via /push/audit-event and verify BigQuery insert is called."""
        audit_event = {
            "encounter_id": "enc-integration-001",
            "node": "extractor",
            "model": "claude-sonnet-4-5-20250929",
            "routing_decision": {
                "category": "symptom_assessment",
                "confidence": 0.92,
            },
            "tokens": {"in": 1200, "out": 450},
            "cost_usd": 0.0034,
            "compliance_flags": ["PII_REDACTED"],
            "sentinel_check": {
                "hallucination_score": 0.05,
                "confidence_score": 0.91,
                "circuit_breaker_tripped": False,
            },
            "duration_ms": 1540,
            "timestamp": "2025-01-15T10:30:00Z",
        }

        encoded = base64.b64encode(json.dumps(audit_event).encode("utf-8")).decode("utf-8")
        envelope = {
            "message": {
                "data": encoded,
                "message_id": "audit-msg-001",
                "publish_time": "2025-01-15T10:30:00Z",
            },
            "subscription": "projects/sentinel-health-dev/subscriptions/audit-events-sub",
        }

        response = await audit_client.post("/push/audit-event", json=envelope)

        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["encounter_id"] == "enc-integration-001"

        mock_bigquery.insert.assert_called_once()
        row = mock_bigquery.insert.call_args[0][0]
        assert row["encounter_id"] == "enc-integration-001"
        assert row["node_name"] == "extractor"
        assert row["model_used"] == "claude-sonnet-4-5-20250929"

"""Tests for AuditWriter class."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from src.audit.writer import AuditWriter


@pytest.fixture
def audit_writer_with_sidecar(mock_firestore, mock_pubsub, mock_sidecar_client):
    return AuditWriter(mock_firestore, mock_pubsub, mock_sidecar_client)


@pytest.fixture
def audit_writer_no_sidecar(mock_firestore, mock_pubsub):
    return AuditWriter(mock_firestore, mock_pubsub, sidecar_client=None)


@pytest.fixture
def node_audit_kwargs():
    return {
        "encounter_id": "enc-001",
        "node_name": "extractor",
        "model": "claude-sonnet-4-5-20250929",
        "routing_decision": {"category": "symptom_assessment", "confidence": 0.92},
        "input_summary": "Patient presents with cough",
        "output_summary": '{"vitals": {"heart_rate": 88}}',
        "tokens": {"in": 100, "out": 50},
        "cost_usd": 0.00015,
        "compliance_flags": ["FHIR_VALID"],
        "sentinel_check": None,
        "duration_ms": 200,
    }


class TestWriteNodeAudit:
    @pytest.mark.asyncio
    async def test_with_sidecar(
        self, audit_writer_with_sidecar, mock_firestore, mock_sidecar_client, node_audit_kwargs
    ):
        doc_path = await audit_writer_with_sidecar.write_node_audit(**node_audit_kwargs)

        assert doc_path == "test_sessions/enc-001/audit/extractor"

        # Sidecar called twice: input + output
        assert mock_sidecar_client.validate.call_count == 2

        # Firestore write called
        mock_firestore.write_audit.assert_called_once()
        call_args = mock_firestore.write_audit.call_args[0]
        assert call_args[0] == "enc-001"
        assert call_args[1] == "extractor"

        audit_doc = call_args[2]
        assert audit_doc["encounter_id"] == "enc-001"
        assert audit_doc["node"] == "extractor"
        assert audit_doc["model"] == "claude-sonnet-4-5-20250929"
        assert "timestamp" in audit_doc

    @pytest.mark.asyncio
    async def test_without_sidecar(
        self, audit_writer_no_sidecar, mock_firestore, node_audit_kwargs
    ):
        doc_path = await audit_writer_no_sidecar.write_node_audit(**node_audit_kwargs)

        assert doc_path == "test_sessions/enc-001/audit/extractor"
        mock_firestore.write_audit.assert_called_once()

        audit_doc = mock_firestore.write_audit.call_args[0][2]
        assert audit_doc["input_summary"] == "Patient presents with cough"
        assert audit_doc["compliance_flags"] == ["FHIR_VALID"]

    @pytest.mark.asyncio
    async def test_sidecar_failure_propagates(
        self, mock_firestore, mock_pubsub, node_audit_kwargs
    ):
        failing_sidecar = AsyncMock()
        failing_sidecar.validate = AsyncMock(side_effect=Exception("Sidecar down"))
        writer = AuditWriter(mock_firestore, mock_pubsub, failing_sidecar)

        with pytest.raises(Exception, match="Sidecar down"):
            await writer.write_node_audit(**node_audit_kwargs)

    @pytest.mark.asyncio
    async def test_publishes_to_pubsub(
        self, audit_writer_no_sidecar, mock_pubsub, node_audit_kwargs
    ):
        await audit_writer_no_sidecar.write_node_audit(**node_audit_kwargs)

        # Give the fire-and-forget task a chance to run
        await asyncio.sleep(0.05)

        mock_pubsub.publish_audit_event.assert_called_once()
        audit_doc = mock_pubsub.publish_audit_event.call_args[0][0]
        assert audit_doc["encounter_id"] == "enc-001"
        assert audit_doc["node"] == "extractor"

    @pytest.mark.asyncio
    async def test_compliance_flags_from_both_validations(
        self, mock_firestore, mock_pubsub, mock_sidecar_client, node_audit_kwargs
    ):
        from src.services.sidecar_client import SidecarValidationResult

        call_count = 0

        def side_effect(content, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return SidecarValidationResult({
                    "validated": True,
                    "content": content,
                    "compliance_flags": ["PII_REDACTED"],
                    "redactions": [],
                    "errors": [],
                    "should_retry": False,
                    "latency_ms": 1.0,
                })
            return SidecarValidationResult({
                "validated": True,
                "content": content,
                "compliance_flags": ["PHI_STRIPPED"],
                "redactions": [],
                "errors": [],
                "should_retry": False,
                "latency_ms": 1.0,
            })

        mock_sidecar_client.validate = AsyncMock(side_effect=side_effect)
        writer = AuditWriter(mock_firestore, mock_pubsub, mock_sidecar_client)

        await writer.write_node_audit(**node_audit_kwargs)

        audit_doc = mock_firestore.write_audit.call_args[0][2]
        assert "FHIR_VALID" in audit_doc["compliance_flags"]
        assert "PII_REDACTED" in audit_doc["compliance_flags"]
        assert "PHI_STRIPPED" in audit_doc["compliance_flags"]


class TestPublishTriageCompleted:
    @pytest.mark.asyncio
    async def test_publishes_event(self, audit_writer_no_sidecar, mock_pubsub):
        await audit_writer_no_sidecar.publish_triage_completed(
            encounter_id="enc-001",
            patient_id="pat-001",
            triage_result={"level": "Semi-Urgent", "confidence": 0.82},
            sentinel_check={"passed": True, "hallucination_score": 0.05},
            audit_ref="test_sessions/enc-001/audit/sentinel",
        )

        mock_pubsub.publish_triage_completed.assert_called_once()
        event = mock_pubsub.publish_triage_completed.call_args[0][0]
        assert event["encounter_id"] == "enc-001"
        assert event["patient_id"] == "pat-001"
        assert event["triage_result"]["level"] == "Semi-Urgent"
        assert event["sentinel_check"]["passed"] is True
        assert event["audit_ref"] == "test_sessions/enc-001/audit/sentinel"
        assert "timestamp" in event


class TestSafePublish:
    @pytest.mark.asyncio
    async def test_swallows_errors(self, mock_firestore, mock_pubsub):
        mock_pubsub.publish_audit_event = AsyncMock(
            side_effect=Exception("Pub/Sub unavailable")
        )
        writer = AuditWriter(mock_firestore, mock_pubsub)

        # Should not raise
        await writer._safe_publish({"encounter_id": "enc-001"})

        mock_pubsub.publish_audit_event.assert_called_once()

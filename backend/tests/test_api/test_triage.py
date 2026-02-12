"""Tests for POST /api/triage endpoint."""

import pytest
from unittest.mock import AsyncMock

from src.api import triage


class TestTriageEndpoint:
    @pytest.mark.asyncio
    async def test_triage_success(self, client, mock_pipeline):
        request = {
            "encounter_text": "45-year-old male with persistent cough for 3 days",
            "patient_id": "pat-001",
            "encounter_id": "enc-001",
        }

        response = await client.post("/api/triage", json=request)
        assert response.status_code == 200

        data = response.json()
        assert data["encounter_id"] == "enc-001"
        assert data["patient_id"] == "pat-001"
        assert data["triage_level"] == "Semi-Urgent"
        assert data["confidence"] == 0.82
        assert data["routing_category"] == "symptom_assessment"
        assert data["sentinel_passed"] is True
        assert data["circuit_breaker_tripped"] is False
        assert data["audit_ref"] == "test_sessions/enc-001/audit/sentinel"
        assert "timestamp" in data

        mock_pipeline.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_pipeline_not_initialized(self, client, mock_audit_writer, mock_firestore):
        triage.set_dependencies(None, mock_audit_writer, mock_firestore)

        request = {
            "encounter_text": "45-year-old male with persistent cough for 3 days",
            "patient_id": "pat-001",
        }

        response = await client.post("/api/triage", json=request)
        assert response.status_code == 503
        assert "Pipeline not initialized" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_circuit_breaker_tripped(self, client, mock_pipeline):
        mock_pipeline.ainvoke.return_value["circuit_breaker_tripped"] = True
        mock_pipeline.ainvoke.return_value["sentinel_check"]["passed"] = False

        request = {
            "encounter_text": "45-year-old male with persistent cough for 3 days",
            "patient_id": "pat-001",
            "encounter_id": "enc-002",
        }

        response = await client.post("/api/triage", json=request)
        assert response.status_code == 200

        data = response.json()
        assert data["circuit_breaker_tripped"] is True
        assert data["sentinel_passed"] is False

    @pytest.mark.asyncio
    async def test_missing_patient_id(self, client):
        request = {
            "encounter_text": "45-year-old male with persistent cough for 3 days",
        }

        response = await client.post("/api/triage", json=request)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_encounter_text_too_short(self, client):
        request = {
            "encounter_text": "short",
            "patient_id": "pat-001",
        }

        response = await client.post("/api/triage", json=request)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_auto_generates_encounter_id(self, client, mock_pipeline):
        request = {
            "encounter_text": "45-year-old male with persistent cough for 3 days",
            "patient_id": "pat-001",
        }

        response = await client.post("/api/triage", json=request)
        assert response.status_code == 200

        # Pipeline should have been called with a UUID encounter_id
        call_args = mock_pipeline.ainvoke.call_args[0][0]
        assert len(call_args["encounter_id"]) == 36  # UUID format

    @pytest.mark.asyncio
    async def test_publishes_triage_completed(self, client, mock_audit_writer):
        request = {
            "encounter_text": "45-year-old male with persistent cough for 3 days",
            "patient_id": "pat-001",
            "encounter_id": "enc-001",
        }

        await client.post("/api/triage", json=request)

        mock_audit_writer.publish_triage_completed.assert_called_once()
        call_kwargs = mock_audit_writer.publish_triage_completed.call_args[1]
        assert call_kwargs["encounter_id"] == "enc-001"
        assert call_kwargs["patient_id"] == "pat-001"
        assert call_kwargs["triage_result"]["level"] == "Semi-Urgent"
        assert call_kwargs["sentinel_check"]["passed"] is True

"""Tests for all sidecar validators and the /validate API."""

import json

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.models import TokenInfo
from src.validators.fhir_validator import FHIRValidator
from src.validators.phi_stripper import PHIStripper
from src.validators.pii_scanner import PIIScanner
from src.validators.token_guard import TokenGuard


# ── PII Scanner ──────────────────────────────────────────────────────────────


class TestPIIScanner:
    def test_detects_ssn(self, pii_scanner):
        result = pii_scanner.scan("Patient SSN is 123-45-6789")
        assert "[REDACTED]" in result.masked
        assert "123-45-6789" not in result.masked
        assert any(r.type == "SSN" for r in result.redactions)
        assert "PII_MASKED_SSN" in result.flags

    def test_detects_email(self, pii_scanner):
        result = pii_scanner.scan("Contact: john@hospital.com for records")
        assert "[REDACTED]" in result.masked
        assert "john@hospital.com" not in result.masked
        assert "PII_MASKED_EMAIL" in result.flags

    def test_detects_mrn(self, pii_scanner):
        result = pii_scanner.scan("MRN: 1234567 for patient file")
        assert "[REDACTED]" in result.masked
        assert "PII_MASKED_MRN" in result.flags

    def test_detects_dob(self, pii_scanner):
        result = pii_scanner.scan("DOB: 01/15/1980 patient information")
        assert "[REDACTED]" in result.masked
        assert "PII_MASKED_DOB" in result.flags

    def test_detects_phone(self, pii_scanner):
        result = pii_scanner.scan("Call 555-123-4567 for appointment")
        assert "[REDACTED]" in result.masked
        assert "PII_MASKED_PHONE" in result.flags

    def test_clean_text_returns_pii_clean(self, pii_scanner):
        result = pii_scanner.scan("Patient has mild headache and fever")
        assert result.masked == "Patient has mild headache and fever"
        assert result.redactions == []
        assert "PII_CLEAN" in result.flags

    def test_multiple_pii_types(self, pii_scanner):
        result = pii_scanner.scan(
            "Patient SSN 123-45-6789, email: test@example.com"
        )
        assert "123-45-6789" not in result.masked
        assert "test@example.com" not in result.masked
        assert len(result.redactions) >= 2

    def test_backend_name_is_python(self, pii_scanner):
        assert pii_scanner.backend_name == "python"


# ── FHIR Validator ───────────────────────────────────────────────────────────


class TestFHIRValidator:
    def test_valid_extractor_output(self, fhir_validator):
        content = json.dumps(
            {
                "vitals": {
                    "heart_rate": 88,
                    "blood_pressure": "130/85",
                    "temperature": 38.2,
                    "respiratory_rate": 18,
                    "spo2": 97,
                },
                "symptoms": [
                    {"description": "cough", "onset": "3 days", "severity": "moderate"}
                ],
                "medications": [{"name": "metformin", "dose": "500mg", "frequency": "BID"}],
                "history": {
                    "conditions": ["diabetes"],
                    "allergies": [],
                    "surgeries": [],
                },
                "chief_complaint": "persistent cough",
                "assessment_notes": "febrile patient",
            }
        )
        result = fhir_validator.validate(content, "extractor")
        assert result.valid is True
        assert "FHIR_VALID_EXTRACTOR" in result.flags

    def test_missing_required_field(self, fhir_validator):
        content = json.dumps(
            {
                "vitals": {
                    "heart_rate": 88,
                    "blood_pressure": "130/85",
                    "temperature": 38.2,
                    "respiratory_rate": 18,
                    "spo2": 97,
                },
                # Missing: symptoms, medications, history, chief_complaint
            }
        )
        result = fhir_validator.validate(content, "extractor")
        assert result.valid is False
        assert "FHIR_INVALID_EXTRACTOR" in result.flags
        assert len(result.errors) > 0

    def test_valid_reasoner_output(self, fhir_validator):
        content = json.dumps(
            {
                "level": "Semi-Urgent",
                "confidence": 0.82,
                "reasoning_summary": "Febrile patient with cough",
                "recommended_actions": ["Chest X-ray"],
                "key_findings": ["Fever 38.2C"],
            }
        )
        result = fhir_validator.validate(content, "reasoner")
        assert result.valid is True
        assert "FHIR_VALID_REASONER" in result.flags

    def test_invalid_triage_level(self, fhir_validator):
        content = json.dumps(
            {
                "level": "Critical",  # Invalid enum value
                "confidence": 0.82,
                "reasoning_summary": "High acuity",
            }
        )
        result = fhir_validator.validate(content, "reasoner")
        assert result.valid is False
        assert "FHIR_INVALID_REASONER" in result.flags

    def test_valid_sentinel_output(self, fhir_validator):
        content = json.dumps(
            {
                "hallucination_score": 0.05,
                "confidence_assessment": 0.90,
                "vitals_consistent": True,
                "medication_safe": True,
                "issues_found": [],
            }
        )
        result = fhir_validator.validate(content, "sentinel")
        assert result.valid is True
        assert "FHIR_VALID_SENTINEL" in result.flags

    def test_invalid_json_content(self, fhir_validator):
        result = fhir_validator.validate("not valid json {{{", "extractor")
        assert result.valid is False
        assert "FHIR_INVALID_EXTRACTOR" in result.flags

    def test_missing_schema_returns_warning(self, fhir_validator):
        result = fhir_validator.validate('{"key": "value"}', "unknown_node")
        assert result.valid is True
        assert "FHIR_SCHEMA_MISSING_UNKNOWN_NODE" in result.flags

    def test_confidence_out_of_range(self, fhir_validator):
        content = json.dumps(
            {
                "hallucination_score": 1.5,  # > 1.0
                "confidence_assessment": 0.90,
                "vitals_consistent": True,
                "medication_safe": True,
            }
        )
        result = fhir_validator.validate(content, "sentinel")
        assert result.valid is False


# ── PHI Stripper ─────────────────────────────────────────────────────────────


class TestPHIStripper:
    def test_strips_ssn(self, phi_stripper):
        result = phi_stripper.strip("SSN 123-45-6789 in audit log")
        assert "123-45-6789" not in result.cleaned
        assert "***PHI_REDACTED***" in result.cleaned
        assert "PHI_REDACTED" in result.flags

    def test_strips_patient_name(self, phi_stripper):
        result = phi_stripper.strip("Patient: John Smith presented with cough")
        assert "John Smith" not in result.cleaned
        assert "PHI_STRIPPED_PATIENT_NAME" in result.flags

    def test_strips_provider_name(self, phi_stripper):
        result = phi_stripper.strip("Dr. Sarah Johnson ordered labs")
        assert "Sarah Johnson" not in result.cleaned
        assert "PHI_STRIPPED_PROVIDER_NAME" in result.flags

    def test_clean_text_returns_phi_clean(self, phi_stripper):
        result = phi_stripper.strip("Vitals: HR 88, BP 130/85, Temp 38.2C")
        assert result.redactions == []
        assert "PHI_CLEAN" in result.flags

    def test_multiple_phi_types(self, phi_stripper):
        result = phi_stripper.strip(
            "Patient: John Smith, SSN 123-45-6789, Dr. Jane Doe"
        )
        assert len(result.redactions) >= 2
        assert "PHI_REDACTED" in result.flags


# ── Token Guard ──────────────────────────────────────────────────────────────


class TestTokenGuard:
    def test_normal_output_tokens(self, token_guard):
        tokens = TokenInfo(**{"in": 100, "out": 50})
        result = token_guard.check(tokens, "output")
        assert "TOKEN_OUTPUT_OK" in result.flags
        assert result.errors == []

    def test_short_output_tokens(self, token_guard):
        tokens = TokenInfo(**{"in": 100, "out": 3})
        result = token_guard.check(tokens, "output")
        assert "TOKEN_OUTPUT_SUSPICIOUSLY_SHORT" in result.flags
        assert len(result.errors) == 1

    def test_long_output_tokens(self, token_guard):
        tokens = TokenInfo(**{"in": 100, "out": 99999})
        result = token_guard.check(tokens, "output")
        assert "TOKEN_OUTPUT_SUSPICIOUSLY_LONG" in result.flags
        assert len(result.errors) == 1

    def test_normal_input_tokens(self, token_guard):
        tokens = TokenInfo(**{"in": 100, "out": 50})
        result = token_guard.check(tokens, "input")
        assert "TOKEN_INPUT_OK" in result.flags

    def test_short_input_tokens(self, token_guard):
        tokens = TokenInfo(**{"in": 1, "out": 50})
        result = token_guard.check(tokens, "input")
        assert "TOKEN_INPUT_SUSPICIOUSLY_SHORT" in result.flags


# ── API Integration ──────────────────────────────────────────────────────────


class TestAPI:
    @pytest.fixture
    def client(self):
        with TestClient(app) as c:
            yield c

    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "pii_backend" in data

    def test_validate_input_type(self, client):
        response = client.post(
            "/validate",
            json={
                "content": "Patient has mild headache",
                "node_name": "extractor",
                "encounter_id": "enc-001",
                "validation_type": "input",
                "tokens": {"in": 100, "out": 0},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["validated"] is True
        assert "PII_CLEAN" in data["compliance_flags"]
        assert "TOKEN_INPUT_OK" in data["compliance_flags"]

    def test_validate_output_type_with_fhir(self, client):
        content = json.dumps(
            {
                "vitals": {
                    "heart_rate": 88,
                    "blood_pressure": "130/85",
                    "temperature": 38.2,
                    "respiratory_rate": 18,
                    "spo2": 97,
                },
                "symptoms": [{"description": "cough", "onset": "3 days", "severity": "moderate"}],
                "medications": [{"name": "metformin", "dose": "500mg", "frequency": "BID"}],
                "history": {"conditions": ["diabetes"], "allergies": [], "surgeries": []},
                "chief_complaint": "persistent cough",
                "assessment_notes": "febrile patient",
            }
        )
        response = client.post(
            "/validate",
            json={
                "content": content,
                "node_name": "extractor",
                "encounter_id": "enc-001",
                "validation_type": "output",
                "tokens": {"in": 100, "out": 50},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["validated"] is True
        assert "FHIR_VALID_EXTRACTOR" in data["compliance_flags"]

    def test_validate_output_fhir_failure(self, client):
        response = client.post(
            "/validate",
            json={
                "content": json.dumps({"level": "Critical", "confidence": 0.9, "reasoning_summary": "test"}),
                "node_name": "reasoner",
                "encounter_id": "enc-001",
                "validation_type": "output",
                "tokens": {"in": 100, "out": 50},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["validated"] is False
        assert data["should_retry"] is True
        assert "FHIR_INVALID_REASONER" in data["compliance_flags"]

    def test_validate_audit_type_strips_phi(self, client):
        response = client.post(
            "/validate",
            json={
                "content": "Patient: John Smith, SSN 123-45-6789",
                "node_name": "extractor",
                "encounter_id": "enc-001",
                "validation_type": "audit",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "123-45-6789" not in data["content"]
        assert "John Smith" not in data["content"]
        assert "PHI_REDACTED" in data["compliance_flags"]

    def test_validate_pii_masking(self, client):
        response = client.post(
            "/validate",
            json={
                "content": "SSN is 123-45-6789 and email john@test.com",
                "node_name": "extractor",
                "encounter_id": "enc-001",
                "validation_type": "input",
                "tokens": {"in": 100, "out": 0},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "123-45-6789" not in data["content"]
        assert "john@test.com" not in data["content"]
        assert len(data["redactions"]) >= 2

    def test_validate_latency_reported(self, client):
        response = client.post(
            "/validate",
            json={
                "content": "simple text",
                "node_name": "extractor",
                "encounter_id": "enc-001",
                "validation_type": "input",
                "tokens": {"in": 10, "out": 0},
            },
        )
        data = response.json()
        assert data["latency_ms"] >= 0

    def test_validate_invalid_node_name(self, client):
        response = client.post(
            "/validate",
            json={
                "content": "test",
                "node_name": "invalid",
                "encounter_id": "enc-001",
                "validation_type": "input",
            },
        )
        assert response.status_code == 422

    def test_validate_invalid_validation_type(self, client):
        response = client.post(
            "/validate",
            json={
                "content": "test",
                "node_name": "extractor",
                "encounter_id": "enc-001",
                "validation_type": "invalid",
            },
        )
        assert response.status_code == 422

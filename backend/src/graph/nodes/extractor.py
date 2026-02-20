import json
import logging
from typing import Any

from src.audit.writer import AuditWriter
from src.graph.state import AgentState
from src.services.anthropic_client import AnthropicClient
from src.services.sidecar_client import SidecarClient

logger = logging.getLogger(__name__)

EXTRACTOR_SYSTEM_PROMPT = """You are a clinical data extraction specialist. Extract structured \
clinical data from the raw encounter text.

Extract the following fields as JSON:
{
  "vitals": {"heart_rate": null, "blood_pressure": null, "temperature": null, "respiratory_rate": null, "spo2": null},
  "symptoms": [{"description": "...", "onset": "...", "severity": "mild|moderate|severe"}],
  "medications": [{"name": "...", "dose": "...", "frequency": "..."}],
  "history": {"conditions": [], "allergies": [], "surgeries": []},
  "chief_complaint": "...",
  "assessment_notes": "..."
}

Be precise. If information is not present, use null. Do not infer or hallucinate data."""

MAX_RETRIES = 2


async def extractor_node(
    state: AgentState,
    *,
    anthropic_client: AnthropicClient,
    audit_writer: AuditWriter,
    sidecar_client: SidecarClient | None = None,
) -> dict[str, Any]:
    """Extract structured clinical data from raw encounter text."""
    model = state["routing_metadata"]["selected_model"]
    encounter_id = state["encounter_id"]
    raw_input = state["raw_input"]

    # --- Sidecar: validate input (PII scan) ---
    compliance_flags: list[str] = list(state.get("compliance_flags", []))
    validated_input = raw_input

    if sidecar_client:
        input_result = await sidecar_client.validate(
            content=raw_input,
            node_name="extractor",
            encounter_id=encounter_id,
            validation_type="input",
        )
        validated_input = input_result.content
        compliance_flags.extend(input_result.compliance_flags)

    # LLM call with retry on FHIR validation failure
    response = None
    extracted = None

    for attempt in range(1 + MAX_RETRIES):
        response = await anthropic_client.complete(
            model=model,
            system_prompt=EXTRACTOR_SYSTEM_PROMPT,
            user_message=validated_input,
        )

        # --- Sidecar: validate output (PII + FHIR + token guard) ---
        if sidecar_client:
            output_result = await sidecar_client.validate(
                content=response["content"],
                node_name="extractor",
                encounter_id=encounter_id,
                validation_type="output",
                tokens=response["tokens"],
            )
            compliance_flags.extend(output_result.compliance_flags)

            if output_result.should_retry and attempt < MAX_RETRIES:
                logger.warning(
                    "FHIR validation failed for extractor (attempt %d/%d): %s",
                    attempt + 1,
                    MAX_RETRIES,
                    output_result.errors,
                )
                continue

            if not output_result.validated and attempt == MAX_RETRIES:
                compliance_flags.append("FHIR_RETRY_EXHAUSTED")
                logger.error(
                    "FHIR validation failed after %d retries for extractor: %s",
                    MAX_RETRIES,
                    output_result.errors,
                )

        break

    try:
        extracted = json.loads(response["content"])
    except (json.JSONDecodeError, KeyError) as exc:
        logger.error(
            "Extractor JSON parse failed for %s — tripping circuit breaker: %s",
            encounter_id,
            exc,
        )
        compliance_flags.append("JSON_PARSE_FAILED")
        extracted = {}

    audit_ref = await audit_writer.write_node_audit(
        encounter_id=encounter_id,
        node_name="extractor",
        model=response["model"],
        routing_decision={
            "category": state["routing_metadata"]["category"],
            "confidence": state["routing_metadata"]["classifier_confidence"],
            "reason": state["routing_metadata"].get("escalation_reason", "default"),
        },
        input_summary=raw_input[:500],
        output_summary=json.dumps(extracted)[:500],
        tokens=response["tokens"],
        cost_usd=response["cost_usd"],
        compliance_flags=compliance_flags,
        sentinel_check=None,
        duration_ms=response["duration_ms"],
    )

    result: dict[str, Any] = {
        "fhir_data": extracted,
        "clinical_context": extracted,
        "compliance_flags": compliance_flags,
        "audit_trail": state.get("audit_trail", [])
        + [
            {
                "encounter_id": encounter_id,
                "node": "extractor",
                "model": response["model"],
                "tokens": response["tokens"],
                "cost_usd": response["cost_usd"],
                "duration_ms": response["duration_ms"],
                "audit_ref": audit_ref,
            }
        ],
    }

    if "JSON_PARSE_FAILED" in compliance_flags:
        result["circuit_breaker_tripped"] = True
        result["error"] = "Extractor failed to parse LLM output"

    return result

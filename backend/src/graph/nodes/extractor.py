import json
import logging
from typing import Any

from src.audit.writer import AuditWriter
from src.graph.state import AgentState
from src.services.anthropic_client import AnthropicClient

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


async def extractor_node(
    state: AgentState,
    *,
    anthropic_client: AnthropicClient,
    audit_writer: AuditWriter,
) -> dict[str, Any]:
    """Extract structured clinical data from raw encounter text."""
    model = state["routing_metadata"]["selected_model"]
    encounter_id = state["encounter_id"]
    raw_input = state["raw_input"]

    # --- Sidecar hook (Layer 1 placeholder for Prompt 3) ---
    validated_input = raw_input
    compliance_flags: list[str] = list(state.get("compliance_flags", []))

    response = await anthropic_client.complete(
        model=model,
        system_prompt=EXTRACTOR_SYSTEM_PROMPT,
        user_message=validated_input,
    )

    extracted = json.loads(response["content"])

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

    return {
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

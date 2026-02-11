import json
import logging
from typing import Any

from src.audit.writer import AuditWriter
from src.config import Settings
from src.graph.state import AgentState, SentinelCheck
from src.services.anthropic_client import AnthropicClient

logger = logging.getLogger(__name__)

HALLUCINATION_CHECK_PROMPT = """You are a clinical safety validator. Review the triage decision \
against the original clinical data. Evaluate:

1. Hallucination: Does the triage decision reference information NOT in the clinical data?
2. Confidence calibration: Is the stated confidence appropriate given the evidence?
3. Vitals cross-reference: Does the triage level match the severity indicated by vitals?
4. Medication safety: Are there any drug interaction or allergy concerns missed?

Respond with JSON:
{
  "hallucination_score": <0.0-1.0>,
  "confidence_assessment": <0.0-1.0>,
  "vitals_consistent": true/false,
  "medication_safe": true/false,
  "issues_found": ["issue1", "issue2"]
}"""


async def sentinel_node(
    state: AgentState,
    *,
    anthropic_client: AnthropicClient,
    audit_writer: AuditWriter,
    settings: Settings,
) -> dict[str, Any]:
    """Validate triage decision with hallucination check and circuit breaker."""
    encounter_id = state["encounter_id"]
    model = settings.sentinel_model

    user_message = (
        f"Original clinical data:\n"
        f"{json.dumps(state['clinical_context'], indent=2)}\n\n"
        f"Triage decision:\n"
        f"{json.dumps(dict(state['triage_decision']), indent=2)}"
    )

    # --- Sidecar hook (Layer 1 placeholder for Prompt 3) ---
    validated_input = user_message

    response = await anthropic_client.complete(
        model=model,
        system_prompt=HALLUCINATION_CHECK_PROMPT,
        user_message=validated_input,
        max_tokens=1024,
    )

    validation = json.loads(response["content"])

    hallucination_score = validation["hallucination_score"]
    confidence_score = validation["confidence_assessment"]
    vitals_ok = validation["vitals_consistent"]
    meds_ok = validation["medication_safe"]

    # Circuit breaker: hallucination > 0.15 OR confidence < 0.85
    circuit_breaker_tripped = (
        hallucination_score > settings.hallucination_threshold
        or confidence_score < settings.confidence_threshold
    )

    failure_reasons: list[str] = []
    if hallucination_score > settings.hallucination_threshold:
        failure_reasons.append(
            f"Hallucination score {hallucination_score:.2f} exceeds "
            f"threshold {settings.hallucination_threshold}"
        )
    if confidence_score < settings.confidence_threshold:
        failure_reasons.append(
            f"Confidence {confidence_score:.2f} below "
            f"threshold {settings.confidence_threshold}"
        )
    if not vitals_ok:
        failure_reasons.append("Vitals inconsistent with triage level")
    if not meds_ok:
        failure_reasons.append("Medication safety concern detected")

    sentinel_check: SentinelCheck = {
        "passed": not circuit_breaker_tripped,
        "hallucination_score": hallucination_score,
        "confidence_score": confidence_score,
        "vitals_cross_ref_passed": vitals_ok,
        "medication_safety_passed": meds_ok,
        "circuit_breaker_tripped": circuit_breaker_tripped,
        "failure_reasons": failure_reasons,
    }

    audit_ref = await audit_writer.write_node_audit(
        encounter_id=encounter_id,
        node_name="sentinel",
        model=response["model"],
        routing_decision={
            "category": state["routing_metadata"]["category"],
            "confidence": state["routing_metadata"]["classifier_confidence"],
            "reason": "sentinel_validation",
        },
        input_summary=user_message[:500],
        output_summary=json.dumps(validation)[:500],
        tokens=response["tokens"],
        cost_usd=response["cost_usd"],
        compliance_flags=state.get("compliance_flags", []),
        sentinel_check=sentinel_check,
        duration_ms=response["duration_ms"],
    )

    return {
        "sentinel_check": sentinel_check,
        "circuit_breaker_tripped": circuit_breaker_tripped,
        "audit_trail": state.get("audit_trail", [])
        + [
            {
                "encounter_id": encounter_id,
                "node": "sentinel",
                "model": response["model"],
                "tokens": response["tokens"],
                "cost_usd": response["cost_usd"],
                "duration_ms": response["duration_ms"],
                "audit_ref": audit_ref,
            }
        ],
    }

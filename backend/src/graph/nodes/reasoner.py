import json
import logging
from typing import Any

from src.audit.writer import AuditWriter
from src.graph.state import AgentState, TriageDecision
from src.services.anthropic_client import AnthropicClient
from src.services.sidecar_client import SidecarClient

logger = logging.getLogger(__name__)

REASONER_SYSTEM_PROMPT = """You are a clinical triage reasoning specialist. Based on the extracted \
clinical data, determine the triage level.

Triage levels:
- Emergency: Life-threatening, requires immediate intervention
- Urgent: Serious condition, needs attention within 1-2 hours
- Semi-Urgent: Moderate condition, can wait 2-4 hours
- Non-Urgent: Minor condition, can be scheduled normally

Respond with JSON:
{
  "level": "Emergency|Urgent|Semi-Urgent|Non-Urgent",
  "confidence": <0.0-1.0>,
  "reasoning_summary": "Brief clinical reasoning",
  "recommended_actions": ["action1", "action2"],
  "key_findings": ["finding1", "finding2"]
}

Be conservative: when in doubt, escalate to a higher triage level."""

MAX_RETRIES = 2


async def reasoner_node(
    state: AgentState,
    *,
    anthropic_client: AnthropicClient,
    audit_writer: AuditWriter,
    sidecar_client: SidecarClient | None = None,
) -> dict[str, Any]:
    """Produce triage decision from extracted clinical data."""
    model = state["routing_metadata"]["selected_model"]
    encounter_id = state["encounter_id"]

    # RAG context placeholder
    rag_context = state.get("rag_context", [])
    rag_section = ""
    if rag_context:
        rag_section = "\n\nSimilar cases for reference:\n" + json.dumps(rag_context)

    user_message = (
        f"Clinical data:\n{json.dumps(state['clinical_context'], indent=2)}"
        f"{rag_section}"
    )

    # --- Sidecar: validate input (PII scan) ---
    compliance_flags: list[str] = list(state.get("compliance_flags", []))
    validated_input = user_message

    if sidecar_client:
        input_result = await sidecar_client.validate(
            content=user_message,
            node_name="reasoner",
            encounter_id=encounter_id,
            validation_type="input",
        )
        validated_input = input_result.content
        compliance_flags.extend(input_result.compliance_flags)

    # LLM call with retry on FHIR validation failure
    response = None
    decision = None

    for attempt in range(1 + MAX_RETRIES):
        response = await anthropic_client.complete(
            model=model,
            system_prompt=REASONER_SYSTEM_PROMPT,
            user_message=validated_input,
        )

        # --- Sidecar: validate output (PII + FHIR + token guard) ---
        if sidecar_client:
            output_result = await sidecar_client.validate(
                content=response["content"],
                node_name="reasoner",
                encounter_id=encounter_id,
                validation_type="output",
                tokens=response["tokens"],
            )
            compliance_flags.extend(output_result.compliance_flags)

            if output_result.should_retry and attempt < MAX_RETRIES:
                logger.warning(
                    "FHIR validation failed for reasoner (attempt %d/%d): %s",
                    attempt + 1,
                    MAX_RETRIES,
                    output_result.errors,
                )
                continue

            if not output_result.validated and attempt == MAX_RETRIES:
                compliance_flags.append("FHIR_RETRY_EXHAUSTED")
                logger.error(
                    "FHIR validation failed after %d retries for reasoner: %s",
                    MAX_RETRIES,
                    output_result.errors,
                )

        break

    try:
        decision = json.loads(response["content"])
        triage_decision: TriageDecision = {
            "level": decision["level"],
            "confidence": decision["confidence"],
            "reasoning_summary": decision["reasoning_summary"],
            "recommended_actions": decision.get("recommended_actions", []),
            "model_used": response["model"],
            "routing_reason": state["routing_metadata"].get(
                "escalation_reason", "default routing"
            ),
        }
    except (json.JSONDecodeError, KeyError) as exc:
        logger.error(
            "Reasoner JSON parse failed for %s — tripping circuit breaker: %s",
            encounter_id,
            exc,
        )
        compliance_flags.append("JSON_PARSE_FAILED")
        decision = {}
        triage_decision = TriageDecision(
            level="Manual_Review_Required",
            confidence=0.0,
            reasoning_summary=f"Reasoner parse error: {type(exc).__name__}",
            recommended_actions=["Manual clinical review required"],
            model_used=response["model"],
            routing_reason="parse_failure_fallback",
        )

    audit_ref = await audit_writer.write_node_audit(
        encounter_id=encounter_id,
        node_name="reasoner",
        model=response["model"],
        routing_decision={
            "category": state["routing_metadata"]["category"],
            "confidence": state["routing_metadata"]["classifier_confidence"],
            "reason": state["routing_metadata"].get("escalation_reason"),
        },
        input_summary=user_message[:500],
        output_summary=json.dumps(decision)[:500],
        tokens=response["tokens"],
        cost_usd=response["cost_usd"],
        compliance_flags=compliance_flags,
        sentinel_check=None,
        duration_ms=response["duration_ms"],
    )

    result: dict[str, Any] = {
        "triage_decision": triage_decision,
        "compliance_flags": compliance_flags,
        "audit_trail": state.get("audit_trail", [])
        + [
            {
                "encounter_id": encounter_id,
                "node": "reasoner",
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
        result["error"] = "Reasoner failed to parse LLM output"

    return result

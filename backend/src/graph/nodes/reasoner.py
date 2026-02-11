import json
import logging
from typing import Any

from src.audit.writer import AuditWriter
from src.graph.state import AgentState, TriageDecision
from src.services.anthropic_client import AnthropicClient

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


async def reasoner_node(
    state: AgentState,
    *,
    anthropic_client: AnthropicClient,
    audit_writer: AuditWriter,
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

    # --- Sidecar hook (Layer 1 placeholder for Prompt 3) ---
    validated_input = user_message

    response = await anthropic_client.complete(
        model=model,
        system_prompt=REASONER_SYSTEM_PROMPT,
        user_message=validated_input,
    )

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
        compliance_flags=state.get("compliance_flags", []),
        sentinel_check=None,
        duration_ms=response["duration_ms"],
    )

    return {
        "triage_decision": triage_decision,
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

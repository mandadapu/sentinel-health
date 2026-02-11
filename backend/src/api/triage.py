from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from src.graph.state import AgentState
from src.models import TriageRequest, TriageResultResponse

router = APIRouter(prefix="/api")

# These are set by main.py at startup
_pipeline = None
_audit_writer = None
_firestore = None


def set_dependencies(pipeline, audit_writer, firestore) -> None:
    global _pipeline, _audit_writer, _firestore
    _pipeline = pipeline
    _audit_writer = audit_writer
    _firestore = firestore


@router.post("/triage", response_model=TriageResultResponse)
async def run_triage(request: TriageRequest) -> TriageResultResponse:
    """Run the full triage pipeline on an encounter."""
    if _pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    initial_state: AgentState = {
        "raw_input": request.encounter_text,
        "encounter_id": request.encounter_id,
        "patient_id": request.patient_id,
        "audit_trail": [],
        "compliance_flags": [],
        "circuit_breaker_tripped": False,
        "error": None,
    }

    result = await _pipeline.ainvoke(initial_state)

    triage = result.get("triage_decision", {})
    sentinel = result.get("sentinel_check", {})
    audit_trail = result.get("audit_trail", [])
    audit_ref = audit_trail[-1]["audit_ref"] if audit_trail else ""

    # Publish TriageCompleted event to Pub/Sub
    await _audit_writer.publish_triage_completed(
        encounter_id=request.encounter_id,
        patient_id=request.patient_id,
        triage_result={
            "level": triage.get("level", "Unknown"),
            "confidence": triage.get("confidence", 0.0),
            "reasoning_summary": triage.get("reasoning_summary", ""),
            "model_used": triage.get("model_used", ""),
            "routing_reason": triage.get("routing_reason", ""),
        },
        sentinel_check={
            "passed": sentinel.get("passed", False),
            "hallucination_score": sentinel.get("hallucination_score", 1.0),
            "confidence_score": sentinel.get("confidence_score", 0.0),
        },
        audit_ref=audit_ref,
    )

    # Write session status to Firestore
    await _firestore.write_session(
        request.encounter_id,
        {
            "status": "completed",
            "triage_level": triage.get("level", "Unknown"),
            "circuit_breaker_tripped": result.get("circuit_breaker_tripped", False),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    return TriageResultResponse(
        encounter_id=request.encounter_id,
        patient_id=request.patient_id,
        triage_level=triage.get("level", "Unknown"),
        confidence=triage.get("confidence", 0.0),
        reasoning_summary=triage.get("reasoning_summary", ""),
        model_used=triage.get("model_used", ""),
        routing_category=result.get("routing_metadata", {}).get("category", ""),
        sentinel_passed=sentinel.get("passed", False),
        hallucination_score=sentinel.get("hallucination_score", 1.0),
        circuit_breaker_tripped=result.get("circuit_breaker_tripped", False),
        audit_ref=audit_ref,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

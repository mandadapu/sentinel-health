from typing import Any, TypedDict


class RoutingMetadata(TypedDict, total=False):
    category: str
    classifier_confidence: float
    selected_model: str
    escalation_reason: str | None
    safety_override: bool


class AuditEntry(TypedDict):
    encounter_id: str
    node: str
    model: str
    tokens: dict[str, int]
    cost_usd: float
    duration_ms: int
    audit_ref: str


class SentinelCheck(TypedDict):
    passed: bool
    hallucination_score: float
    confidence_score: float
    vitals_cross_ref_passed: bool
    medication_safety_passed: bool
    circuit_breaker_tripped: bool
    failure_reasons: list[str]


class TriageDecision(TypedDict, total=False):
    level: str
    confidence: float
    reasoning_summary: str
    recommended_actions: list[str]
    model_used: str
    routing_reason: str


class AgentState(TypedDict, total=False):
    # Input
    raw_input: str
    encounter_id: str
    patient_id: str

    # Extracted data
    fhir_data: dict[str, Any]
    clinical_context: dict[str, Any]

    # RAG context (placeholder)
    rag_context: list[dict[str, Any]]

    # Triage output
    triage_decision: TriageDecision

    # Sentinel validation
    sentinel_check: SentinelCheck

    # Routing
    routing_metadata: RoutingMetadata

    # Audit
    audit_trail: list[AuditEntry]

    # Compliance
    compliance_flags: list[str]

    # Pipeline control
    circuit_breaker_tripped: bool
    error: str | None

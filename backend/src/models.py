import re
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator

# Patterns that indicate prompt injection attempts
_INJECTION_PATTERNS = re.compile(
    r"(?:ignore\s+(?:all\s+)?previous\s+instructions"
    r"|you\s+are\s+now\s+(?:a\s+)?(?:different|new)\s+(?:ai|assistant|model)"
    r"|system\s*:\s*you\s+are"
    r"|<\s*(?:system|admin|root)\s*>"
    r"|IGNORE\s+ALL\s+RULES"
    r"|override\s+(?:safety|content)\s+(?:filter|policy))",
    re.IGNORECASE,
)


class TriageRequest(BaseModel):
    encounter_text: str = Field(..., min_length=10, max_length=50_000)
    patient_id: str = Field(..., description="Encrypted patient reference")
    encounter_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("encounter_text")
    @classmethod
    def check_prompt_injection(cls, v: str) -> str:
        if _INJECTION_PATTERNS.search(v):
            raise ValueError("Input contains disallowed instruction patterns")
        return v


class TriageResultResponse(BaseModel):
    encounter_id: str
    patient_id: str
    triage_level: str
    confidence: float
    reasoning_summary: str
    model_used: str
    routing_category: str
    sentinel_passed: bool
    hallucination_score: float
    circuit_breaker_tripped: bool
    audit_ref: str
    timestamp: str


class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "0.1.0"
    environment: str
    checks: dict[str, str] = Field(default_factory=dict)
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

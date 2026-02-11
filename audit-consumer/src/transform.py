"""Transform Pub/Sub audit doc to BigQuery audit_trail row."""

import json


def transform_audit_event(doc: dict) -> dict:
    """Map audit event fields to BigQuery audit_trail schema."""
    routing = doc.get("routing_decision") or {}
    tokens = doc.get("tokens") or {}
    sentinel = doc.get("sentinel_check") or {}

    return {
        "encounter_id": doc["encounter_id"],
        "node_name": doc.get("node", ""),
        "model_used": doc.get("model", ""),
        "routing_category": routing.get("category"),
        "routing_confidence": routing.get("confidence"),
        "input_tokens": tokens.get("in"),
        "output_tokens": tokens.get("out"),
        "cost_usd": doc.get("cost_usd"),
        "reasoning_snapshot": json.dumps(doc),
        "compliance_flags": doc.get("compliance_flags", []),
        "sentinel_hallucination_score": sentinel.get("hallucination_score"),
        "sentinel_confidence_score": sentinel.get("confidence_score"),
        "circuit_breaker_tripped": sentinel.get("circuit_breaker_tripped"),
        "duration_ms": doc.get("duration_ms"),
        "created_at": doc.get("timestamp"),
    }

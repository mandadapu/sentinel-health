from dataclasses import dataclass

from src.graph.state import RoutingMetadata

CRITICAL_KEYWORDS = [
    "chest pain", "difficulty breathing", "unconscious", "seizure",
    "severe bleeding", "anaphylaxis", "stroke", "cardiac arrest",
    "respiratory failure", "sepsis", "trauma", "suicidal",
]

MODEL_TIERS = [
    "claude-haiku-4-5-20241022",
    "claude-sonnet-4-5-20250929",
    "claude-opus-4-6-20250929",
]


@dataclass(frozen=True)
class CategoryConfig:
    default_model: str
    escalation_threshold: float
    safety_override: bool


CATEGORY_ROUTING: dict[str, CategoryConfig] = {
    # Haiku tier — routine, low-risk
    "routine_vitals":            CategoryConfig("claude-haiku-4-5-20241022",  0.65, False),
    "chronic_management":        CategoryConfig("claude-haiku-4-5-20241022",  0.60, False),
    # Sonnet tier — moderate complexity
    "symptom_assessment":        CategoryConfig("claude-sonnet-4-5-20250929", 0.55, True),
    "medication_review":         CategoryConfig("claude-sonnet-4-5-20250929", 0.50, True),
    "diagnostic_interpretation": CategoryConfig("claude-sonnet-4-5-20250929", 0.45, True),
    # Opus tier — always Opus, high-acuity (threshold irrelevant, already top tier)
    "acute_presentation":        CategoryConfig("claude-opus-4-6-20250929",   0.0, True),
    "critical_emergency":        CategoryConfig("claude-opus-4-6-20250929",   0.0, True),
    "mental_health":             CategoryConfig("claude-opus-4-6-20250929",   0.0, True),
    "pediatric":                 CategoryConfig("claude-opus-4-6-20250929",   0.0, True),
    "surgical_consult":          CategoryConfig("claude-opus-4-6-20250929",   0.0, True),
}


class ModelRouter:
    def __init__(self, min_confidence: float = 0.70) -> None:
        self._min_confidence = min_confidence

    def route(self, encounter_text: str, classification: dict) -> RoutingMetadata:
        category = classification["category"]
        confidence = classification["confidence"]

        # Safety override: critical keywords -> always Opus
        if self._has_critical_keywords(encounter_text):
            return RoutingMetadata(
                category=category,
                classifier_confidence=confidence,
                selected_model="claude-opus-4-6-20250929",
                escalation_reason="Critical keyword safety override",
                safety_override=True,
            )

        config = CATEGORY_ROUTING.get(category)
        if config is None:
            return RoutingMetadata(
                category=category,
                classifier_confidence=confidence,
                selected_model="claude-sonnet-4-5-20250929",
                escalation_reason="Unknown category fallback",
                safety_override=False,
            )

        selected_model = config.default_model

        # Escalation: confidence < category threshold -> go up one tier
        if confidence < config.escalation_threshold:
            current_idx = MODEL_TIERS.index(selected_model)
            if current_idx < len(MODEL_TIERS) - 1:
                selected_model = MODEL_TIERS[current_idx + 1]

        # Global minimum: confidence < 0.70 -> at least Sonnet
        if confidence < self._min_confidence:
            sonnet_idx = MODEL_TIERS.index("claude-sonnet-4-5-20250929")
            current_idx = MODEL_TIERS.index(selected_model)
            if current_idx < sonnet_idx:
                selected_model = MODEL_TIERS[sonnet_idx]

        # Safety override categories: ensure at least Sonnet
        if config.safety_override:
            sonnet_idx = MODEL_TIERS.index("claude-sonnet-4-5-20250929")
            current_idx = MODEL_TIERS.index(selected_model)
            if current_idx < sonnet_idx:
                selected_model = MODEL_TIERS[sonnet_idx]

        escalation_reason = None
        if confidence < config.escalation_threshold:
            escalation_reason = (
                f"Confidence {confidence:.2f} below threshold "
                f"{config.escalation_threshold}"
            )

        return RoutingMetadata(
            category=category,
            classifier_confidence=confidence,
            selected_model=selected_model,
            escalation_reason=escalation_reason,
            safety_override=False,
        )

    def _has_critical_keywords(self, text: str) -> bool:
        text_lower = text.lower()
        return any(kw in text_lower for kw in CRITICAL_KEYWORDS)

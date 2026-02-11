"""Pure logic tests for ModelRouter — no LLM calls needed."""

import pytest

from src.routing.router import (
    CATEGORY_ROUTING,
    CRITICAL_KEYWORDS,
    MODEL_TIERS,
    ModelRouter,
)


@pytest.fixture
def router():
    return ModelRouter(min_confidence=0.70)


class TestCriticalKeywordOverride:
    """Critical keywords → always Opus, regardless of category or confidence."""

    @pytest.mark.parametrize(
        "keyword",
        ["chest pain", "stroke", "cardiac arrest", "seizure", "suicidal"],
    )
    def test_critical_keyword_selects_opus(self, router, keyword):
        result = router.route(
            f"Patient presents with {keyword}",
            {"category": "routine_vitals", "confidence": 0.99},
        )
        assert result["selected_model"] == "claude-opus-4-6-20250929"
        assert result["safety_override"] is True
        assert result["escalation_reason"] == "Critical keyword safety override"

    def test_critical_keyword_case_insensitive(self, router):
        result = router.route(
            "PATIENT HAS CHEST PAIN AND DIFFICULTY BREATHING",
            {"category": "routine_vitals", "confidence": 0.99},
        )
        assert result["selected_model"] == "claude-opus-4-6-20250929"
        assert result["safety_override"] is True

    def test_no_critical_keywords(self, router):
        result = router.route(
            "Patient has mild headache",
            {"category": "routine_vitals", "confidence": 0.95},
        )
        assert result["safety_override"] is False


class TestCategoryRouting:
    """Each category maps to the correct default model."""

    def test_routine_vitals_defaults_to_haiku(self, router):
        result = router.route(
            "Normal checkup",
            {"category": "routine_vitals", "confidence": 0.95},
        )
        assert result["selected_model"] == "claude-haiku-4-5-20241022"

    def test_symptom_assessment_defaults_to_sonnet(self, router):
        result = router.route(
            "Patient reports headache",
            {"category": "symptom_assessment", "confidence": 0.90},
        )
        assert result["selected_model"] == "claude-sonnet-4-5-20250929"

    def test_critical_emergency_defaults_to_opus(self, router):
        # No critical keywords in text, but category is critical_emergency
        result = router.route(
            "Patient in distress",
            {"category": "critical_emergency", "confidence": 0.95},
        )
        assert result["selected_model"] == "claude-opus-4-6-20250929"

    def test_unknown_category_falls_back_to_sonnet(self, router):
        result = router.route(
            "Something unusual",
            {"category": "unknown_category", "confidence": 0.90},
        )
        assert result["selected_model"] == "claude-sonnet-4-5-20250929"
        assert result["escalation_reason"] == "Unknown category fallback"


class TestConfidenceEscalation:
    """Low confidence → escalate one tier."""

    def test_haiku_escalates_to_sonnet(self, router):
        # routine_vitals: threshold 0.85, default haiku
        result = router.route(
            "Routine check",
            {"category": "routine_vitals", "confidence": 0.80},
        )
        assert result["selected_model"] == "claude-sonnet-4-5-20250929"
        assert "0.80" in result["escalation_reason"]

    def test_sonnet_escalates_to_opus(self, router):
        # symptom_assessment: threshold 0.75, default sonnet
        result = router.route(
            "Patient reports symptoms",
            {"category": "symptom_assessment", "confidence": 0.70},
        )
        assert result["selected_model"] == "claude-opus-4-6-20250929"

    def test_opus_stays_at_opus(self, router):
        # critical_emergency: already opus, can't escalate further
        result = router.route(
            "Patient in distress",
            {"category": "critical_emergency", "confidence": 0.40},
        )
        assert result["selected_model"] == "claude-opus-4-6-20250929"

    def test_high_confidence_no_escalation(self, router):
        result = router.route(
            "Normal vitals",
            {"category": "routine_vitals", "confidence": 0.95},
        )
        assert result["selected_model"] == "claude-haiku-4-5-20241022"
        assert result["escalation_reason"] is None


class TestGlobalMinimumConfidence:
    """Confidence < 0.70 → at least Sonnet."""

    def test_very_low_confidence_forces_sonnet(self, router):
        result = router.route(
            "Unclear presentation",
            {"category": "routine_vitals", "confidence": 0.50},
        )
        # Haiku would escalate to Sonnet by threshold, AND global minimum applies
        assert result["selected_model"] in [
            "claude-sonnet-4-5-20250929",
            "claude-opus-4-6-20250929",
        ]

    def test_confidence_above_minimum_allows_haiku(self, router):
        result = router.route(
            "Clear presentation",
            {"category": "routine_vitals", "confidence": 0.95},
        )
        assert result["selected_model"] == "claude-haiku-4-5-20241022"


class TestSafetyOverrideCategories:
    """Categories with safety_override=True ensure at least Sonnet."""

    @pytest.mark.parametrize(
        "category",
        ["medication_review", "acute_presentation", "critical_emergency",
         "mental_health", "pediatric"],
    )
    def test_safety_categories_at_least_sonnet(self, router, category):
        result = router.route(
            "Standard encounter",
            {"category": category, "confidence": 0.99},
        )
        model_idx = MODEL_TIERS.index(result["selected_model"])
        sonnet_idx = MODEL_TIERS.index("claude-sonnet-4-5-20250929")
        assert model_idx >= sonnet_idx


class TestRoutingMetadataFields:
    """Verify RoutingMetadata structure is complete."""

    def test_metadata_has_all_fields(self, router):
        result = router.route(
            "Patient with cough",
            {"category": "symptom_assessment", "confidence": 0.90},
        )
        assert "category" in result
        assert "classifier_confidence" in result
        assert "selected_model" in result
        assert "escalation_reason" in result
        assert "safety_override" in result

    def test_confidence_is_preserved(self, router):
        result = router.route(
            "Patient with cough",
            {"category": "symptom_assessment", "confidence": 0.87},
        )
        assert result["classifier_confidence"] == 0.87
        assert result["category"] == "symptom_assessment"


class TestRoutingTableCoverage:
    """Ensure all 10 categories are covered in the routing table."""

    def test_all_categories_present(self):
        expected = {
            "routine_vitals", "chronic_management", "symptom_assessment",
            "medication_review", "diagnostic_interpretation", "acute_presentation",
            "critical_emergency", "mental_health", "pediatric", "surgical_consult",
        }
        assert set(CATEGORY_ROUTING.keys()) == expected

    def test_critical_keywords_non_empty(self):
        assert len(CRITICAL_KEYWORDS) > 0
        assert "chest pain" in CRITICAL_KEYWORDS
        assert "stroke" in CRITICAL_KEYWORDS

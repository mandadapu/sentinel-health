import json
import logging

from src.services.anthropic_client import AnthropicClient

logger = logging.getLogger(__name__)

CLINICAL_CATEGORIES = [
    "routine_vitals",
    "chronic_management",
    "symptom_assessment",
    "medication_review",
    "diagnostic_interpretation",
    "acute_presentation",
    "critical_emergency",
    "mental_health",
    "pediatric",
    "surgical_consult",
]

CLASSIFIER_SYSTEM_PROMPT = """You are a clinical encounter classifier. Given raw encounter text, classify it into exactly ONE category and provide a confidence score.

Categories: {categories}

Respond ONLY with valid JSON:
{{"category": "<category>", "confidence": <0.0-1.0>, "reason": "<brief reason>"}}"""


class ClinicalClassifier:
    def __init__(self, client: AnthropicClient, model: str) -> None:
        self._client = client
        self._model = model

    async def classify(self, encounter_text: str, timeout: float = 5.0) -> dict:
        try:
            response = await self._client.complete(
                model=self._model,
                system_prompt=CLASSIFIER_SYSTEM_PROMPT.format(
                    categories=", ".join(CLINICAL_CATEGORIES)
                ),
                user_message=encounter_text,
                max_tokens=256,
                temperature=0.0,
                timeout=timeout,
            )
        except Exception as exc:
            logger.warning(
                "Classifier call failed — falling back to default routing: %s", exc
            )
            return {
                "category": "symptom_assessment",
                "confidence": 0.0,
                "reason": f"classifier_timeout: {type(exc).__name__}",
                "classifier_tokens": {"in": 0, "out": 0},
                "classifier_cost": 0.0,
            }
        try:
            parsed = json.loads(response["content"])
            return {
                "category": parsed["category"],
                "confidence": parsed["confidence"],
                "reason": parsed["reason"],
                "classifier_tokens": response["tokens"],
                "classifier_cost": response["cost_usd"],
            }
        except (json.JSONDecodeError, KeyError) as exc:
            logger.error(
                "Classifier JSON parse failed — falling back to default routing: %s",
                exc,
            )
            return {
                "category": "symptom_assessment",
                "confidence": 0.0,
                "reason": f"classifier_parse_error: {type(exc).__name__}",
                "classifier_tokens": response["tokens"],
                "classifier_cost": response["cost_usd"],
            }

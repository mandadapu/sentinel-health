import json

from src.services.anthropic_client import AnthropicClient

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

    async def classify(self, encounter_text: str) -> dict:
        response = await self._client.complete(
            model=self._model,
            system_prompt=CLASSIFIER_SYSTEM_PROMPT.format(
                categories=", ".join(CLINICAL_CATEGORIES)
            ),
            user_message=encounter_text,
            max_tokens=256,
            temperature=0.0,
        )
        parsed = json.loads(response["content"])
        return {
            "category": parsed["category"],
            "confidence": parsed["confidence"],
            "reason": parsed["reason"],
            "classifier_tokens": response["tokens"],
            "classifier_cost": response["cost_usd"],
        }

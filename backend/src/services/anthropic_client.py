import time

from anthropic import AsyncAnthropic

from src.config import Settings

MODEL_PRICING: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5-20241022": (1.00, 5.00),
    "claude-sonnet-4-5-20250929": (3.00, 15.00),
    "claude-opus-4-6-20250929": (15.00, 75.00),
}


class AnthropicClient:
    def __init__(self, settings: Settings) -> None:
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def complete(
        self,
        model: str,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> dict:
        start = time.monotonic()
        response = await self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        duration_ms = int((time.monotonic() - start) * 1000)

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        pricing = MODEL_PRICING.get(model, (0.0, 0.0))
        cost_usd = (input_tokens * pricing[0] + output_tokens * pricing[1]) / 1_000_000

        return {
            "content": response.content[0].text,
            "model": model,
            "tokens": {"in": input_tokens, "out": output_tokens},
            "cost_usd": round(cost_usd, 8),
            "duration_ms": duration_ms,
            "stop_reason": response.stop_reason,
        }

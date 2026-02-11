import logging
from typing import Any

import httpx

from src.config import Settings

logger = logging.getLogger(__name__)


class SidecarValidationResult:
    """Typed wrapper around sidecar /validate response."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.validated: bool = data["validated"]
        self.content: str = data["content"]
        self.compliance_flags: list[str] = data.get("compliance_flags", [])
        self.redactions: list[dict] = data.get("redactions", [])
        self.errors: list[str] = data.get("errors", [])
        self.should_retry: bool = data.get("should_retry", False)
        self.latency_ms: float = data.get("latency_ms", 0.0)


class SidecarClient:
    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.sidecar_url
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(5.0, connect=2.0),
        )

    async def validate(
        self,
        content: str,
        node_name: str,
        encounter_id: str,
        validation_type: str,
        tokens: dict[str, int] | None = None,
    ) -> SidecarValidationResult:
        """Call sidecar /validate. On failure, return a pass-through result."""
        payload = {
            "content": content,
            "node_name": node_name,
            "encounter_id": encounter_id,
            "validation_type": validation_type,
            "tokens": tokens or {"in": 0, "out": 0},
        }
        try:
            response = await self._client.post("/validate", json=payload)
            response.raise_for_status()
            return SidecarValidationResult(response.json())
        except Exception:
            logger.exception(
                "Sidecar validation failed for %s/%s — passing through",
                encounter_id,
                node_name,
            )
            # Fail-open: return original content with a warning flag
            return SidecarValidationResult(
                {
                    "validated": True,
                    "content": content,
                    "compliance_flags": ["SIDECAR_UNAVAILABLE"],
                    "redactions": [],
                    "errors": [],
                    "should_retry": False,
                    "latency_ms": 0.0,
                }
            )

    async def close(self) -> None:
        await self._client.aclose()

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from src.services.firestore import FirestoreService
from src.services.pubsub import PubSubService

if TYPE_CHECKING:
    from src.services.sidecar_client import SidecarClient

logger = logging.getLogger(__name__)


class AuditWriter:
    def __init__(
        self,
        firestore: FirestoreService,
        pubsub: PubSubService,
        sidecar_client: SidecarClient | None = None,
    ) -> None:
        self._firestore = firestore
        self._pubsub = pubsub
        self._sidecar = sidecar_client

    async def write_node_audit(
        self,
        encounter_id: str,
        node_name: str,
        model: str,
        routing_decision: dict[str, Any],
        input_summary: str,
        output_summary: str,
        tokens: dict[str, int],
        cost_usd: float,
        compliance_flags: list[str],
        sentinel_check: dict[str, Any] | None,
        duration_ms: int,
    ) -> str:
        timestamp = datetime.now(timezone.utc).isoformat()

        # PHI strip input_summary and output_summary before persistence
        if self._sidecar:
            input_strip = await self._sidecar.validate(
                content=input_summary,
                node_name=node_name,
                encounter_id=encounter_id,
                validation_type="audit",
            )
            input_summary = input_strip.content
            compliance_flags = list(compliance_flags) + input_strip.compliance_flags

            output_strip = await self._sidecar.validate(
                content=output_summary,
                node_name=node_name,
                encounter_id=encounter_id,
                validation_type="audit",
            )
            output_summary = output_strip.content
            compliance_flags = compliance_flags + output_strip.compliance_flags

        audit_doc = {
            "encounter_id": encounter_id,
            "node": node_name,
            "model": model,
            "routing_decision": routing_decision,
            "input_summary": input_summary,
            "output_summary": output_summary,
            "tokens": tokens,
            "cost_usd": cost_usd,
            "compliance_flags": compliance_flags,
            "sentinel_check": sentinel_check,
            "duration_ms": duration_ms,
            "timestamp": timestamp,
        }

        # Sync write to Firestore
        doc_path = await self._firestore.write_audit(
            encounter_id, node_name, audit_doc
        )

        # Async fire-and-forget to Pub/Sub
        asyncio.create_task(self._safe_publish(audit_doc))

        return doc_path

    async def publish_triage_completed(
        self,
        encounter_id: str,
        patient_id: str,
        triage_result: dict,
        sentinel_check: dict,
        audit_ref: str,
    ) -> None:
        event = {
            "encounter_id": encounter_id,
            "patient_id": patient_id,
            "triage_result": triage_result,
            "sentinel_check": sentinel_check,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "audit_ref": audit_ref,
        }
        await self._pubsub.publish_triage_completed(event)

    async def _safe_publish(self, data: dict) -> None:
        try:
            await self._pubsub.publish_audit_event(data)
        except Exception:
            logger.exception("Failed to publish audit event to Pub/Sub")

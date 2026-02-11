import asyncio
import json

from google.cloud.pubsub_v1 import PublisherClient

from src.config import Settings


class PubSubService:
    def __init__(self, settings: Settings) -> None:
        self._publisher = PublisherClient()
        self._project = settings.gcp_project_id
        self._audit_topic = (
            f"projects/{settings.gcp_project_id}/topics/{settings.pubsub_audit_topic}"
        )
        self._triage_topic = (
            f"projects/{settings.gcp_project_id}/topics/"
            f"{settings.pubsub_triage_completed_topic}"
        )

    async def publish_audit_event(self, data: dict) -> None:
        loop = asyncio.get_running_loop()
        future = self._publisher.publish(
            self._audit_topic,
            json.dumps(data).encode("utf-8"),
        )
        await loop.run_in_executor(None, future.result, 5)

    async def publish_triage_completed(self, data: dict) -> None:
        loop = asyncio.get_running_loop()
        future = self._publisher.publish(
            self._triage_topic,
            json.dumps(data).encode("utf-8"),
        )
        await loop.run_in_executor(None, future.result, 10)

import asyncio
import json

from google.cloud.pubsub_v1 import PublisherClient

from src.config import WorkerSettings


class ApprovalPubSub:
    def __init__(self, settings: WorkerSettings) -> None:
        self._publisher = PublisherClient()
        self._approved_topic = settings.pubsub_triage_approved_topic
        self._audit_events_topic = settings.pubsub_audit_events_topic

    async def publish_triage_approved(self, data: dict) -> None:
        loop = asyncio.get_running_loop()
        future = self._publisher.publish(
            self._approved_topic,
            json.dumps(data).encode("utf-8"),
        )
        await loop.run_in_executor(None, future.result, 10)

    async def publish_classifier_feedback(self, data: dict) -> None:
        loop = asyncio.get_running_loop()
        future = self._publisher.publish(
            self._audit_events_topic,
            json.dumps(data).encode("utf-8"),
        )
        await loop.run_in_executor(None, future.result, 10)

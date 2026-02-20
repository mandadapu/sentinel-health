import asyncio
import json
import logging

from google.cloud.pubsub_v1 import PublisherClient
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.config import Settings

logger = logging.getLogger(__name__)


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

    async def _publish(self, topic: str, data: dict, timeout: int) -> None:
        loop = asyncio.get_running_loop()
        future = self._publisher.publish(
            topic,
            json.dumps(data).encode("utf-8"),
        )
        await loop.run_in_executor(None, future.result, timeout)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type(Exception),
        reraise=True,
        before_sleep=lambda rs: logger.warning(
            "Retrying Pub/Sub audit publish (attempt %d): %s",
            rs.attempt_number,
            rs.outcome.exception(),
        ),
    )
    async def publish_audit_event(self, data: dict) -> None:
        await self._publish(self._audit_topic, data, timeout=5)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type(Exception),
        reraise=True,
        before_sleep=lambda rs: logger.warning(
            "Retrying Pub/Sub triage-completed publish (attempt %d): %s",
            rs.attempt_number,
            rs.outcome.exception(),
        ),
    )
    async def publish_triage_completed(self, data: dict) -> None:
        await self._publish(self._triage_topic, data, timeout=10)

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from src.services.firestore import FirestoreService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

_firestore: FirestoreService | None = None


def set_dependencies(firestore: FirestoreService | None) -> None:
    global _firestore
    _firestore = firestore


@router.get("/stream/triage-results")
async def stream_triage_results() -> EventSourceResponse:
    """SSE stream of triage session changes via Firestore watch."""

    async def event_generator():
        yield {"event": "connected", "data": json.dumps({"status": "stream_ready"})}

        if _firestore is None:
            logger.warning("Firestore not available — SSE falling back to heartbeat only")
            while True:
                await asyncio.sleep(30)
                yield {"event": "heartbeat", "data": json.dumps({"status": "alive"})}
            return

        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        watch = _firestore.watch_collection(queue)

        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield {
                        "event": event["event"],
                        "data": json.dumps(event["data"], default=str),
                    }
                except asyncio.TimeoutError:
                    yield {"event": "heartbeat", "data": json.dumps({"status": "alive"})}
        finally:
            watch.unsubscribe()

    return EventSourceResponse(event_generator())

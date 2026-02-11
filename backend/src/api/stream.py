import json

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/api")

# Set by main.py at startup
_firestore = None


def set_dependencies(firestore) -> None:
    global _firestore
    _firestore = firestore


@router.get("/stream/triage-results")
async def stream_triage_results():
    """SSE stream of completed triage results via Firestore watch."""

    async def event_generator():
        # Placeholder: in production this watches Firestore for new documents.
        # For now, yields nothing until Firestore watch is implemented with
        # the on_snapshot callback-to-async-generator bridge.
        yield {
            "event": "connected",
            "data": json.dumps({"status": "stream_ready"}),
        }
        # The actual Firestore watch will be implemented when the frontend
        # (Prompt 4) needs to consume this endpoint.
        import asyncio

        while True:
            await asyncio.sleep(30)
            yield {
                "event": "heartbeat",
                "data": json.dumps({"status": "alive"}),
            }

    return EventSourceResponse(event_generator())

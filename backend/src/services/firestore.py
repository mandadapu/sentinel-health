import asyncio
from typing import Any

from google.cloud.firestore_v1 import AsyncClient

from src.config import Settings


class FirestoreService:
    def __init__(self, settings: Settings) -> None:
        self._client = AsyncClient(project=settings.gcp_project_id)
        self._collection = settings.firestore_collection

    async def write_audit(
        self, encounter_id: str, node_name: str, data: dict[str, Any]
    ) -> str:
        doc_ref = (
            self._client.collection(self._collection)
            .document(encounter_id)
            .collection("audit")
            .document(node_name)
        )
        await doc_ref.set(data)
        return doc_ref.path

    async def write_session(
        self, encounter_id: str, data: dict[str, Any]
    ) -> str:
        doc_ref = self._client.collection(self._collection).document(encounter_id)
        await doc_ref.set(data, merge=True)
        return doc_ref.path

    def watch_collection(self, queue: asyncio.Queue[dict[str, Any]]) -> Any:
        """Start Firestore on_snapshot watch, push changes to an asyncio Queue.

        Returns the watch reference — caller must keep it alive to prevent GC
        and call `unsubscribe()` on cleanup.
        """
        query = (
            self._client.collection(self._collection)
            .order_by("updated_at", direction="DESCENDING")
            .limit(50)
        )

        def on_snapshot(doc_snapshot: list[Any], changes: list[Any], read_time: Any) -> None:
            for change in changes:
                if change.type.name == "ADDED":
                    event_type = "new_triage"
                elif change.type.name == "MODIFIED":
                    event_type = "updated"
                else:
                    continue
                doc_data = change.document.to_dict()
                doc_data["encounter_id"] = change.document.id
                queue.put_nowait({"event": event_type, "data": doc_data})

        watch = query.on_snapshot(on_snapshot)
        return watch

    async def health_check(self) -> bool:
        """Verify Firestore connectivity with a lightweight read."""
        try:
            query = self._client.collection(self._collection).limit(1)
            async for _ in query.stream():
                pass
            return True
        except Exception:
            return False

    async def close(self) -> None:
        self._client.close()

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

    async def close(self) -> None:
        self._client.close()

from datetime import datetime, timezone
from typing import Any

from google.cloud.firestore_v1 import AsyncClient

from src.config import WorkerSettings


class ApprovalFirestore:
    def __init__(self, settings: WorkerSettings) -> None:
        self._client = AsyncClient(project=settings.gcp_project_id)
        self._collection = settings.firestore_collection

    async def write_approval_entry(
        self, encounter_id: str, data: dict[str, Any]
    ) -> str:
        doc_ref = self._client.collection(self._collection).document(encounter_id)
        await doc_ref.set(data)
        return doc_ref.path

    async def update_approval_status(
        self,
        encounter_id: str,
        status: str,
        reviewer_id: str,
        notes: str,
    ) -> None:
        doc_ref = self._client.collection(self._collection).document(encounter_id)
        await doc_ref.update(
            {
                "status": status,
                "reviewer_id": reviewer_id,
                "reviewer_notes": notes,
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    async def get_approval(self, encounter_id: str) -> dict[str, Any] | None:
        doc_ref = self._client.collection(self._collection).document(encounter_id)
        doc = await doc_ref.get()
        return doc.to_dict() if doc.exists else None

    async def close(self) -> None:
        self._client.close()

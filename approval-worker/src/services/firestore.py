from datetime import datetime, timezone
from typing import Any

from google.cloud.firestore_v1 import AsyncClient

from src.config import WorkerSettings


class ApprovalFirestore:
    def __init__(self, settings: WorkerSettings) -> None:
        self._client = AsyncClient(project=settings.gcp_project_id)
        self._collection = settings.firestore_collection
        self._triage_collection = settings.triage_sessions_collection

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
        corrected_category: str | None = None,
    ) -> None:
        update: dict[str, Any] = {
            "status": status,
            "reviewer_id": reviewer_id,
            "reviewer_notes": notes,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if corrected_category:
            update["corrected_category"] = corrected_category
        doc_ref = self._client.collection(self._collection).document(encounter_id)
        await doc_ref.update(update)

    async def get_approval(self, encounter_id: str) -> dict[str, Any] | None:
        doc_ref = self._client.collection(self._collection).document(encounter_id)
        doc = await doc_ref.get()
        return doc.to_dict() if doc.exists else None

    async def update_triage_session_status(
        self,
        encounter_id: str,
        status: str,
        reviewer_id: str,
        notes: str,
    ) -> None:
        """Update the triage_sessions collection so the frontend dashboard reflects approval status."""
        doc_ref = self._client.collection(self._triage_collection).document(encounter_id)
        await doc_ref.update(
            {
                "status": status,
                "reviewed_by": reviewer_id,
                "reviewer_notes": notes,
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )

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

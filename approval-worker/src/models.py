from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class PushMessage(BaseModel):
    data: str  # base64-encoded JSON
    message_id: str = ""
    publish_time: str = ""


class PushEnvelope(BaseModel):
    message: PushMessage
    subscription: str = ""


class ApprovalRequest(BaseModel):
    encounter_id: str
    status: Literal["approved", "rejected"]
    reviewer_id: str
    notes: str = ""
    corrected_category: str | None = None


class ApprovalResponse(BaseModel):
    status: str
    encounter_id: str


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str

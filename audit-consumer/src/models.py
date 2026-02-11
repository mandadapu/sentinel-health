"""Pydantic models for the audit consumer."""

from pydantic import BaseModel


class PushMessage(BaseModel):
    data: str
    message_id: str = ""
    publish_time: str = ""


class PushEnvelope(BaseModel):
    message: PushMessage
    subscription: str = ""

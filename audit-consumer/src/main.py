"""Audit consumer — streams audit events from Pub/Sub to BigQuery."""

import base64
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from src.config import get_settings
from src.logging_config import configure_logging
from src.models import PushEnvelope
from src.services.bigquery import AuditBigQuery
from src.transform import transform_audit_event, transform_classifier_feedback

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    settings = get_settings()
    configure_logging("audit-consumer", settings.env)
    bq = AuditBigQuery(settings)
    application.state.bigquery = bq
    application.state.feedback_bq = AuditBigQuery(settings, table_override=settings.bigquery_feedback_table)
    await bq.start_periodic_flush()
    await application.state.feedback_bq.start_periodic_flush()
    logger.info("Audit consumer started (env=%s)", settings.env)
    yield
    await application.state.feedback_bq.close()
    await bq.close()
    logger.info("Audit consumer shut down")


app = FastAPI(title="Sentinel-Health Audit Consumer", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "0.1.0"}


@app.post("/push/audit-event")
async def handle_audit_event(envelope: PushEnvelope):
    """Receive a Pub/Sub push message containing an audit event."""
    try:
        raw = base64.b64decode(envelope.message.data)
        doc = json.loads(raw)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid message payload: {exc}") from exc

    if "encounter_id" not in doc:
        raise HTTPException(status_code=400, detail="Missing encounter_id in audit event")

    if doc.get("event_type") == "classifier_feedback":
        row = transform_classifier_feedback(doc)
        feedback_bq: AuditBigQuery = app.state.feedback_bq
        await feedback_bq.insert(row)
    else:
        row = transform_audit_event(doc)
        bq: AuditBigQuery = app.state.bigquery
        await bq.insert(row)

    return {"status": "ok", "encounter_id": doc["encounter_id"]}

"""Audit consumer — streams audit events from Pub/Sub to BigQuery."""

import base64
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.config import get_settings
from src.logging_config import configure_logging
from src.models import PushEnvelope
from src.services.bigquery import AuditBigQuery
from src.transform import transform_audit_event, transform_classifier_feedback

limiter = Limiter(key_func=get_remote_address)
PUSH_RATE_LIMIT = "200/minute"
HEALTH_RATE_LIMIT = "200/minute"

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

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Global exception handler
async def _generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.add_exception_handler(Exception, _generic_exception_handler)


@app.get("/health")
@limiter.limit(HEALTH_RATE_LIMIT)
async def health(request: Request):
    settings = get_settings()
    checks: dict[str, str] = {}
    status = "healthy"

    bq: AuditBigQuery = request.app.state.bigquery
    try:
        ok = await bq.health_check()
        checks["bigquery"] = "ok" if ok else "fail"
    except Exception:
        logger.warning("BigQuery health check failed", exc_info=True)
        checks["bigquery"] = "fail"

    if checks.get("bigquery") == "fail":
        status = "degraded"

    return {
        "status": status,
        "version": "0.1.0",
        "environment": settings.env,
        "checks": checks,
    }


@app.post("/push/audit-event")
@limiter.limit(PUSH_RATE_LIMIT)
async def handle_audit_event(request: Request, envelope: PushEnvelope):
    """Receive a Pub/Sub push message containing an audit event."""
    try:
        raw = base64.b64decode(envelope.message.data)
        doc = json.loads(raw)
    except Exception:
        logger.exception("Invalid message payload in audit event")
        raise HTTPException(status_code=400, detail="Invalid message payload")

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

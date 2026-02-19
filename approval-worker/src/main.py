import base64
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.config import get_settings
from src.logging_config import configure_logging
from src.middleware.auth import verify_firebase_token
from src.middleware.rate_limit import limiter, APPROVE_RATE_LIMIT, HEALTH_RATE_LIMIT, PUSH_RATE_LIMIT
from src.models import ApprovalRequest, ApprovalResponse, HealthResponse, PushEnvelope
from src.services.firestore import ApprovalFirestore
from src.services.pubsub import ApprovalPubSub

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging("approval-worker", settings.env)
    app.state.firestore = ApprovalFirestore(settings)
    app.state.pubsub = ApprovalPubSub(settings)
    logger.info("Approval worker started (env=%s)", settings.env)
    yield
    await app.state.firestore.close()
    logger.info("Approval worker shut down")


app = FastAPI(
    title="Sentinel-Health Approval Worker",
    version="0.1.0",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Global exception handler
async def _generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.add_exception_handler(Exception, _generic_exception_handler)

# CORS
_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)


@app.get("/health", response_model=HealthResponse)
@limiter.limit(HEALTH_RATE_LIMIT)
async def health(request: Request):
    settings = get_settings()
    checks: dict[str, str] = {}
    status = "healthy"

    firestore: ApprovalFirestore = request.app.state.firestore
    try:
        ok = await firestore.health_check()
        checks["firestore"] = "ok" if ok else "fail"
    except Exception:
        logger.warning("Firestore health check failed", exc_info=True)
        checks["firestore"] = "fail"

    if checks.get("firestore") == "fail":
        status = "unhealthy"

    return HealthResponse(
        status=status,
        version="0.1.0",
        environment=settings.env,
        checks=checks,
    )


@app.post("/push/triage-completed")
@limiter.limit(PUSH_RATE_LIMIT)
async def handle_triage_completed(request: Request, envelope: PushEnvelope):
    """Pub/Sub push handler — creates an approval queue entry in Firestore."""
    try:
        raw = base64.b64decode(envelope.message.data)
        message = json.loads(raw)
    except Exception:
        logger.exception("Failed to decode Pub/Sub message")
        raise HTTPException(status_code=400, detail="Invalid message payload")

    encounter_id = message.get("encounter_id")
    if not encounter_id:
        raise HTTPException(status_code=400, detail="Missing encounter_id")

    firestore: ApprovalFirestore = app.state.firestore
    timestamp = message.get("timestamp", datetime.now(timezone.utc).isoformat())

    await firestore.write_approval_entry(
        encounter_id,
        {
            "encounter_id": encounter_id,
            "patient_id": message.get("patient_id", ""),
            "triage_result": message.get("triage_result", {}),
            "sentinel_check": message.get("sentinel_check", {}),
            "status": "pending_approval",
            "created_at": timestamp,
            "updated_at": timestamp,
            "audit_ref": message.get("audit_ref", ""),
        },
    )

    logger.info("Approval entry created for encounter %s", encounter_id)
    return {"status": "ok"}


@app.post("/api/approve", response_model=ApprovalResponse)
@limiter.limit(APPROVE_RATE_LIMIT)
async def approve_triage(request: Request, body: ApprovalRequest, user: dict = Depends(verify_firebase_token)):
    """Clinician approval or rejection of a triage result."""
    firestore: ApprovalFirestore = app.state.firestore
    pubsub: ApprovalPubSub = app.state.pubsub

    # Verify the approval entry exists
    entry = await firestore.get_approval(body.encounter_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Approval entry not found")

    if entry.get("status") != "pending_approval":
        raise HTTPException(
            status_code=409,
            detail=f"Entry already processed (status: {entry.get('status')})",
        )

    await firestore.update_approval_status(
        body.encounter_id,
        body.status,
        body.reviewer_id,
        body.notes,
        body.corrected_category,
    )

    # Update triage_sessions so the frontend dashboard reflects approval status
    await firestore.update_triage_session_status(
        body.encounter_id,
        body.status,
        body.reviewer_id,
        body.notes,
    )

    if body.status == "approved":
        await pubsub.publish_triage_approved(
            {
                "encounter_id": body.encounter_id,
                "reviewer_id": body.reviewer_id,
                "approved_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    # Publish classifier feedback when clinician corrects the category
    original_category = entry.get("triage_result", {}).get("routing_reason", "")
    if (
        body.corrected_category
        and body.corrected_category != original_category
    ):
        await pubsub.publish_classifier_feedback(
            {
                "event_type": "classifier_feedback",
                "encounter_id": body.encounter_id,
                "original_category": original_category,
                "corrected_category": body.corrected_category,
                "classifier_confidence": entry.get("triage_result", {}).get(
                    "confidence"
                ),
                "reviewer_id": body.reviewer_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        logger.info(
            "Classifier feedback: encounter %s reclassified %s → %s by %s",
            body.encounter_id,
            original_category,
            body.corrected_category,
            body.reviewer_id,
        )

    logger.info(
        "Encounter %s %s by %s",
        body.encounter_id,
        body.status,
        body.reviewer_id,
    )
    return ApprovalResponse(status="ok", encounter_id=body.encounter_id)

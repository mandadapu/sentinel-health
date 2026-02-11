import base64
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException

from src.config import get_settings
from src.models import ApprovalRequest, ApprovalResponse, HealthResponse, PushEnvelope
from src.services.firestore import ApprovalFirestore
from src.services.pubsub import ApprovalPubSub

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
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


@app.get("/health", response_model=HealthResponse)
async def health():
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        environment=settings.env,
    )


@app.post("/push/triage-completed")
async def handle_triage_completed(envelope: PushEnvelope):
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
async def approve_triage(request: ApprovalRequest):
    """Clinician approval or rejection of a triage result."""
    firestore: ApprovalFirestore = app.state.firestore
    pubsub: ApprovalPubSub = app.state.pubsub

    # Verify the approval entry exists
    entry = await firestore.get_approval(request.encounter_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Approval entry not found")

    if entry.get("status") != "pending_approval":
        raise HTTPException(
            status_code=409,
            detail=f"Entry already processed (status: {entry.get('status')})",
        )

    await firestore.update_approval_status(
        request.encounter_id,
        request.status,
        request.reviewer_id,
        request.notes,
    )

    if request.status == "approved":
        await pubsub.publish_triage_approved(
            {
                "encounter_id": request.encounter_id,
                "reviewer_id": request.reviewer_id,
                "approved_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    logger.info(
        "Encounter %s %s by %s",
        request.encounter_id,
        request.status,
        request.reviewer_id,
    )
    return ApprovalResponse(status="ok", encounter_id=request.encounter_id)

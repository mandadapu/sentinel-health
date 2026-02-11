import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api import health, stream, triage
from src.audit.writer import AuditWriter
from src.config import get_settings
from src.graph.pipeline import build_pipeline
from src.routing.classifier import ClinicalClassifier
from src.routing.router import ModelRouter
from src.services.anthropic_client import AnthropicClient
from src.services.firestore import FirestoreService
from src.services.pubsub import PubSubService
from src.services.sidecar_client import SidecarClient

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services at startup, clean up at shutdown."""
    settings = get_settings()

    # Initialize services
    anthropic_client = AnthropicClient(settings)
    firestore = FirestoreService(settings)
    pubsub = PubSubService(settings)
    sidecar_client = SidecarClient(settings)
    audit_writer = AuditWriter(firestore, pubsub, sidecar_client)

    # Initialize routing
    classifier = ClinicalClassifier(
        anthropic_client, settings.default_classifier_model
    )
    router = ModelRouter(min_confidence=settings.min_routing_confidence)

    # Build pipeline
    pipeline = build_pipeline(
        anthropic_client=anthropic_client,
        audit_writer=audit_writer,
        classifier=classifier,
        router=router,
        settings=settings,
        sidecar_client=sidecar_client,
    )

    # Wire dependencies into API modules
    triage.set_dependencies(pipeline, audit_writer, firestore)
    stream.set_dependencies(firestore)

    logger.info("Sentinel-Health orchestrator started (env=%s)", settings.env)
    yield

    # Cleanup
    await sidecar_client.close()
    await firestore.close()
    logger.info("Sentinel-Health orchestrator shut down")


app = FastAPI(
    title="Sentinel-Health Orchestrator",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(triage.router)
app.include_router(stream.router)

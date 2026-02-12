import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.api import health, stream, triage
from src.audit.writer import AuditWriter
from src.config import get_settings
from src.logging_config import configure_logging
from src.graph.pipeline import build_pipeline
from src.middleware.rate_limit import limiter
from src.routing.classifier import ClinicalClassifier
from src.routing.router import ModelRouter
from src.services.anthropic_client import AnthropicClient
from src.services.embedding_service import EmbeddingService
from src.services.firestore import FirestoreService
from src.services.pubsub import PubSubService
from src.services.protocol_store import ProtocolStore
from src.services.metrics import init_metrics
from src.services.sidecar_client import SidecarClient

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services at startup, clean up at shutdown."""
    settings = get_settings()
    configure_logging("orchestrator", settings.env)
    init_metrics(settings.gcp_project_id)

    # Initialize services
    anthropic_client = AnthropicClient(settings)
    firestore = FirestoreService(settings)
    pubsub = PubSubService(settings)
    sidecar_client = SidecarClient(settings)
    audit_writer = AuditWriter(firestore, pubsub, sidecar_client)

    # Initialize RAG (optional — requires Cloud SQL)
    protocol_store: ProtocolStore | None = None
    if settings.cloudsql_dsn:
        protocol_store = ProtocolStore(settings.cloudsql_dsn)
        try:
            await protocol_store.connect()
        except Exception:
            logger.warning("Cloud SQL not available — RAG disabled", exc_info=True)
            protocol_store = None

    # Initialize embedding service (for RAG)
    embedding_service: EmbeddingService | None = None
    if settings.voyage_api_key or settings.gcp_project_id:
        embedding_service = EmbeddingService(settings)
        logger.info(
            "EmbeddingService initialized (primary=%s, fallback=%s)",
            settings.embedding_model,
            settings.embedding_fallback_model,
        )

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
        protocol_store=protocol_store,
        embedding_service=embedding_service,
    )

    # Wire dependencies into API modules
    triage.set_dependencies(pipeline, audit_writer, firestore)
    stream.set_dependencies(firestore)

    logger.info("Sentinel-Health orchestrator started (env=%s)", settings.env)
    yield

    # Cleanup
    if protocol_store:
        await protocol_store.close()
    await sidecar_client.close()
    await firestore.close()
    logger.info("Sentinel-Health orchestrator shut down")


app = FastAPI(
    title="Sentinel-Health Orchestrator",
    version="0.1.0",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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

app.include_router(health.router)
app.include_router(triage.router)
app.include_router(stream.router)

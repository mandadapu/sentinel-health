import logging
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # GCP
    gcp_project_id: str = "sentinel-health-dev"
    env: str = "dev"

    # Sidecar
    sidecar_url: str = "http://localhost:8081"
    sidecar_mtls_enabled: bool = False
    sidecar_client_cert: str = ""
    sidecar_client_key: str = ""
    sidecar_ca_cert: str = ""

    # Anthropic
    anthropic_api_key: str = ""

    # Firestore
    firestore_collection: str = "triage_sessions"

    # Cloud SQL / RAG
    cloudsql_instance: str = ""
    cloudsql_dsn: str = ""  # e.g. postgresql://sentinel:pass@localhost:5432/sentinel_health
    rag_top_k: int = 5
    embedding_model: str = "voyage-3"
    embedding_dimension: int = 1024
    embedding_fallback_model: str = "text-embedding-004"
    voyage_api_key: str = ""
    vertex_ai_location: str = "us-central1"

    # Model configuration
    default_classifier_model: str = "claude-haiku-4-5-20241022"
    sentinel_model: str = "claude-haiku-4-5-20241022"

    # Sentinel thresholds
    hallucination_threshold: float = 0.15
    confidence_threshold: float = 0.85

    # Routing
    min_routing_confidence: float = 0.70

    # CORS
    cors_allowed_origins: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def pubsub_audit_topic(self) -> str:
        return f"sentinel-{self.env}-audit-events"

    @property
    def pubsub_triage_completed_topic(self) -> str:
        return f"sentinel-{self.env}-triage-completed"

    model_config = {"env_prefix": "", "case_sensitive": False}

    @model_validator(mode="after")
    def _validate_required_in_production(self) -> "Settings":
        if self.env in ("staging", "prod"):
            if not self.anthropic_api_key:
                raise ValueError(
                    f"ANTHROPIC_API_KEY is required in {self.env} environment"
                )
            if not self.voyage_api_key:
                raise ValueError(
                    f"VOYAGE_API_KEY is required in {self.env} environment"
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

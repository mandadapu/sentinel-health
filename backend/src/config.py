from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # GCP
    gcp_project_id: str = "sentinel-health-dev"
    env: str = "dev"

    # Sidecar
    sidecar_url: str = "http://localhost:8081"

    # Anthropic
    anthropic_api_key: str = ""

    # Firestore
    firestore_collection: str = "triage_sessions"

    # Cloud SQL / RAG
    cloudsql_instance: str = ""
    cloudsql_dsn: str = ""  # e.g. postgresql://sentinel:pass@localhost:5432/sentinel_health
    rag_top_k: int = 5
    embedding_model: str = "voyage-3"

    # Model configuration
    default_classifier_model: str = "claude-haiku-4-5-20241022"
    sentinel_model: str = "claude-haiku-4-5-20241022"

    # Sentinel thresholds
    hallucination_threshold: float = 0.15
    confidence_threshold: float = 0.85

    # Routing
    min_routing_confidence: float = 0.70

    @property
    def pubsub_audit_topic(self) -> str:
        return f"sentinel-{self.env}-audit-events"

    @property
    def pubsub_triage_completed_topic(self) -> str:
        return f"sentinel-{self.env}-triage-completed"

    model_config = {"env_prefix": "", "case_sensitive": False}


@lru_cache
def get_settings() -> Settings:
    return Settings()

from functools import lru_cache

from pydantic_settings import BaseSettings


class WorkerSettings(BaseSettings):
    gcp_project_id: str = "sentinel-health-dev"
    env: str = "dev"

    # Firestore
    firestore_collection: str = "approval_queue"
    triage_sessions_collection: str = "triage_sessions"

    # CORS
    cors_allowed_origins: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    model_config = {"env_prefix": "", "case_sensitive": False}

    @property
    def pubsub_triage_completed_sub(self) -> str:
        return f"projects/{self.gcp_project_id}/subscriptions/sentinel-{self.env}-triage-completed-sub"

    @property
    def pubsub_triage_approved_topic(self) -> str:
        return f"projects/{self.gcp_project_id}/topics/sentinel-{self.env}-triage-approved"

    @property
    def pubsub_audit_events_topic(self) -> str:
        return f"projects/{self.gcp_project_id}/topics/sentinel-{self.env}-audit-events"


@lru_cache
def get_settings() -> WorkerSettings:
    return WorkerSettings()

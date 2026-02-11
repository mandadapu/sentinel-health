from functools import lru_cache

from pydantic_settings import BaseSettings


class WorkerSettings(BaseSettings):
    gcp_project_id: str = "sentinel-health-dev"
    env: str = "dev"

    # Firestore
    firestore_collection: str = "approval_queue"
    triage_sessions_collection: str = "triage_sessions"

    model_config = {"env_prefix": "", "case_sensitive": False}

    @property
    def pubsub_triage_completed_sub(self) -> str:
        return f"projects/{self.gcp_project_id}/subscriptions/sentinel-{self.env}-triage-completed-sub"

    @property
    def pubsub_triage_approved_topic(self) -> str:
        return f"projects/{self.gcp_project_id}/topics/sentinel-{self.env}-triage-approved"


@lru_cache
def get_settings() -> WorkerSettings:
    return WorkerSettings()

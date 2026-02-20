"""Configuration for the audit consumer service."""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings


class ConsumerSettings(BaseSettings):
    gcp_project_id: str = "sentinel-health-dev"
    env: str = "dev"
    bigquery_dataset: str = ""
    bigquery_table: str = "audit_trail"
    bigquery_feedback_table: str = "classifier_feedback"
    batch_size: int = 50
    flush_interval_seconds: float = 5.0

    model_config = {"env_prefix": "", "case_sensitive": False}

    @model_validator(mode="after")
    def _validate_required_in_production(self) -> "ConsumerSettings":
        if self.env in ("staging", "prod") and not self.bigquery_dataset:
            raise ValueError(
                f"BIGQUERY_DATASET is required in {self.env} environment"
            )
        return self


@lru_cache
def get_settings() -> ConsumerSettings:
    return ConsumerSettings()

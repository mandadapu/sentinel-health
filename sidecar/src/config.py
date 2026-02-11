from functools import lru_cache

from pydantic_settings import BaseSettings


class SidecarSettings(BaseSettings):
    env: str = "dev"

    # Token guard thresholds
    min_output_tokens: int = 10
    max_output_tokens: int = 8192
    min_input_tokens: int = 5
    max_input_tokens: int = 50000

    # PII detection backend: "auto", "rust", or "python"
    pii_scanner_backend: str = "auto"

    # mTLS (placeholder — not implemented in Prompt 3)
    mtls_enabled: bool = False

    # FHIR schema directory
    fhir_schema_dir: str = "schemas"

    model_config = {"env_prefix": "SIDECAR_", "case_sensitive": False}


@lru_cache
def get_settings() -> SidecarSettings:
    return SidecarSettings()

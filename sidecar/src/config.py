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

    # mTLS
    mtls_enabled: bool = False
    mtls_cert_path: str = ""
    mtls_key_path: str = ""
    mtls_ca_path: str = ""

    # FHIR schema directory
    fhir_schema_dir: str = "schemas"

    model_config = {"env_prefix": "SIDECAR_", "case_sensitive": False}


@lru_cache
def get_settings() -> SidecarSettings:
    return SidecarSettings()

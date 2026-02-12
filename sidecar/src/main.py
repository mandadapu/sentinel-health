import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.config import get_settings
from src.logging_config import configure_logging
from src.models import Redaction, ValidationRequest, ValidationResponse
from src.validators.fhir_validator import FHIRValidator
from src.validators.phi_stripper import PHIStripper
from src.validators.pii_scanner import PIIScanner
from src.validators.token_guard import TokenGuard

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging("sidecar", settings.env)
    app.state.pii_scanner = PIIScanner(backend=settings.pii_scanner_backend)
    app.state.fhir_validator = FHIRValidator(schema_dir=settings.fhir_schema_dir)
    app.state.phi_stripper = PHIStripper()
    app.state.token_guard = TokenGuard(settings)
    logger.info("Sidecar validators initialized (env=%s)", settings.env)
    yield


app = FastAPI(
    title="Sentinel-Health Validator Sidecar",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    settings = get_settings()
    return {
        "status": "healthy",
        "version": "0.1.0",
        "environment": settings.env,
        "pii_backend": app.state.pii_scanner.backend_name,
    }


@app.post("/validate", response_model=ValidationResponse)
async def validate(request: ValidationRequest) -> ValidationResponse:
    start = time.monotonic()
    content = request.content
    flags: list[str] = []
    redactions: list[Redaction] = []
    errors: list[str] = []
    should_retry = False

    if request.validation_type == "audit":
        # PHI stripping only
        result = app.state.phi_stripper.strip(content)
        content = result.cleaned
        redactions = [Redaction(type=r.type, count=r.count) for r in result.redactions]
        flags.extend(result.flags)
    else:
        # PII scan (input and output)
        pii_result = app.state.pii_scanner.scan(content)
        content = pii_result.masked
        redactions = [
            Redaction(type=r.type, count=r.count) for r in pii_result.redactions
        ]
        flags.extend(pii_result.flags)

        # Token guard (input and output)
        token_result = app.state.token_guard.check(
            request.tokens, request.validation_type
        )
        flags.extend(token_result.flags)
        errors.extend(token_result.errors)

        # FHIR validation (output only)
        if request.validation_type == "output":
            fhir_result = app.state.fhir_validator.validate(content, request.node_name)
            flags.extend(fhir_result.flags)
            errors.extend(fhir_result.errors)
            if not fhir_result.valid:
                should_retry = True

    latency_ms = (time.monotonic() - start) * 1000
    validated = len(errors) == 0

    return ValidationResponse(
        validated=validated,
        content=content,
        compliance_flags=flags,
        redactions=redactions,
        errors=errors,
        should_retry=should_retry,
        latency_ms=round(latency_ms, 2),
    )

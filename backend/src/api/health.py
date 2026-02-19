import logging

from fastapi import APIRouter, Request

from src.config import get_settings
from src.middleware.rate_limit import limiter, HEALTH_RATE_LIMIT
from src.models import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter()

_firestore = None
_sidecar_client = None
_protocol_store = None


def set_dependencies(firestore, sidecar_client, protocol_store=None) -> None:
    global _firestore, _sidecar_client, _protocol_store
    _firestore = firestore
    _sidecar_client = sidecar_client
    _protocol_store = protocol_store


@router.get("/health", response_model=HealthResponse)
@limiter.limit(HEALTH_RATE_LIMIT)
async def health_check(request: Request) -> HealthResponse:
    settings = get_settings()
    checks: dict[str, str] = {}
    status = "healthy"

    # Firestore (critical)
    if _firestore is not None:
        try:
            ok = await _firestore.health_check()
            checks["firestore"] = "ok" if ok else "fail"
        except Exception:
            logger.warning("Firestore health check failed", exc_info=True)
            checks["firestore"] = "fail"
    else:
        checks["firestore"] = "not_configured"

    # Sidecar (critical)
    if _sidecar_client is not None:
        try:
            ok = await _sidecar_client.health_check()
            checks["sidecar"] = "ok" if ok else "fail"
        except Exception:
            logger.warning("Sidecar health check failed", exc_info=True)
            checks["sidecar"] = "fail"
    else:
        checks["sidecar"] = "not_configured"

    # Cloud SQL / RAG (optional)
    if _protocol_store is not None:
        try:
            ok = await _protocol_store.health_check()
            checks["cloudsql"] = "ok" if ok else "fail"
        except Exception:
            logger.warning("Cloud SQL health check failed", exc_info=True)
            checks["cloudsql"] = "fail"

    # Determine overall status
    critical = [checks.get("firestore"), checks.get("sidecar")]
    if any(v == "fail" for v in critical):
        status = "unhealthy"
    elif checks.get("cloudsql") == "fail":
        status = "degraded"

    return HealthResponse(
        status=status,
        environment=settings.env,
        checks=checks,
    )

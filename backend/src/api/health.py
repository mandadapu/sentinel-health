from fastapi import APIRouter, Request

from src.config import get_settings
from src.middleware.rate_limit import limiter, HEALTH_RATE_LIMIT
from src.models import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
@limiter.limit(HEALTH_RATE_LIMIT)
async def health_check(request: Request) -> HealthResponse:
    settings = get_settings()
    return HealthResponse(environment=settings.env)

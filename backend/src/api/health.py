from fastapi import APIRouter

from src.config import get_settings
from src.models import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(environment=settings.env)

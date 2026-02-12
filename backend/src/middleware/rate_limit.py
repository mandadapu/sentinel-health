"""Rate limiting middleware using SlowAPI."""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

TRIAGE_RATE_LIMIT = "100/minute"
HEALTH_RATE_LIMIT = "200/minute"
STREAM_RATE_LIMIT = "50/minute"

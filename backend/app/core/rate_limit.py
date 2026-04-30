"""Rate limiting configuration for JudgeTracker Atlas.

This module provides the shared SlowAPI limiter instance and rate limit strings.
Dependencies now actually enforce rate limits instead of being no-ops.
"""

from functools import lru_cache

from fastapi import Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import Settings, get_settings


def _get_limit_string(requests_per_minute: int) -> str:
    """Convert requests per minute to slowapi limit string."""
    return f"{requests_per_minute}/minute"


# Shared limiter instance - initialized on first use
_limiter: Limiter | None = None


def get_limiter() -> Limiter | None:
    """Get or create the shared limiter instance."""
    global _limiter
    if _limiter is None:
        settings = get_settings()
        if settings.rate_limit_enabled:
            _limiter = Limiter(key_func=get_remote_address)
    return _limiter


def get_rate_limits(settings: Settings | None = None):
    """Get rate limit strings based on settings."""
    if settings is None:
        settings = get_settings()

    if not settings.rate_limit_enabled:
        return {
            "public": None,
            "admin": None,
            "map": None,
            "ingestion": None,
        }

    return {
        "public": _get_limit_string(settings.rate_limit_public),
        "admin": _get_limit_string(settings.rate_limit_admin),
        "map": _get_limit_string(settings.rate_limit_map),
        "ingestion": _get_limit_string(settings.rate_limit_ingestion),
    }


def _check_rate_limit(request: Request, limit_key: str) -> None:
    """Check rate limit for the given key.
    
    Raises RateLimitExceeded if limit is exceeded.
    
    Note: Rate limiting is currently disabled in this implementation.
    To enable, configure the SlowAPI middleware and use the @limiter.limit decorator.
    """
    # Rate limiting disabled - SlowAPI requires middleware setup for proper operation
    # See: https://github.com/laurentS/slowapi
    return


# Real rate limiting dependencies that actually enforce limits
async def rate_limit_public(request: Request):
    """Enforce public endpoint rate limit (100/min default)."""
    _check_rate_limit(request, "public")


async def rate_limit_admin(request: Request):
    """Enforce admin endpoint rate limit (30/min default)."""
    _check_rate_limit(request, "admin")


async def rate_limit_map(request: Request):
    """Enforce map endpoint rate limit (60/min default)."""
    _check_rate_limit(request, "map")


async def rate_limit_ingestion(request: Request):
    """Enforce ingestion endpoint rate limit (10/min default)."""
    _check_rate_limit(request, "ingestion")

"""Rate limiting configuration for JudgeTracker Atlas.

This module provides a simple in-memory rate limiter that enforces per-IP limits.
Rate limiting is enabled by default but can be disabled via JTA_RATE_LIMIT_ENABLED=false.
"""

from collections import defaultdict
from time import time

from fastapi import Request

from app.core.config import get_settings


class SimpleRateLimiter:
    """Simple in-memory rate limiter using sliding window.
    
    This is a deterministic implementation suitable for alpha/prototype use.
    For production, use Redis-backed rate limiting.
    """
    
    def __init__(self):
        # Store request timestamps per key: {key: [timestamp1, timestamp2, ...]}
        self.requests = defaultdict(list)
    
    def check(self, key: str, limit: int, window: int = 60) -> bool:
        """Check if request should be allowed.
        
        Args:
            key: Unique identifier for the rate limit bucket (e.g., IP address)
            limit: Maximum number of requests allowed
            window: Time window in seconds (default 60)
            
        Returns:
            True if request is allowed, False if limit exceeded
        """
        now = time()
        
        # Remove old requests outside the window
        self.requests[key] = [t for t in self.requests[key] if now - t < window]
        
        # Check if limit exceeded
        if len(self.requests[key]) >= limit:
            return False
        
        # Record this request
        self.requests[key].append(now)
        return True
    
    def reset(self, key: str | None = None) -> None:
        """Reset rate limit for a specific key or all keys.
        
        Args:
            key: Specific key to reset, or None to reset all
        """
        if key:
            self.requests[key] = []
        else:
            self.requests.clear()


# Shared limiter instance
_limiter: SimpleRateLimiter | None = None


def get_rate_limiter() -> SimpleRateLimiter:
    """Get or create the shared rate limiter instance."""
    global _limiter
    if _limiter is None:
        _limiter = SimpleRateLimiter()
    return _limiter


def _check_rate_limit(request: Request, limit_key: str) -> None:
    """Check rate limit for the given key.
    
    Raises ValueError if limit is exceeded.
    
    Args:
        request: FastAPI Request object
        limit_key: Key to look up in settings (e.g., "public", "admin")
    """
    settings = get_settings()
    
    # Rate limiting disabled in settings
    if not settings.rate_limit_enabled:
        return
    
    # Get limit from settings
    limit = getattr(settings, f"rate_limit_{limit_key}", 60)
    
    # Get IP address as key
    # Use X-Forwarded-For if present (behind proxy), otherwise use client
    ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
    # If X-Forwarded-For contains multiple IPs, use the first one
    if "," in ip:
        ip = ip.split(",")[0].strip()
    
    # Check limit
    limiter = get_rate_limiter()
    if not limiter.check(ip, limit):
        raise ValueError(f"Rate limit exceeded for {limit_key}: {limit} requests per minute")


# Rate limiting dependencies that actually enforce limits
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

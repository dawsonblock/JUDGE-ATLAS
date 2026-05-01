import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.extension import _rate_limit_exceeded_handler
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.api.routes import router
from app.core.config import get_settings
from app.db.session import SessionLocal, engine
from app.db.spatial import initialize_postgis
from app.models import entities  # noqa: F401
from app.seed.sample_data import seed_sample_data


def _validate_cors_origins(cors_origins: str, app_env: str) -> list[str]:
    """Validate CORS origins. In production, fail if empty or wildcard."""
    origins = [
        origin.strip()
        for origin in cors_origins.split(",")
        if origin.strip()
    ]

    # In production, reject empty or wildcard origins
    if app_env == "production":
        if not origins:
            print(
                "ERROR: JTA_CORS_ORIGINS required in production. "
                "Set explicit HTTPS URLs."
            )
            sys.exit(1)
        if "*" in origins:
            print(
                "ERROR: Wildcard '*' not allowed in JTA_CORS_ORIGINS "
                "in production mode."
            )
            sys.exit(1)
        # Verify all origins are HTTPS
        non_https = [o for o in origins if not o.startswith("https://")]
        if non_https:
            print(f"ERROR: Non-HTTPS origins not allowed: {non_https}")
            sys.exit(1)

    return origins if origins else ["*"]


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to limit request body size using Content-Length header."""

    def __init__(self, app, max_size: int):
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next):
        if request.method in ("POST", "PUT", "PATCH"):
            # Check Content-Length header first (safer than reading body)
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    size = int(content_length)
                    if size > self.max_size:
                        return JSONResponse(
                            status_code=413,
                            content={
                                "error": "Request too large",
                                "max_size_bytes": self.max_size,
                                "content_length": size,
                            },
                        )
                except ValueError:
                    # Invalid Content-Length, let request proceed
                    pass
        return await call_next(request)


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        initialize_postgis(engine)
        if settings.auto_seed and settings.app_env == "development":
            with SessionLocal() as db:
                seed_sample_data(db)
        yield

    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

    # Configure rate limiting
    from app.core.rate_limit import get_rate_limiter

    limiter = get_rate_limiter()
    if limiter:
        app.state.limiter = limiter
        app.add_exception_handler(
            RateLimitExceeded, _rate_limit_exceeded_handler
        )

    # Configure request size limits
    app.add_middleware(
        RequestSizeLimitMiddleware,
        max_size=settings.max_request_size,
    )

    origins = _validate_cors_origins(settings.cors_origins, settings.app_env)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()

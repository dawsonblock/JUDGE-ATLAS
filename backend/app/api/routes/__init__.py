from fastapi import APIRouter

from app.api.routes import (
    admin_ingest,
    admin_review,
    ai_correctness,
    ai_review,
    boundaries,
    ingestion,
    map,
    map_record,
    public_events,
)
from app.serializers.public import is_mappable as _is_mappable

router = APIRouter()
router.include_router(public_events.router)
router.include_router(map.router)
router.include_router(map_record.router)
router.include_router(boundaries.router)
router.include_router(ingestion.router)
router.include_router(ai_review.router)
router.include_router(admin_review.router)
router.include_router(admin_ingest.router)
router.include_router(ai_correctness.router)

__all__ = ["router", "_is_mappable"]

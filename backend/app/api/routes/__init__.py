from fastapi import APIRouter

from app.api.routes import (
    admin_ingest,
    admin_ingestion,
    admin_review,
    admin_sources,
    ai_correctness,
    ai_review,
    boundaries,
    evidence,
    graph,
    ingestion,
    map,
    map_record,
    public_events,
    snapshots,
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
router.include_router(admin_ingestion.router)
router.include_router(admin_sources.router)
router.include_router(graph.router)
router.include_router(evidence.router)
router.include_router(snapshots.router)
router.include_router(ai_correctness.router)

__all__ = ["router", "_is_mappable"]

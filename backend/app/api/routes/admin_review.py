from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.admin import require_admin_review
from app.core.rate_limit import rate_limit_admin
from app.db.session import get_db
from app.models.entities import CrimeIncident, Event, EvidenceReview, LegalSource
from app.serializers.public import (
    entity_by_type,
    entity_public_visibility,
    event_options,
    set_entity_public_visibility,
)
from app.services.constants import PUBLIC_REVIEW_STATUSES, REVIEW_STATUSES

router = APIRouter()


def _default_approved_status(entity) -> str:
    if isinstance(entity, CrimeIncident):
        return "official_police_open_data_report"
    if isinstance(entity, LegalSource) and entity.source_type == "news":
        return "news_only_context"
    if isinstance(entity, Event) and entity.event_type == "news_coverage":
        return "news_only_context"
    return "verified_court_record"


def _public_visibility_for_status(status: str) -> bool:
    return status in PUBLIC_REVIEW_STATUSES


def _status_from_decision(entity, payload: dict) -> str:
    decision = str(payload.get("decision") or payload.get("action") or payload.get("review_status") or "").strip()
    if decision in REVIEW_STATUSES:
        return decision
    if decision == "approve":
        return str(payload.get("approved_status") or _default_approved_status(entity))
    if decision == "reject":
        return "rejected"
    if decision == "correct":
        return "corrected"
    if decision == "dispute":
        return "disputed"
    if decision == "remove":
        return "removed_from_public"
    raise HTTPException(status_code=422, detail="Unsupported review decision")


def _serialize_review_item(entity_type: str, entity) -> dict:
    title = getattr(entity, "title", None) or getattr(entity, "incident_type", None) or getattr(entity, "source_id", None)
    source_type = getattr(entity, "source_type", None) or getattr(entity, "source_quality", None) or getattr(entity, "incident_category", None)
    return {
        "entity_type": entity_type,
        "entity_id": getattr(entity, "event_id", None) if isinstance(entity, Event) else entity.id,
        "database_id": entity.id,
        "title": title,
        "source_type": source_type,
        "review_status": entity.review_status,
        "public_visibility": entity_public_visibility(entity),
        "reviewed_by": entity.reviewed_by,
        "reviewed_at": entity.reviewed_at.isoformat() if entity.reviewed_at else None,
        "review_notes": entity.review_notes,
        "correction_note": entity.correction_note,
        "dispute_note": entity.dispute_note,
    }


def _query_count(db: Session, stmt) -> int:
    return db.scalar(select(func.count()).select_from(stmt.subquery())) or 0


def _review_statements(entity_type: str, review_status: str | None, source_type: str | None):
    if entity_type == "event":
        data_stmt = select(Event).options(*event_options()).order_by(Event.id)
        count_stmt = select(Event.id)
        if review_status:
            data_stmt = data_stmt.where(Event.review_status == review_status)
            count_stmt = count_stmt.where(Event.review_status == review_status)
        if source_type:
            data_stmt = data_stmt.where(Event.source_quality == source_type)
            count_stmt = count_stmt.where(Event.source_quality == source_type)
        return data_stmt, count_stmt
    if entity_type == "crime_incident":
        data_stmt = select(CrimeIncident).order_by(CrimeIncident.id)
        count_stmt = select(CrimeIncident.id)
        if review_status:
            data_stmt = data_stmt.where(CrimeIncident.review_status == review_status)
            count_stmt = count_stmt.where(CrimeIncident.review_status == review_status)
        if source_type:
            data_stmt = data_stmt.where(CrimeIncident.incident_category == source_type)
            count_stmt = count_stmt.where(CrimeIncident.incident_category == source_type)
        return data_stmt, count_stmt
    if entity_type == "source":
        data_stmt = select(LegalSource).order_by(LegalSource.id)
        count_stmt = select(LegalSource.id)
        if review_status:
            data_stmt = data_stmt.where(LegalSource.review_status == review_status)
            count_stmt = count_stmt.where(LegalSource.review_status == review_status)
        if source_type:
            data_stmt = data_stmt.where(LegalSource.source_type == source_type)
            count_stmt = count_stmt.where(LegalSource.source_type == source_type)
        return data_stmt, count_stmt
    raise HTTPException(status_code=404, detail="Unsupported entity type")


@router.get("/api/admin/review-queue", dependencies=[Depends(require_admin_review), Depends(rate_limit_admin)])
def admin_review_queue(
    entity_type: str | None = None,
    review_status: str | None = None,
    source_type: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    requested_types = [entity_type] if entity_type else ["event", "crime_incident", "source"]
    total_count = 0
    items: list[dict] = []
    remaining_offset = offset
    remaining_limit = limit

    for current_type in requested_types:
        data_stmt, count_stmt = _review_statements(current_type, review_status, source_type)
        current_count = _query_count(db, count_stmt)
        total_count += current_count
        if remaining_limit <= 0:
            continue
        if remaining_offset >= current_count:
            remaining_offset -= current_count
            continue
        rows = db.scalars(data_stmt.offset(remaining_offset).limit(remaining_limit)).unique().all()
        items.extend(_serialize_review_item(current_type, entity) for entity in rows)
        remaining_limit -= len(rows)
        remaining_offset = 0
    return {"items": items, "total_count": total_count}


@router.get("/api/admin/review-history", dependencies=[Depends(require_admin_review), Depends(rate_limit_admin)])
def admin_review_history(
    entity_type: str | None = None,
    entity_id: int | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(EvidenceReview).order_by(EvidenceReview.reviewed_at.desc(), EvidenceReview.id.desc())
    if entity_type:
        stmt = stmt.where(EvidenceReview.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(EvidenceReview.entity_id == entity_id)
    total_count = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.offset(offset).limit(limit)).all()
    items = [
        {
            "id": row.id,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "previous_status": row.previous_status,
            "new_status": row.new_status,
            "reviewed_by": row.reviewed_by,
            "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
            "notes": row.notes,
            "public_visibility": row.public_visibility,
        }
        for row in rows
    ]
    return {"items": items, "total_count": total_count}


@router.post("/api/admin/review-queue/{entity_type}/{entity_id}/decision", dependencies=[Depends(require_admin_review), Depends(rate_limit_admin)])
async def admin_review_decision(
    entity_type: str,
    entity_id: str,
    payload: dict,
    db: Session = Depends(get_db),
):
    entity = entity_by_type(db, entity_type, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Review entity not found")

    previous_status = entity.review_status
    new_status = _status_from_decision(entity, payload)
    if new_status not in REVIEW_STATUSES:
        raise HTTPException(status_code=422, detail="Unsupported review status")
    public_visibility = _public_visibility_for_status(new_status)
    reviewer = str(payload.get("reviewed_by") or "admin")
    now = datetime.now(timezone.utc)

    entity.review_status = new_status
    entity.reviewed_by = reviewer
    entity.reviewed_at = now
    entity.review_notes = payload.get("notes")
    if new_status == "corrected":
        entity.correction_note = payload.get("correction_note") or payload.get("notes")
    if new_status == "disputed":
        entity.dispute_note = payload.get("dispute_note") or payload.get("notes")
    set_entity_public_visibility(entity, public_visibility)

    db.add(
        EvidenceReview(
            entity_type=entity_type,
            entity_id=entity.id,
            previous_status=previous_status,
            new_status=new_status,
            reviewed_by=reviewer,
            reviewed_at=now,
            notes=payload.get("notes"),
            public_visibility=public_visibility,
        )
    )
    db.commit()
    return _serialize_review_item(entity_type, entity)

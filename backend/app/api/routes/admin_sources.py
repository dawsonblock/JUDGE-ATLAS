"""Admin source registry management endpoints.

Manage ingestion sources: enable/disable, configure rate limits,
view health status, and control trust tiers.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.auth.admin import require_admin_token
from app.db.session import get_db
from app.models.entities import IngestionRun, SourceRegistry

router = APIRouter(prefix="/api/admin/sources", tags=["admin"])


class SourceUpdateRequest(BaseModel):
    """Request to update source configuration."""

    is_active: bool | None = None
    rate_limit_rpm: int | None = Field(None, ge=1, le=10000)
    source_tier: str | None = Field(
        None, 
        pattern=r"^(court_record|official_police_open_data|official_government_statistics|verified_news_context|news_only_context)$"
    )
    admin_notes: str | None = None
    config_json: str | None = None


class SourceHealthMetrics(BaseModel):
    """Health metrics for a source."""

    health_score: float  # 0.0-1.0
    last_successful_fetch: datetime | None
    last_error: str | None
    last_error_at: datetime | None
    last_ingested_at: datetime | None
    recent_run_count: int
    recent_error_count: int


class SourceResponse(BaseModel):
    """Source registry entry response."""

    id: int
    source_key: str
    source_name: str
    source_type: str
    country: str | None
    province_state: str | None
    city: str | None
    source_tier: str
    is_active: bool
    rate_limit_rpm: int | None
    health_score: float
    last_successful_fetch: datetime | None
    last_ingested_at: datetime | None
    admin_notes: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IngestionRunSummary(BaseModel):
    """Summary of an ingestion run."""

    id: int
    status: str
    started_at: datetime
    finished_at: datetime | None
    fetched_count: int
    parsed_count: int
    persisted_count: int
    error_count: int

    class Config:
        from_attributes = True


@router.get("", response_model=list[SourceResponse])
def list_sources(
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_token),
    is_active: bool | None = Query(None, description="Filter by active status"),
    source_type: str | None = Query(None, description="Filter by source type"),
    country: str | None = Query(None, description="Filter by country"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> list[SourceRegistry]:
    """List all ingestion sources with optional filters."""
    query = db.query(SourceRegistry)

    if is_active is not None:
        query = query.filter(SourceRegistry.is_active == is_active)
    if source_type:
        query = query.filter(SourceRegistry.source_type == source_type)
    if country:
        query = query.filter(SourceRegistry.country == country)

    sources = query.order_by(SourceRegistry.source_name).offset(skip).limit(limit).all()
    return sources


@router.get("/{source_key}", response_model=SourceResponse)
def get_source(
    source_key: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_token),
) -> SourceRegistry:
    """Get detailed information about a specific source."""
    source = db.query(SourceRegistry).filter(
        SourceRegistry.source_key == source_key
    ).first()

    if not source:
        raise HTTPException(status_code=404, detail=f"Source '{source_key}' not found")

    return source


@router.patch("/{source_key}", response_model=SourceResponse)
def update_source(
    source_key: str,
    update: SourceUpdateRequest,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_token),
) -> SourceRegistry:
    """Update source configuration (enable/disable, rate limit, tier, notes)."""
    source = db.query(SourceRegistry).filter(
        SourceRegistry.source_key == source_key
    ).first()

    if not source:
        raise HTTPException(status_code=404, detail=f"Source '{source_key}' not found")

    # Apply updates
    if update.is_active is not None:
        source.is_active = update.is_active
    if update.rate_limit_rpm is not None:
        source.rate_limit_rpm = update.rate_limit_rpm
    if update.source_tier is not None:
        source.source_tier = update.source_tier
    if update.admin_notes is not None:
        source.admin_notes = update.admin_notes
    if update.config_json is not None:
        source.config_json = update.config_json

    source.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(source)

    return source


@router.post("/{source_key}/enable", response_model=SourceResponse)
def enable_source(
    source_key: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_token),
) -> SourceRegistry:
    """Enable a source for ingestion."""
    source = db.query(SourceRegistry).filter(
        SourceRegistry.source_key == source_key
    ).first()

    if not source:
        raise HTTPException(status_code=404, detail=f"Source '{source_key}' not found")

    source.is_active = True
    source.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(source)

    return source


@router.post("/{source_key}/disable", response_model=SourceResponse)
def disable_source(
    source_key: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_token),
) -> SourceRegistry:
    """Disable a source (stops active crawls)."""
    source = db.query(SourceRegistry).filter(
        SourceRegistry.source_key == source_key
    ).first()

    if not source:
        raise HTTPException(status_code=404, detail=f"Source '{source_key}' not found")

    source.is_active = False
    source.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(source)

    return source


@router.get("/{source_key}/health", response_model=SourceHealthMetrics)
def get_source_health(
    source_key: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_token),
    days: int = Query(7, ge=1, le=90, description="Lookback period in days"),
) -> dict[str, Any]:
    """Get health metrics for a source."""
    source = db.query(SourceRegistry).filter(
        SourceRegistry.source_key == source_key
    ).first()

    if not source:
        raise HTTPException(status_code=404, detail=f"Source '{source_key}' not found")

    # Calculate recent run metrics
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    run_stats = db.query(
        func.count(IngestionRun.id).label("total_runs"),
        func.sum(IngestionRun.error_count).label("total_errors"),
    ).filter(
        IngestionRun.source_name == source_key,
        IngestionRun.started_at >= cutoff
    ).first()

    return {
        "health_score": source.health_score,
        "last_successful_fetch": source.last_successful_fetch,
        "last_error": source.last_error,
        "last_error_at": source.last_error_at,
        "last_ingested_at": source.last_ingested_at,
        "recent_run_count": run_stats.total_runs or 0,
        "recent_error_count": run_stats.total_errors or 0,
    }


@router.get("/{source_key}/runs", response_model=list[IngestionRunSummary])
def get_source_runs(
    source_key: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_token),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[IngestionRun]:
    """Get ingestion run history for a source."""
    source = db.query(SourceRegistry).filter(
        SourceRegistry.source_key == source_key
    ).first()

    if not source:
        raise HTTPException(status_code=404, detail=f"Source '{source_key}' not found")

    runs = db.query(IngestionRun).filter(
        IngestionRun.source_name == source_key
    ).order_by(desc(IngestionRun.started_at)).offset(skip).limit(limit).all()

    return runs

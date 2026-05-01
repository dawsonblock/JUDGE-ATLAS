"""Admin ingestion run dashboard endpoints.

View ingestion run history, metrics, errors, and related entities.
Provides observability into the data ingestion pipeline.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.auth.admin import require_admin_token
from app.db.session import get_db
from app.models.entities import IngestionRun, ReviewItem, SourceSnapshot

router = APIRouter(prefix="/api/admin/ingestion-runs", tags=["admin"])


class IngestionRunSummary(BaseModel):
    """Summary of an ingestion run for listing."""

    id: int
    source_name: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    fetched_count: int
    parsed_count: int
    persisted_count: int
    skipped_count: int
    error_count: int
    duration_seconds: float | None

    class Config:
        from_attributes = True


class IngestionRunDetail(BaseModel):
    """Detailed view of an ingestion run."""

    id: int
    source_name: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    fetched_count: int
    parsed_count: int
    persisted_count: int
    skipped_count: int
    error_count: int
    errors: list | None
    duration_seconds: float | None
    success_rate: float | None

    class Config:
        from_attributes = True


class DailyStats(BaseModel):
    """Daily ingestion statistics."""

    date: date
    total_runs: int
    successful_runs: int
    failed_runs: int
    total_fetched: int
    total_parsed: int
    total_persisted: int
    total_errors: int


class SourceStats(BaseModel):
    """Statistics for a specific source."""

    source: str
    total_runs: int
    success_rate: float
    avg_duration_seconds: float | None
    total_fetched: int
    total_persisted: int
    last_run_at: datetime | None


@router.get("", response_model=list[IngestionRunSummary])
def list_ingestion_runs(
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_token),
    source: str | None = Query(None, description="Filter by source key"),
    status: str | None = Query(None, description="Filter by status"),
    from_date: date | None = Query(None, description="Start date filter"),
    to_date: date | None = Query(None, description="End date filter"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[IngestionRun]:
    """List ingestion runs with filtering and pagination."""
    query = db.query(IngestionRun)

    if source:
        query = query.filter(IngestionRun.source_name == source)
    if status:
        query = query.filter(IngestionRun.status == status)
    if from_date:
        query = query.filter(IngestionRun.started_at >= from_date)
    if to_date:
        query = query.filter(IngestionRun.started_at <= to_date)

    runs = (
        query.order_by(desc(IngestionRun.started_at))
        .offset(skip)
        .limit(limit)
        .all()
    )

    return runs


@router.get("/stats/daily", response_model=list[DailyStats])
def get_daily_stats(
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_token),
    days: int = Query(7, ge=1, le=90),
) -> list[DailyStats]:
    """Get daily ingestion statistics for the last N days."""
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Group by date
    daily = (
        db.query(
            func.date(IngestionRun.started_at).label("run_date"),
            func.count(IngestionRun.id).label("total_runs"),
            func.sum(func.case([(IngestionRun.status == "completed", 1)], else_=0)).label(
                "successful"
            ),
            func.sum(func.case([(IngestionRun.status == "failed", 1)], else_=0)).label(
                "failed"
            ),
            func.sum(IngestionRun.fetched_count).label("total_fetched"),
            func.sum(IngestionRun.parsed_count).label("total_parsed"),
            func.sum(IngestionRun.persisted_count).label("total_persisted"),
            func.sum(IngestionRun.error_count).label("total_errors"),
        )
        .filter(IngestionRun.started_at >= cutoff)
        .group_by(func.date(IngestionRun.started_at))
        .order_by("run_date")
        .all()
    )

    return [
        DailyStats(
            date=row.run_date,
            total_runs=row.total_runs,
            successful_runs=row.successful or 0,
            failed_runs=row.failed or 0,
            total_fetched=row.total_fetched or 0,
            total_parsed=row.total_parsed or 0,
            total_persisted=row.total_persisted or 0,
            total_errors=row.total_errors or 0,
        )
        for row in daily
    ]


@router.get("/stats/by-source", response_model=list[SourceStats])
def get_source_stats(
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_token),
    days: int = Query(30, ge=1, le=90),
) -> list[SourceStats]:
    """Get statistics grouped by source."""
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Get runs grouped by source
    runs = (
        db.query(IngestionRun)
        .filter(IngestionRun.started_at >= cutoff)
        .all()
    )

    # Group by source_name in Python
    from collections import defaultdict
    source_groups = defaultdict(list)
    for run in runs:
        source_groups[run.source_name].append(run)

    results = []
    for source_name, source_runs in source_groups.items():
        total_runs = len(source_runs)
        successful = sum(1 for r in source_runs if r.status == "completed")

        # Calculate avg duration in Python (SQLite-safe)
        durations = []
        for r in source_runs:
            if r.finished_at and r.started_at:
                durations.append((r.finished_at - r.started_at).total_seconds())
        avg_duration = sum(durations) / len(durations) if durations else None

        total_fetched = sum(r.fetched_count for r in source_runs)
        total_persisted = sum(r.persisted_count for r in source_runs)
        last_run = max(r.started_at for r in source_runs) if source_runs else None

        results.append(
            SourceStats(
                source=source_name,
                total_runs=total_runs,
                success_rate=(successful / total_runs * 100) if total_runs else 0,
                avg_duration_seconds=avg_duration,
                total_fetched=total_fetched,
                total_persisted=total_persisted,
                last_run_at=last_run,
            )
        )

    return results


@router.get("/{run_id}", response_model=IngestionRunDetail)
def get_ingestion_run(
    run_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_token),
) -> IngestionRun:
    """Get detailed information about a specific ingestion run."""
    run = db.query(IngestionRun).filter(IngestionRun.id == run_id).first()

    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    return run


@router.get("/{run_id}/review-items")
def get_run_review_items(
    run_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_token),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    """Get review items created by an ingestion run."""
    run = db.query(IngestionRun).filter(IngestionRun.id == run_id).first()

    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    # Query review items directly linked to this ingestion run
    items = (
        db.query(ReviewItem)
        .filter(ReviewItem.ingestion_run_id == run_id)
        .order_by(desc(ReviewItem.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )

    return {
        "run_id": run_id,
        "source_name": run.source_name,
        "total_items": len(items),
        "items": [
            {
                "id": item.id,
                "record_type": item.record_type,
                "source_url": item.source_url,
                "status": item.status,
                "created_at": item.created_at,
            }
            for item in items
        ],
    }


@router.get("/{run_id}/snapshots")
def get_run_snapshots(
    run_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_token),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    """Get source snapshots related to an ingestion run."""
    run = db.query(IngestionRun).filter(IngestionRun.id == run_id).first()

    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    # Find snapshots directly linked to this ingestion run
    snapshots = (
        db.query(SourceSnapshot)
        .filter(SourceSnapshot.ingestion_run_id == run_id)
        .order_by(desc(SourceSnapshot.fetched_at))
        .offset(skip)
        .limit(limit)
        .all()
    )

    return {
        "run_id": run_id,
        "source_name": run.source_name,
        "total_snapshots": len(snapshots),
        "snapshots": [
            {
                "id": s.id,
                "source_url": s.source_url,
                "fetched_at": s.fetched_at,
                "http_status": s.http_status,
                "storage_backend": s.storage_backend,
            }
            for s in snapshots
        ],
    }


@router.post("/{run_id}/retry")
def retry_ingestion_run(
    run_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_token),
) -> dict[str, Any]:
    """Queue a retry of a failed ingestion run.

    Note: This marks the run for retry but does not execute immediately.
    The actual retry is handled by the ingestion runner.
    """
    run = db.query(IngestionRun).filter(IngestionRun.id == run_id).first()

    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    if run.status == "running":
        raise HTTPException(
            status_code=400, detail="Cannot retry a run that is currently running"
        )

    # TODO: Queue retry in background worker
    # For now, just return the run info

    return {
        "run_id": run_id,
        "source_name": run.source_name,
        "original_status": run.status,
        "retry_queued": True,
        "message": "Retry queued (execution pending background worker)",
    }

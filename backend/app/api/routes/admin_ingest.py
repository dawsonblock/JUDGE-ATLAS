"""Admin ingestion endpoint.

Triggers manual ingestion runs for each open-data source.
Guarded by JTA_ENABLE_ADMIN_IMPORTS and admin token.
"""
from __future__ import annotations

import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth.admin import require_admin_imports
from app.core.config import get_settings
from app.core.rate_limit import rate_limit_ingestion
from app.core.request_utils import read_upload_file_limited
from app.db.session import get_db
from app.ingestion.gdelt import fetch_gdelt_articles, import_gdelt_articles
from app.ingestion.crime_sources.chicago_socrata import import_chicago_csv
from app.ingestion.crime_sources.toronto import import_toronto_csv
from app.ingestion.crime_sources.saskatoon import import_saskatoon_csv
from app.ingestion.crime_sources.los_angeles import import_la_csv
from app.ingestion.crime_sources.statscan import import_statscan_csv
from app.ingestion.crime_sources.fbi_crime_data import import_fbi_json

router = APIRouter(prefix="/api/admin/ingest", tags=["admin"])


def _require_imports(
    db: Session = Depends(get_db),
    _=Depends(require_admin_imports),
    __=Depends(rate_limit_ingestion),
) -> Session:
    return db


@router.post("/gdelt")
def ingest_gdelt(db: Session = Depends(_require_imports)):
    """Fetch and import GDELT news articles."""
    settings = get_settings()
    if not settings.gdelt_enabled:
        raise HTTPException(status_code=403, detail="GDELT feed disabled")
    articles = fetch_gdelt_articles()
    if articles is None:
        raise HTTPException(status_code=502, detail="GDELT fetch failed")
    result = import_gdelt_articles(db, articles)
    return result.__dict__


@router.post("/chicago")
async def ingest_chicago(
    file: UploadFile = File(...),
    db: Session = Depends(_require_imports),
):
    """Import Chicago Data Portal crime CSV upload."""
    settings = get_settings()
    if not settings.local_feeds_enabled:
        raise HTTPException(status_code=403, detail="Local feeds disabled")
    content = await read_upload_file_limited(file, settings.max_csv_upload_size)
    stream = io.StringIO(content.decode("utf-8-sig"))
    result = import_chicago_csv(db, stream)
    return result.__dict__


@router.post("/toronto")
async def ingest_toronto(
    file: UploadFile = File(...),
    db: Session = Depends(_require_imports),
):
    """Import Toronto Police CSV upload."""
    settings = get_settings()
    if not settings.local_feeds_enabled:
        raise HTTPException(status_code=403, detail="Local feeds disabled")
    content = await read_upload_file_limited(file, settings.max_csv_upload_size)
    stream = io.StringIO(content.decode("utf-8-sig"))
    result = import_toronto_csv(db, stream)
    return result.__dict__


@router.post("/saskatoon")
async def ingest_saskatoon(
    file: UploadFile = File(...),
    db: Session = Depends(_require_imports),
):
    """Import Saskatoon Police CSV upload."""
    settings = get_settings()
    if not settings.local_feeds_enabled:
        raise HTTPException(status_code=403, detail="Local feeds disabled")
    content = await read_upload_file_limited(file, settings.max_csv_upload_size)
    stream = io.StringIO(content.decode("utf-8-sig"))
    result = import_saskatoon_csv(db, stream)
    return result.__dict__


@router.post("/los-angeles")
async def ingest_los_angeles(
    file: UploadFile = File(...),
    db: Session = Depends(_require_imports),
):
    """Import LA Open Data crime CSV upload."""
    settings = get_settings()
    if not settings.local_feeds_enabled:
        raise HTTPException(status_code=403, detail="Local feeds disabled")
    content = await read_upload_file_limited(file, settings.max_csv_upload_size)
    stream = io.StringIO(content.decode("utf-8-sig"))
    result = import_la_csv(db, stream)
    return result.__dict__


@router.post("/statscan")
def ingest_statscan(
    file: UploadFile = File(...),
    db: Session = Depends(_require_imports),
):
    """Import Statistics Canada CSV upload."""
    settings = get_settings()
    if not settings.statscan_enabled:
        raise HTTPException(status_code=403, detail="StatsCan feed disabled")
    content = file.file.read()
    stream = io.StringIO(content.decode("utf-8-sig"))
    result = import_statscan_csv(db, stream)
    return result.__dict__


@router.post("/fbi")
def ingest_fbi(
    payload: list[dict],
    db: Session = Depends(_require_imports),
):
    """Import FBI Crime Data JSON payload."""
    settings = get_settings()
    if not settings.fbi_crime_enabled:
        raise HTTPException(status_code=403, detail="FBI feed disabled")
    result = import_fbi_json(db, payload)
    return result.__dict__


# ---------------------------------------------------------------------------
# CourtListener bulk-data endpoints
# ---------------------------------------------------------------------------

@router.get("/courtlistener-bulk/runs")
def cl_bulk_runs(db: Session = Depends(_require_imports)):
    """List all CourtListener bulk import run records."""
    from sqlalchemy import select as _select
    from app.models.entities import CourtListenerBulkRun
    runs = db.scalars(
        _select(CourtListenerBulkRun).order_by(
            CourtListenerBulkRun.id.desc()
        )
    ).all()
    return [
        {
            "id": r.id,
            "snapshot_date": r.snapshot_date,
            "file_name": r.file_name,
            "status": r.status,
            "rows_read": r.rows_read,
            "rows_persisted": r.rows_persisted,
            "rows_skipped": r.rows_skipped,
            "errors": (r.errors or [])[:10],
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": (
                r.finished_at.isoformat() if r.finished_at else None
            ),
        }
        for r in runs
    ]


@router.post("/courtlistener-bulk/list")
def cl_bulk_list(db: Session = Depends(_require_imports)):
    """List CSV files available in the configured bulk_data_dir."""
    import os
    settings = get_settings()
    data_dir = settings.courtlistener_bulk_data_dir
    if not os.path.isdir(data_dir):
        raise HTTPException(
            status_code=404,
            detail=f"bulk_data_dir not found: {data_dir}",
        )
    files = [
        f for f in sorted(os.listdir(data_dir)) if f.endswith(".csv")
    ]
    return {
        "data_dir": data_dir,
        "snapshot_date": settings.courtlistener_bulk_snapshot_date,
        "files": files,
    }


@router.post("/courtlistener-bulk/import")
def cl_bulk_import(
    payload: dict | None = None,
    db: Session = Depends(_require_imports),
):
    """Trigger bulk normalization for a snapshot date.

    Body (optional JSON):
        {"snapshot_date": "2026-03-31", "files": ["courts","dockets"],
         "force": false, "include_opinions": false}
    """
    import os
    from app.ingestion.courtlistener_bulk_normalizer import (
        get_or_create_bulk_run,
        mark_run_done,
        mark_run_failed,
        mark_run_started,
        normalize_clusters,
        normalize_courts,
        normalize_dockets,
        normalize_opinions,
        normalize_people,
        normalize_positions,
    )

    _NORMALIZERS = {
        "courts": normalize_courts,
        "people-db-people": normalize_people,
        "people-db-positions": normalize_positions,
        "dockets": normalize_dockets,
        "opinion-clusters": normalize_clusters,
        "opinions": normalize_opinions,
    }
    _ORDER = [
        "courts", "people-db-people", "people-db-positions",
        "dockets", "opinion-clusters",
    ]

    settings = get_settings()
    body = payload or {}
    snapshot_date = str(
        body.get("snapshot_date") or settings.courtlistener_bulk_snapshot_date or ""
    )
    if not snapshot_date:
        raise HTTPException(
            status_code=422, detail="snapshot_date required"
        )
    force = bool(body.get("force", False))
    include_opinions = bool(
        body.get("include_opinions", settings.courtlistener_bulk_include_opinions)
    )
    enabled = [
        s.strip()
        for s in str(
            body.get("files") or settings.courtlistener_bulk_enabled_files
        ).split(",")
        if s.strip()
    ]
    ordered = [s for s in _ORDER if s in enabled]
    if include_opinions:
        ordered.append("opinions")

    data_dir = settings.courtlistener_bulk_data_dir
    results = []
    for stem in ordered:
        csv_path = None
        for fname in sorted(os.listdir(data_dir)):
            if fname.startswith(stem) and fname.endswith(".csv"):
                csv_path = os.path.join(data_dir, fname)
                break
        if not csv_path:
            results.append({"file": stem, "status": "skipped_no_file"})
            continue

        run = get_or_create_bulk_run(db, snapshot_date, stem)
        if run.status in ("done", "done_with_errors") and not force:
            results.append({
                "file": stem,
                "status": "skipped_already_done",
                "rows_persisted": run.rows_persisted,
            })
            continue
        if force and run.status != "pending":
            db.delete(run)
            db.flush()
            run = get_or_create_bulk_run(db, snapshot_date, stem)

        mark_run_started(db, run)
        try:
            with open(csv_path, encoding="utf-8", errors="replace") as fh:
                result = _NORMALIZERS[stem](
                    db,
                    fh,
                    settings.courtlistener_bulk_import_batch_size,
                    run.id,
                    stem,
                    snapshot_date,
                )
            mark_run_done(db, run, result)
            db.commit()
            results.append({
                "file": stem,
                "status": run.status,
                "rows_read": result.rows_read,
                "rows_persisted": result.rows_persisted,
                "rows_skipped": result.rows_skipped,
                "error_count": len(result.errors),
            })
        except Exception as exc:
            mark_run_failed(db, run, exc)
            db.commit()
            results.append({"file": stem, "status": "failed", "error": str(exc)})

    return {"snapshot_date": snapshot_date, "results": results}


@router.post("/courtlistener-bulk/normalize")
def cl_bulk_normalize(
    payload: dict | None = None,
    db: Session = Depends(_require_imports),
):
    """Re-run normalization only (skips file-existence check for already-imported rows).

    Delegates to /import with force=True but only for already-downloaded files.
    """
    body = dict(payload or {})
    body["force"] = True
    return cl_bulk_import(body, db)

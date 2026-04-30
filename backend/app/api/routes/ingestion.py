from datetime import datetime
from io import StringIO

from fastapi import APIRouter, Depends, Query, Request, UploadFile, File
from sqlalchemy.orm import Session

from app.auth.admin import require_admin_imports
from app.core.config import get_settings
from app.core.rate_limit import rate_limit_ingestion
from app.core.request_utils import read_upload_file_limited
from app.db.session import get_db
from app.ingestion.crime_sources.manual_csv import import_crime_incidents_csv
from app.ingestion.runner import run_courtlistener_ingestion
from app.models.entities import IngestionRun

router = APIRouter()


@router.post("/api/admin/import/crime-incidents/manual-csv", dependencies=[Depends(require_admin_imports), Depends(rate_limit_ingestion)])
async def import_crime_incidents_manual_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Import crime incidents from CSV with size limits."""
    settings = get_settings()

    # Read file with size limit enforcement
    content = await read_upload_file_limited(file, settings.max_csv_upload_size)
    text = content.decode("utf-8-sig")
    result = import_crime_incidents_csv(db, StringIO(text))
    return {
        "read_count": result.read_count,
        "persisted_count": result.persisted_count,
        "skipped_count": result.skipped_count,
        "error_count": result.error_count,
        "errors": result.errors,
    }


@router.post("/api/ingest/courtlistener", dependencies=[Depends(require_admin_imports), Depends(rate_limit_ingestion)])
def ingest_courtlistener(since: datetime = Query(...), db: Session = Depends(get_db)):
    run: IngestionRun = run_courtlistener_ingestion(db, since)
    return {
        "id": run.id,
        "status": run.status,
        "fetched_count": run.fetched_count,
        "parsed_count": run.parsed_count,
        "persisted_count": run.persisted_count,
        "skipped_count": run.skipped_count,
        "error_count": run.error_count,
        "errors": run.errors or [],
    }

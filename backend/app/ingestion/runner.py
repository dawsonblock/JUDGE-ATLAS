import threading
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.ingestion.courtlistener import CourtListenerAdapter
from app.ingestion.persistence import persist_parsed_record
from app.ingestion.source_registry_ctl import (
    check_ingestion_allowed,
    require_source_registry,
    update_source_health,
)
from app.models.entities import IngestionRun

# Ingestion lock to prevent concurrent CourtListener runs
_ingestion_lock = threading.Lock()


def run_courtlistener_ingestion(db: Session, since: datetime) -> IngestionRun:
    settings = get_settings()
    max_dockets = settings.courtlistener_max_dockets_per_run

    # Check SourceRegistry control plane
    registry = require_source_registry(
        db, source_key="courtlistener", source_name="CourtListener API"
    )
    allowed, reason = check_ingestion_allowed(registry)

    if not allowed:
        run = IngestionRun(
            source_name="courtlistener",
            started_at=datetime.now(timezone.utc),
            status="failed",
            errors=[f"Ingestion blocked: {reason}"],
        )
        run.error_count = 1
        run.finished_at = datetime.now(timezone.utc)
        db.add(run)
        db.commit()
        db.refresh(run)
        return run

    # Acquire lock to prevent concurrent ingestion
    if not _ingestion_lock.acquire(blocking=False):
        run = IngestionRun(
            source_name="courtlistener",
            started_at=datetime.now(timezone.utc),
            status="failed",
            errors=["Concurrent ingestion already in progress"],
        )
        run.error_count = 1
        run.finished_at = datetime.now(timezone.utc)
        db.add(run)
        db.commit()
        db.refresh(run)
        return run

    run = IngestionRun(source_name="courtlistener", started_at=datetime.now(timezone.utc), status="running", errors=[])
    db.add(run)
    db.flush()

    adapter = CourtListenerAdapter()
    parsed_count = 0
    persisted_count = 0
    skipped_count = 0
    fetched_count = 0
    errors: list[str] = []
    try:
        records = adapter.fetch(since)
        # Apply dockets per run cap
        records = records[:max_dockets]
        fetched_count = len(records)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        run = IngestionRun(source_name="courtlistener", started_at=datetime.now(timezone.utc), status="completed_with_errors", errors=[str(exc)])
        run.error_count = 1
        run.finished_at = datetime.now(timezone.utc)
        db.add(run)
        db.commit()
        db.refresh(run)
        _ingestion_lock.release()
        return run

    for raw in records:
        try:
            with db.begin_nested():
                if hasattr(adapter, "parse_many"):
                    parsed_list = adapter.parse_many(raw)
                else:
                    parsed_list = [adapter.parse(raw)]
                for parsed in parsed_list:
                    parsed_count += 1
                    result = persist_parsed_record(db, parsed)
                    if result.persisted:
                        persisted_count += 1
                    if result.skipped:
                        skipped_count += 1
        except Exception as exc:  # noqa: BLE001 - ingestion isolates bad records by design
            errors.append(str(exc))

    errors.extend(adapter.errors)
    run.fetched_count = fetched_count
    run.parsed_count = parsed_count
    run.persisted_count = persisted_count
    run.skipped_count = skipped_count
    run.error_count = len(errors)
    run.errors = errors
    run.status = "completed_with_errors" if errors else "completed"
    run.finished_at = datetime.now(timezone.utc)
    try:
        db.commit()
        db.refresh(run)
        # Update SourceRegistry health
        update_source_health(db, "courtlistener", run)
    finally:
        _ingestion_lock.release()
    return run

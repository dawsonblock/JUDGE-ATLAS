"""Canonical snapshot writer service for source snapshots.

This service provides a unified interface for writing source snapshots,
supporting both filesystem storage (via EvidenceStore) and database fallback.
All snapshot writes should go through this service to ensure consistency.
"""

import hashlib
import json
import os
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.models.entities import SourceSnapshot
from app.services.evidence_store import EvidenceStore

if TYPE_CHECKING:
    pass


# Maximum size for DB storage (1MB)
MAX_DB_SIZE = 1024 * 1024


def write_snapshot(
    db: Session,
    source_url: str,
    fetched_at: datetime,
    content: bytes | str,
    extracted_text: str | None = None,
    headers: dict | None = None,
    http_status: int | None = None,
    content_type: str | None = None,
    error_message: str | None = None,
    ingestion_run_id: int | None = None,
) -> SourceSnapshot:
    """Write a source snapshot using canonical storage logic.
    
    This service decides where to store the snapshot based on configuration:
    - If JTA_EVIDENCE_STORE_ROOT is set and usable: store in filesystem
    - Otherwise: store in database (with size limit)
    
    Args:
        db: Database session
        source_url: URL of the source
        fetched_at: Timestamp when content was fetched
        content: Raw content as bytes or string
        extracted_text: Extracted plain text (optional)
        headers: HTTP headers dict (optional)
        http_status: HTTP status code (optional)
        content_type: Content-Type header (optional)
        error_message: Error message if fetch failed (optional)
        ingestion_run_id: ID of the ingestion run that created this snapshot (optional)
        
    Returns:
        SourceSnapshot: Created or updated snapshot record
    """
    # Convert content to bytes if needed
    if isinstance(content, str):
        content_bytes = content.encode("utf-8")
        content_text = content
    else:
        content_bytes = content
        content_text = content.decode("utf-8", errors="replace")
    
    # Compute SHA256 hash
    content_hash = hashlib.sha256(content_bytes).hexdigest()
    
    # Determine storage backend
    evidence_root = os.getenv("JTA_EVIDENCE_STORE_ROOT")
    
    if evidence_root:
        # Try filesystem storage
        try:
            evidence_store = EvidenceStore(root_path=evidence_root)
            storage_path = evidence_store.store(content_bytes, content_hash)
            storage_backend = "filesystem"
            raw_content = None  # Don't store in DB
        except Exception:
            # Fallback to DB on error
            storage_backend = "db"
            storage_path = None
            raw_content = content_text[:MAX_DB_SIZE]
    else:
        # Store in DB
        storage_backend = "db"
        storage_path = None
        raw_content = content_text[:MAX_DB_SIZE]
    
    # Create SourceSnapshot
    snapshot = SourceSnapshot(
        source_url=source_url,
        fetched_at=fetched_at,
        content_hash=content_hash,
        raw_content=raw_content,
        extracted_text=extracted_text,
        http_status=http_status,
        content_type=content_type,
        headers_json=json.dumps(headers) if headers else None,
        error_message=error_message,
        storage_backend=storage_backend,
        storage_path=storage_path,
        ingestion_run_id=ingestion_run_id,
    )
    
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    
    return snapshot


def read_snapshot_content(db: Session, snapshot: SourceSnapshot) -> bytes | None:
    """Read snapshot content from appropriate storage backend.
    
    Args:
        db: Database session
        snapshot: SourceSnapshot record
        
    Returns:
        Raw content as bytes, or None if unavailable
    """
    if snapshot.storage_backend == "filesystem" and snapshot.storage_path:
        try:
            evidence_root = os.getenv("JTA_EVIDENCE_STORE_ROOT")
            if evidence_root:
                evidence_store = EvidenceStore(root_path=evidence_root)
                return evidence_store.read(snapshot.storage_path)
        except Exception:
            # Fall through to DB fallback
            pass
    
    # DB fallback
    if snapshot.raw_content:
        return snapshot.raw_content.encode("utf-8")
    
    return None

"""SourceRegistry integration for ingestion control.

Provides control plane integration with SourceRegistry:
- Check if ingestion is enabled for a source
- Determine review requirements
- Update source health after ingestion runs
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.models.entities import SourceRegistry

if TYPE_CHECKING:
    from app.models.entities import IngestionRun


def require_source_registry(
    db: Session,
    source_key: str,
    source_name: str | None = None,
) -> SourceRegistry:
    """Require a SourceRegistry entry, failing closed if missing.

    If the source_key doesn't exist, creates a new disabled registry entry
    that must be explicitly enabled by an admin.

    Args:
        db: Database session
        source_key: Unique source identifier (e.g., "courtlistener")
        source_name: Human-readable name (optional)

    Returns:
        SourceRegistry row

    Raises:
        ValueError: If source_key is empty
    """
    if not source_key:
        raise ValueError("source_key is required")

    registry = db.query(SourceRegistry).filter_by(source_key=source_key).first()

    if registry is None:
        # Create disabled entry - fail closed on missing registry
        registry = SourceRegistry(
            source_key=source_key,
            source_name=source_name or source_key,
            is_active=False,
            requires_manual_review=True,
            auto_publish_enabled=False,
            last_error=f"Auto-created on {datetime.now(timezone.utc).isoformat()}. "
                       f"Enable explicitly in admin panel.",
        )
        db.add(registry)
        db.commit()
        db.refresh(registry)

    return registry


def check_ingestion_allowed(registry: SourceRegistry) -> tuple[bool, str]:
    """Check if ingestion is allowed for this source.

    Returns:
        (is_allowed, reason)
    """
    if not registry.is_active:
        return False, f"Source {registry.source_key} is disabled in registry"

    return True, "ok"


def update_source_health(
    db: Session,
    source_key: str,
    run: "IngestionRun",
) -> None:
    """Update SourceRegistry health metrics after ingestion run.

    Args:
        db: Database session
        source_key: Source identifier
        run: Completed IngestionRun with metrics
    """
    registry = db.query(SourceRegistry).filter_by(source_key=source_key).first()
    if registry is None:
        return

    if run.status in ("completed", "completed_with_errors"):
        registry.last_successful_fetch = datetime.now(timezone.utc)
        # Clear error if successful
        if run.status == "completed" and run.error_count == 0:
            registry.last_error = None
            registry.last_error_at = None
    else:
        registry.last_error = f"Status: {run.status}"
        if run.errors:
            error_msg = str(run.errors[0])
            registry.last_error = f"Status: {run.status}, Error: {error_msg[:200]}"
        registry.last_error_at = datetime.now(timezone.utc)

    db.commit()


def get_review_requirement(registry: SourceRegistry) -> bool:
    """Determine if records from this source require manual review.

    Returns:
        True if records need admin review before publishing
    """
    return registry.requires_manual_review


def get_auto_publish_policy(registry: SourceRegistry) -> bool:
    """Determine if records should be auto-published after review.

    Returns:
        True if records should auto-publish (when review passes)
    """
    return registry.auto_publish_enabled

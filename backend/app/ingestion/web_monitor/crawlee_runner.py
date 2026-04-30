"""Crawlee-based web monitoring runner with strict safety controls.

This runner provides controlled fetching of known public pages only.
It enforces strict allowlists, request limits, and safety rules.

Safety features:
- Strict domain allowlist enforcement
- Request counting with hard stop at max_requests
- Low concurrency by default
- All fetched content defaults to pending_review
- Integration with SourceRegistry control plane
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.ingestion.source_registry_ctl import (
    check_ingestion_allowed,
    require_source_registry,
    update_source_health,
)
from app.models.entities import IngestionRun, SourceSnapshot

if TYPE_CHECKING:
    from app.ingestion.web_monitor.source_targets import WebMonitorTarget


class CrawleeRunner:
    """Controlled web monitoring runner using Crawlee.

    Enforces strict safety limits and never performs open-ended crawling.
    """

    def __init__(self, target: "WebMonitorTarget", db: Session):
        """Initialize runner with target configuration.

        Args:
            target: WebMonitorTarget configuration
            db: Database session
        """
        self.target = target
        self.db = db
        self.request_count = 0
        self.snapshots: list[SourceSnapshot] = []
        self.errors: list[str] = []

    def _is_url_allowed(self, url: str) -> bool:
        """Check if URL is in the allowed domains list.

        Args:
            url: URL to check

        Returns:
            True if allowed, False otherwise
        """
        return self.target.is_url_allowed(url)

    def _check_request_limit(self) -> bool:
        """Check if we've reached the request limit.

        Returns:
            True if under limit, False if limit reached
        """
        if self.request_count >= self.target.max_requests:
            return False
        return True

    def _create_snapshot(
        self,
        source_url: str,
        http_status: int,
        content_type: str | None,
        content: bytes | str,
        title: str | None = None,
        text_excerpt: str | None = None,
    ) -> SourceSnapshot:
        """Create a source snapshot from fetched content.

        Args:
            source_url: Fetched URL
            http_status: HTTP status code
            content_type: Content-Type header
            content: Raw content (bytes or string)
            title: Page title if extracted (stored in raw_content field)
            text_excerpt: Text excerpt if extracted

        Returns:
            SourceSnapshot entity
        """
        # Calculate content hash
        if isinstance(content, str):
            content_bytes = content.encode("utf-8")
            raw_content = content
        else:
            content_bytes = content
            raw_content = content.decode("utf-8", errors="replace")
        content_hash = hashlib.sha256(content_bytes).hexdigest()

        # Build metadata string with target info
        metadata = f"[Target: {self.target.name}]"
        if title:
            metadata += f" [Title: {title}]"

        snapshot = SourceSnapshot(
            source_url=source_url,
            fetched_at=datetime.now(timezone.utc),
            http_status=http_status,
            content_type=content_type or "unknown",
            content_hash=content_hash,
            raw_content=f"{metadata}\n\n{raw_content[:10000]}",  # Limit size, include metadata
            extracted_text=text_excerpt[:2000] if text_excerpt else None,
            storage_backend="db",
        )
        return snapshot

    def run(self) -> IngestionRun:
        """Execute the web monitoring run.

        Returns:
            IngestionRun with metrics and status
        """
        from crawlee import Request
        from crawlee.crawlers import HttpCrawler

        # Check SourceRegistry control plane
        registry_key = f"web_monitor_{self.target.name.lower().replace(' ', '_')}"
        registry = require_source_registry(
            self.db,
            source_key=registry_key,
            source_name=self.target.name,
        )

        allowed, reason = check_ingestion_allowed(registry)
        if not allowed:
            run = IngestionRun(
                source_name=registry_key,
                started_at=datetime.now(timezone.utc),
                status="failed",
                errors=[f"Ingestion blocked: {reason}"],
            )
            run.error_count = 1
            run.fetched_count = 0
            run.parsed_count = 0
            run.persisted_count = 0
            run.finished_at = datetime.now(timezone.utc)
            self.db.add(run)
            self.db.commit()
            return run

        # Initialize run tracking
        run = IngestionRun(
            source_name=registry_key,
            started_at=datetime.now(timezone.utc),
            status="running",
            errors=[],
        )
        self.db.add(run)
        self.db.flush()

        # Track metrics
        fetched_count = 0
        parsed_count = 0
        persisted_count = 0

        try:
            # Create crawler with safety limits
            config = self.target.get_crawlee_config()

            crawler = HttpCrawler(
                max_requests_per_crawl=config["max_requests_per_crawl"],
                max_crawl_depth=config["max_crawl_depth"],
                max_concurrency=config["max_concurrency"],
            )

            @crawler.router.default_handler
            async def handler(context) -> None:
                """Handle each crawled page."""
                nonlocal fetched_count, parsed_count, persisted_count

                # Check request limit
                if not self._check_request_limit():
                    context.log.warning(f"Request limit ({self.target.max_requests}) reached")
                    return

                # Check allowlist
                url = str(context.request.url)
                if not self._is_url_allowed(url):
                    context.log.warning(f"URL not in allowlist: {url}")
                    return

                try:
                    # Extract content
                    response = context.http.response
                    content = await response.text()
                    content_type = response.headers.get("content-type", "unknown")
                    http_status = response.status_code

                    # Try to extract title from HTML
                    title = None
                    import re
                    title_match = re.search(r"<title[^>]*>([^<]*)</title>", content, re.IGNORECASE)
                    if title_match:
                        title = title_match.group(1).strip()
                    text_excerpt = content[:2000] if content else None

                    # Create snapshot
                    snapshot = self._create_snapshot(
                        source_url=url,
                        http_status=http_status,
                        content_type=content_type,
                        content=content,
                        title=title,
                        text_excerpt=text_excerpt,
                    )

                    self.snapshots.append(snapshot)
                    self.db.add(snapshot)

                    # Extract candidate using appropriate extractor
                    from app.ingestion.web_monitor.extractors import extract_from_page
                    try:
                        candidate = extract_from_page(
                            url=url,
                            content=content,
                            title=title,
                            extractor_type=self.target.extractor_type,
                        )
                        # TODO: In Phase 5, save candidate to pending_review queue
                        context.log.info(f"Extracted candidate from {url}: {candidate.candidate_type}")
                    except Exception as extract_err:
                        error_msg = f"Extractor failed for {url}: {str(extract_err)}"
                        self.errors.append(error_msg)
                        context.log.warning(error_msg)

                    fetched_count += 1
                    parsed_count += 1
                    persisted_count += 1
                    self.request_count += 1

                    context.log.info(f"Fetched {url} ({http_status})")

                except Exception as e:
                    error_msg = f"Error processing {url}: {str(e)}"
                    self.errors.append(error_msg)
                    context.log.error(error_msg)

            # Run crawler with start URLs
            start_requests = [
                Request(url=url) for url in self.target.start_urls
            ]

            # Execute crawl
            crawler.run(start_requests)

            # Update run status
            run.fetched_count = fetched_count
            run.parsed_count = parsed_count
            run.persisted_count = persisted_count
            run.error_count = len(self.errors)
            run.errors = self.errors
            run.status = "completed_with_errors" if self.errors else "completed"
            run.finished_at = datetime.now(timezone.utc)

            self.db.commit()

            # Update source registry health
            update_source_health(self.db, registry_key, run)

        except Exception as e:
            # Handle fatal errors
            run.status = "failed"
            run.errors.append(f"Fatal error: {str(e)}")
            run.error_count = len(run.errors)
            run.fetched_count = fetched_count
            run.parsed_count = parsed_count
            run.persisted_count = persisted_count
            run.finished_at = datetime.now(timezone.utc)
            self.db.commit()

        return run


def run_web_monitor_target(target: "WebMonitorTarget", db: Session) -> IngestionRun:
    """Run web monitoring for a specific target.

    Convenience function to create runner and execute.

    Args:
        target: WebMonitorTarget configuration
        db: Database session

    Returns:
        IngestionRun with results
    """
    runner = CrawleeRunner(target, db)
    return runner.run()

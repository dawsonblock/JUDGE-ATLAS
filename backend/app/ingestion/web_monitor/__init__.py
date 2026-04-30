"""Web monitoring module for controlled source evidence capture.

This module provides controlled web monitoring for known public pages only.
It does NOT perform open-ended web crawling or mass scraping.

Safety rules:
- All output defaults to review_status = pending_review
- Strict allowlists only - no open-ended crawling
- Respects robots.txt and site terms
- Never publishes directly to public APIs
- Passes through source_verifier, public_safety, and publish_rules

Flow:
known source target -> Crawlee fetch -> snapshot -> extractor -> candidate item
-> pending_review -> publication gate -> public map (after approval only)
"""

from app.ingestion.web_monitor.source_targets import WebMonitorTarget

__all__ = ["WebMonitorTarget"]

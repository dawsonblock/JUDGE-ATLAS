"""Source fetching service with snapshot persistence.

Provides URL fetching with:
- SSRF protection (private IPs, localhost blocked)
- Content hash storage
- SourceSnapshot persistence for provenance
- Size limits and timeout enforcement
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import logging
import socket
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.entities import SourceSnapshot

log = logging.getLogger(__name__)

# Max download size (bytes)
_DEFAULT_MAX_BYTES = 512_000

# Private/reserved IP ranges to block
_PRIVATE_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local
    ipaddress.ip_network("100.64.0.0/10"),   # CGNAT
    ipaddress.ip_network("224.0.0.0/4"),     # Multicast
    ipaddress.ip_network("240.0.0.0/4"),     # Reserved (class E)
    ipaddress.ip_network("fc00::/7"),       # IPv6 unique local
    ipaddress.ip_network("fe80::/10"),       # IPv6 link-local
)


@dataclass
class FetchResult:
    """Result of a source fetch operation."""

    url: str
    final_url: str | None
    fetched_at: datetime
    http_status: int | None
    content_type: str | None
    headers: dict[str, str]
    raw_content: bytes | None
    raw_content_hash: str | None
    extracted_text: str | None
    extracted_text_hash: str | None
    error: str | None
    snapshot_id: int | None = None


def _is_safe_url(url: str, check_dns: bool = True) -> tuple[bool, str]:
    """Validate URL is safe to fetch (no SSRF).
    
    Args:
        url: URL to validate
        check_dns: If True, also check if hostname resolves to private IP
    """
    try:
        parsed = urllib.parse.urlparse(url)

        # Scheme check
        if parsed.scheme not in ("http", "https"):
            return False, f"scheme '{parsed.scheme}' not allowed"

        # Host check
        host = parsed.hostname
        if not host:
            return False, "missing hostname"

        # Localhost check
        if host.lower() in ("localhost", "127.0.0.1", "::1"):
            return False, "localhost not allowed"

        # Block cloud metadata IPs (direct and Azure/AWS variants)
        if host in ("169.254.169.254", "fd00:ec2::254", "metadata.google.internal",
                    "metadata.internal", "100.100.100.200"):
            return False, "cloud metadata IP blocked"

        # IP address check (blocks private ranges)
        is_ip = False
        try:
            addr = ipaddress.ip_address(host)
            is_ip = True
            for network in _PRIVATE_NETWORKS:
                if addr in network:
                    return False, f"private IP {host} not allowed"
        except ValueError:
            pass  # Not an IP, it's a hostname

        # DNS resolution check for hostnames (prevents DNS rebinding)
        if check_dns and not is_ip:
            try:
                resolved = socket.getaddrinfo(host, None)
                for family, _, _, _, sockaddr in resolved:
                    ip_str = sockaddr[0]
                    try:
                        addr = ipaddress.ip_address(ip_str)
                        for network in _PRIVATE_NETWORKS:
                            if addr in network:
                                return False, f"hostname resolves to private IP {ip_str}"
                    except ValueError:
                        continue
            except socket.gaierror:
                return False, f"could not resolve hostname {host}"
            except Exception:
                pass  # Continue if DNS check fails

        return True, "ok"
    except Exception as exc:
        return False, f"URL parse error: {exc}"


class _SSRFRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Custom redirect handler that validates each redirect target."""
    
    max_redirections = 5
    
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        """Override to validate redirect URL before following."""
        # Validate the new URL
        is_safe, reason = _is_safe_url(newurl, check_dns=True)
        if not is_safe:
            log.warning("source_fetcher: blocked unsafe redirect to %s: %s", newurl, reason)
            raise urllib.request.HTTPError(
                newurl, code, f"Redirect blocked: {reason}", headers, fp
            )
        
        log.debug("source_fetcher: following redirect to %s", newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _sha256(data: bytes | str) -> str:
    """Compute SHA256 hash of data."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _extract_text_from_html(raw_bytes: bytes, content_type: str) -> str:
    """Simple text extraction from HTML."""
    from html.parser import HTMLParser

    class TextExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.parts: list[str] = []
            self.skip = {"script", "style", "noscript"}
            self.skip_depth = 0

        def handle_starttag(self, tag, attrs):
            if tag in self.skip:
                self.skip_depth += 1

        def handle_endtag(self, tag):
            if tag in self.skip and self.skip_depth > 0:
                self.skip_depth -= 1

        def handle_data(self, data):
            if self.skip_depth == 0:
                self.parts.append(data)

    try:
        charset = "utf-8"
        if "charset=" in content_type:
            charset = content_type.split("charset=")[-1].split(";")[0].strip()
        text = raw_bytes.decode(charset, errors="replace")
        extractor = TextExtractor()
        extractor.feed(text)
        return " ".join(extractor.parts)
    except Exception as exc:
        log.warning("Text extraction failed: %s", exc)
        return ""


def fetch_source(
    url: str,
    timeout: int = 30,
    max_bytes: int = _DEFAULT_MAX_BYTES,
    store_snapshot: bool = True,
) -> FetchResult:
    """Fetch a source URL with SSRF protection and optional snapshot storage.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        max_bytes: Maximum bytes to download
        store_snapshot: Whether to persist to SourceSnapshot table

    Returns:
        FetchResult with content and provenance info
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)

    result = FetchResult(
        url=url,
        final_url=None,
        fetched_at=now,
        http_status=None,
        content_type=None,
        headers={},
        raw_content=None,
        raw_content_hash=None,
        extracted_text=None,
        extracted_text_hash=None,
        error=None,
    )

    # SSRF check
    is_safe, reason = _is_safe_url(url)
    if not is_safe:
        result.error = f"SSRF blocked: {reason}"
        log.warning("source_fetcher: blocked unsafe URL %s: %s", url, reason)
        if store_snapshot:
            _persist_snapshot(result, settings)
        return result

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "JudgeTrackerAtlas/1.0 source-fetcher",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
            method="GET",
        )

        # Build opener with custom redirect handler for SSRF protection
        redirect_handler = _SSRFRedirectHandler()
        opener = urllib.request.build_opener(redirect_handler)
        
        with opener.open(req, timeout=timeout) as resp:
            result.http_status = resp.status
            result.final_url = resp.geturl()
            result.content_type = resp.headers.get_content_type() or ""

            # Store sanitized headers
            for key, value in resp.headers.items():
                if key.lower() not in ("set-cookie", "authorization"):
                    result.headers[key] = value

            # Read with size limit
            result.raw_content = resp.read(max_bytes + 1)
            if len(result.raw_content) > max_bytes:
                result.error = f"Content exceeds max_bytes: {max_bytes}"
                result.raw_content = result.raw_content[:max_bytes]

            # Compute hash
            if result.raw_content:
                result.raw_content_hash = _sha256(result.raw_content)

            # Extract text for HTML content
            if "text/html" in result.content_type and result.raw_content:
                result.extracted_text = _extract_text_from_html(
                    result.raw_content, result.content_type
                )
                if result.extracted_text:
                    result.extracted_text_hash = _sha256(result.extracted_text)

        log.info("source_fetcher: fetched %s (%s bytes)", url, len(result.raw_content or b""))

    except urllib.error.HTTPError as exc:
        result.http_status = exc.code
        result.error = f"HTTP error {exc.code}: {exc.reason}"
        log.warning("source_fetcher: HTTP %s for %s", exc.code, url)
    except Exception as exc:
        result.error = f"Fetch failed: {exc}"
        log.warning("source_fetcher: fetch failed for %s: %s", url, exc)

    if store_snapshot:
        _persist_snapshot(result, settings)

    return result


def _persist_snapshot(result: FetchResult, settings) -> int | None:
    """Persist fetch result to SourceSnapshot table."""
    try:
        # Truncate content for DB storage
        max_db_bytes = getattr(settings, "max_source_snapshot_db_bytes", 100_000)
        raw_for_db = result.raw_content
        if raw_for_db and len(raw_for_db) > max_db_bytes:
            raw_for_db = raw_for_db[:max_db_bytes]
            storage_backend = "db_truncated"
        else:
            storage_backend = "db"

        snapshot = SourceSnapshot(
            source_url=result.url,
            fetched_at=result.fetched_at,
            content_hash=result.raw_content_hash or "",
            raw_content=raw_for_db.decode("utf-8", errors="replace") if raw_for_db else None,
            extracted_text=result.extracted_text,
            http_status=result.http_status,
            content_type=result.content_type,
            headers_json=json.dumps(result.headers) if result.headers else None,
            error_message=result.error,
            storage_backend=storage_backend,
        )

        with SessionLocal() as db:
            db.add(snapshot)
            db.commit()
            result.snapshot_id = snapshot.id
            log.debug("source_fetcher: persisted snapshot id=%s", snapshot.id)
            return snapshot.id

    except Exception as exc:
        log.error("source_fetcher: failed to persist snapshot: %s", exc)
        return None


def get_snapshot_text(snapshot_id: int) -> str | None:
    """Retrieve extracted text from a snapshot by ID."""
    try:
        with SessionLocal() as db:
            snapshot = db.get(SourceSnapshot, snapshot_id)
            if snapshot:
                return snapshot.extracted_text
    except Exception as exc:
        log.warning("source_fetcher: failed to get snapshot %s: %s", snapshot_id, exc)
    return None

"""Tests for external snapshot storage integration.

Tests that crawlee runner correctly stores snapshots externally
when JTA_EVIDENCE_STORE_ROOT is configured.
"""

import hashlib
import os
import tempfile
from datetime import datetime, timezone

import pytest

from app.db.session import SessionLocal
from app.ingestion.web_monitor.crawlee_runner import CrawleeRunner
from app.ingestion.web_monitor.source_targets import WebMonitorTarget
from app.models.entities import SourceSnapshot
from app.services.evidence_store import EvidenceStore


class TestExternalSnapshotStorage:
    """Test external snapshot storage in crawlee runner."""

    def test_snapshot_stored_externally_when_env_set(self, db):
        """Snapshot should be stored externally when JTA_EVIDENCE_STORE_ROOT set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Set env var
            old_env = os.environ.get("JTA_EVIDENCE_STORE_ROOT")
            os.environ["JTA_EVIDENCE_STORE_ROOT"] = tmpdir
            try:
                target = WebMonitorTarget(
                    name="Test External",
                    source_type="news_only_context",
                    base_url="https://example.com",
                    allowed_domains=["example.com"],
                    start_urls=["https://example.com/"],
                    extractor_type="rss_or_news_listing",
                    source_tier="news_only_context",
                )
                runner = CrawleeRunner(target, db)

                content = b"<html><body>External storage test</body></html>"
                content_hash = hashlib.sha256(content).hexdigest()

                snapshot = runner._create_snapshot(
                    source_url="https://example.com/page1",
                    http_status=200,
                    content_type="text/html",
                    content=content,
                    title="Test Page",
                    text_excerpt="External storage test",
                )

                # Should be stored externally
                assert snapshot.storage_backend == "filesystem"
                assert snapshot.storage_path is not None
                assert snapshot.storage_path.startswith("snapshots/sha256/")
                assert snapshot.content_hash == content_hash

                # raw_content should be None (content stored externally)
                assert snapshot.raw_content is None

                # Verify file exists
                store = EvidenceStore(tmpdir)
                retrieved = store.read_snapshot(snapshot.storage_path)
                assert retrieved == content

            finally:
                if old_env:
                    os.environ["JTA_EVIDENCE_STORE_ROOT"] = old_env
                else:
                    os.environ.pop("JTA_EVIDENCE_STORE_ROOT", None)

    def test_snapshot_stored_in_db_when_env_not_set(self, db):
        """Snapshot should be stored in DB when JTA_EVIDENCE_STORE_ROOT not set."""
        # Ensure env var is not set
        old_env = os.environ.pop("JTA_EVIDENCE_STORE_ROOT", None)
        try:
            target = WebMonitorTarget(
                name="Test DB",
                source_type="news_only_context",
                base_url="https://example.com",
                allowed_domains=["example.com"],
                start_urls=["https://example.com/"],
                extractor_type="rss_or_news_listing",
                source_tier="news_only_context",
            )
            runner = CrawleeRunner(target, db)

            content = b"<html><body>DB storage test</body></html>"
            content_hash = hashlib.sha256(content).hexdigest()

            snapshot = runner._create_snapshot(
                source_url="https://example.com/page2",
                http_status=200,
                content_type="text/html",
                content=content,
                title="DB Test",
                text_excerpt="DB storage test",
            )

            # Should be stored in DB
            assert snapshot.storage_backend == "db"
            assert snapshot.storage_path is None
            assert snapshot.content_hash == content_hash

            # raw_content should have content
            assert snapshot.raw_content is not None
            assert "[Target: Test DB]" in snapshot.raw_content
            assert "DB storage test" in snapshot.raw_content

        finally:
            if old_env:
                os.environ["JTA_EVIDENCE_STORE_ROOT"] = old_env

    def test_metadata_stored_in_db_even_when_external(self, db):
        """Metadata should still be stored in DB even when content is external."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_env = os.environ.get("JTA_EVIDENCE_STORE_ROOT")
            os.environ["JTA_EVIDENCE_STORE_ROOT"] = tmpdir
            try:
                target = WebMonitorTarget(
                    name="Metadata Test",
                    source_type="news_only_context",
                    base_url="https://example.com",
                    allowed_domains=["example.com"],
                    start_urls=["https://example.com/"],
                    extractor_type="rss_or_news_listing",
                    source_tier="news_only_context",
                )
                runner = CrawleeRunner(target, db)

                content = b"<html>Content</html>"

                snapshot = runner._create_snapshot(
                    source_url="https://example.com/meta",
                    http_status=200,
                    content_type="text/html",
                    content=content,
                    title="Metadata Test Page",
                    text_excerpt="Extracted text",
                )

                # Metadata in DB
                assert snapshot.source_url == "https://example.com/meta"
                assert snapshot.http_status == 200
                assert snapshot.content_type == "text/html"
                assert snapshot.extracted_text == "Extracted text"

                # Content is external
                assert snapshot.storage_backend == "filesystem"
                assert snapshot.raw_content is None

            finally:
                if old_env:
                    os.environ["JTA_EVIDENCE_STORE_ROOT"] = old_env
                else:
                    os.environ.pop("JTA_EVIDENCE_STORE_ROOT", None)

    def test_extracted_text_always_in_db(self, db):
        """Extracted text should always be in DB regardless of storage backend."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_env = os.environ.get("JTA_EVIDENCE_STORE_ROOT")
            os.environ["JTA_EVIDENCE_STORE_ROOT"] = tmpdir
            try:
                target = WebMonitorTarget(
                    name="Extract Test",
                    source_type="news_only_context",
                    base_url="https://example.com",
                    allowed_domains=["example.com"],
                    start_urls=["https://example.com/"],
                    extractor_type="rss_or_news_listing",
                    source_tier="news_only_context",
                )
                runner = CrawleeRunner(target, db)

                content = b"<html><body>Page content for extraction</body></html>"
                excerpt = "Page content for extraction"

                snapshot = runner._create_snapshot(
                    source_url="https://example.com/extract",
                    http_status=200,
                    content_type="text/html",
                    content=content,
                    title="Extract Test",
                    text_excerpt=excerpt,
                )

                # extracted_text should be in DB
                assert snapshot.extracted_text == excerpt[:2000]
                assert snapshot.storage_backend == "filesystem"

            finally:
                if old_env:
                    os.environ["JTA_EVIDENCE_STORE_ROOT"] = old_env
                else:
                    os.environ.pop("JTA_EVIDENCE_STORE_ROOT", None)

    def test_fallback_to_db_on_storage_error(self, db):
        """Should fallback to DB storage if external storage fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Make directory read-only to simulate error
            old_env = os.environ.get("JTA_EVIDENCE_STORE_ROOT")
            os.environ["JTA_EVIDENCE_STORE_ROOT"] = tmpdir
            try:
                # Remove write permission
                os.chmod(tmpdir, 0o555)

                target = WebMonitorTarget(
                    name="Fallback Test",
                    source_type="news_only_context",
                    base_url="https://example.com",
                    allowed_domains=["example.com"],
                    start_urls=["https://example.com/"],
                    extractor_type="rss_or_news_listing",
                    source_tier="news_only_context",
                )
                runner = CrawleeRunner(target, db)

                content = b"<html>Fallback content</html>"

                # Should not raise, should fallback to DB
                snapshot = runner._create_snapshot(
                    source_url="https://example.com/fallback",
                    http_status=200,
                    content_type="text/html",
                    content=content,
                    title="Fallback",
                )

                # Falls back to DB
                assert snapshot.storage_backend == "db"
                assert snapshot.storage_path is None
                assert snapshot.raw_content is not None

                # Error should be recorded
                assert len(runner.errors) > 0
                assert any("External storage failed" in e for e in runner.errors)

            finally:
                # Restore permissions
                os.chmod(tmpdir, 0o755)
                if old_env:
                    os.environ["JTA_EVIDENCE_STORE_ROOT"] = old_env
                else:
                    os.environ.pop("JTA_EVIDENCE_STORE_ROOT", None)

    def test_content_hash_consistency(self, db):
        """Content hash should be consistent regardless of storage backend."""
        content = b"<html>Consistent hash test</html>"
        expected_hash = hashlib.sha256(content).hexdigest()

        # Test with external storage
        with tempfile.TemporaryDirectory() as tmpdir:
            old_env = os.environ.get("JTA_EVIDENCE_STORE_ROOT")
            os.environ["JTA_EVIDENCE_STORE_ROOT"] = tmpdir
            try:
                target = WebMonitorTarget(
                    name="External Hash",
                    source_type="news_only_context",
                    base_url="https://example.com",
                    allowed_domains=["example.com"],
                    start_urls=["https://example.com/"],
                    extractor_type="rss_or_news_listing",
                    source_tier="news_only_context",
                )
                runner = CrawleeRunner(target, db)

                snapshot_ext = runner._create_snapshot(
                    source_url="https://example.com/ext",
                    http_status=200,
                    content_type="text/html",
                    content=content,
                )

                assert snapshot_ext.content_hash == expected_hash

            finally:
                if old_env:
                    os.environ["JTA_EVIDENCE_STORE_ROOT"] = old_env
                else:
                    os.environ.pop("JTA_EVIDENCE_STORE_ROOT", None)

        # Test with DB storage
        old_env = os.environ.pop("JTA_EVIDENCE_STORE_ROOT", None)
        try:
            target = WebMonitorTarget(
                name="DB Hash",
                source_type="news_only_context",
                base_url="https://example.com",
                allowed_domains=["example.com"],
                start_urls=["https://example.com/"],
                extractor_type="rss_or_news_listing",
                source_tier="news_only_context",
            )
            runner = CrawleeRunner(target, db)

            snapshot_db = runner._create_snapshot(
                source_url="https://example.com/db",
                http_status=200,
                content_type="text/html",
                content=content,
            )

            assert snapshot_db.content_hash == expected_hash

        finally:
            if old_env:
                os.environ["JTA_EVIDENCE_STORE_ROOT"] = old_env

    def test_path_format_correct(self, db):
        """External storage path should follow correct format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_env = os.environ.get("JTA_EVIDENCE_STORE_ROOT")
            os.environ["JTA_EVIDENCE_STORE_ROOT"] = tmpdir
            try:
                target = WebMonitorTarget(
                    name="Path Test",
                    source_type="news_only_context",
                    base_url="https://example.com",
                    allowed_domains=["example.com"],
                    start_urls=["https://example.com/"],
                    extractor_type="rss_or_news_listing",
                    source_tier="news_only_context",
                )
                runner = CrawleeRunner(target, db)

                content = b"<html>Path format test</html>"
                content_hash = hashlib.sha256(content).hexdigest()

                snapshot = runner._create_snapshot(
                    source_url="https://example.com/path",
                    http_status=200,
                    content_type="text/html",
                    content=content,
                )

                # Path format: snapshots/sha256/aa/bb/<hash>.bin
                path = snapshot.storage_path
                assert path.startswith("snapshots/sha256/")

                parts = path.split("/")
                assert len(parts) == 5
                assert parts[2] == content_hash[:2]
                assert parts[3] == content_hash[2:4]
                assert parts[4] == f"{content_hash}.bin"

            finally:
                if old_env:
                    os.environ["JTA_EVIDENCE_STORE_ROOT"] = old_env
                else:
                    os.environ.pop("JTA_EVIDENCE_STORE_ROOT", None)


@pytest.fixture
def db():
    """Database session fixture."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()

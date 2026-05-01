"""Regression tests for admin ingestion and source endpoints.

Verifies that admin endpoints return correct field names matching ORM models.
Prevents drift like source vs source_name, completed_at vs finished_at, etc.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.main import app
from app.models.entities import IngestionRun, ReviewItem, SourceRegistry, SourceSnapshot

client = TestClient(app)


def get_admin_headers():
    """Get admin auth headers for testing."""
    # For testing, we can use a test override or mock token
    # This is a simplified version - in real tests you'd mock the auth
    return {"Authorization": "Bearer test-admin-token"}


class TestAdminIngestionEndpoints:
    """Regression tests for admin ingestion control plane."""

    def test_list_runs_empty(self) -> None:
        """GET /api/admin/ingestion-runs returns empty list when no runs."""
        with SessionLocal() as db:
            # Clear any existing runs for clean test
            db.query(IngestionRun).delete()
            db.commit()

        response = client.get("/api/admin/ingestion-runs", headers=get_admin_headers())
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_runs_with_data(self) -> None:
        """GET /api/admin/ingestion-runs returns runs with correct field names."""
        with SessionLocal() as db:
            # Create test run
            run = IngestionRun(
                source_name="test_source",
                started_at=datetime.now(timezone.utc),
                status="completed",
                fetched_count=100,
                parsed_count=95,
                persisted_count=90,
                skipped_count=5,
                error_count=0,
            )
            db.add(run)
            db.commit()
            run_id = run.id

        response = client.get("/api/admin/ingestion-runs", headers=get_admin_headers())
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

        # Verify field names match ORM model (NOT drifted names)
        first_run = data[0]
        assert "source_name" in first_run  # NOT "source"
        assert "finished_at" in first_run  # NOT "completed_at"
        assert "skipped_count" in first_run  # NOT "rejected_count"
        assert "error_count" in first_run
        assert "fetched_count" in first_run
        assert "parsed_count" in first_run
        assert "persisted_count" in first_run  # NOT "items_inserted"

        # Cleanup
        with SessionLocal() as db:
            db.query(IngestionRun).filter(IngestionRun.id == run_id).delete()
            db.commit()

    def test_list_runs_filter_by_source(self) -> None:
        """Filter by source_name works."""
        with SessionLocal() as db:
            run = IngestionRun(
                source_name="specific_source",
                started_at=datetime.now(timezone.utc),
                status="running",
            )
            db.add(run)
            db.commit()
            run_id = run.id

        response = client.get(
            "/api/admin/ingestion-runs?source=specific_source",
            headers=get_admin_headers(),
        )
        assert response.status_code == 200
        data = response.json()
        assert all(r["source_name"] == "specific_source" for r in data)

        # Cleanup
        with SessionLocal() as db:
            db.query(IngestionRun).filter(IngestionRun.id == run_id).delete()
            db.commit()

    def test_list_runs_filter_by_status(self) -> None:
        """Filter by status works."""
        with SessionLocal() as db:
            run = IngestionRun(
                source_name="test",
                started_at=datetime.now(timezone.utc),
                status="failed",
            )
            db.add(run)
            db.commit()
            run_id = run.id

        response = client.get(
            "/api/admin/ingestion-runs?status=failed",
            headers=get_admin_headers(),
        )
        assert response.status_code == 200
        data = response.json()
        assert all(r["status"] == "failed" for r in data)

        # Cleanup
        with SessionLocal() as db:
            db.query(IngestionRun).filter(IngestionRun.id == run_id).delete()
            db.commit()

    def test_get_run_detail(self) -> None:
        """GET /{run_id} returns correct IngestionRunDetail with all fields."""
        with SessionLocal() as db:
            run = IngestionRun(
                source_name="detail_test",
                started_at=datetime.now(timezone.utc),
                finished_at=datetime.now(timezone.utc),
                status="completed",
                fetched_count=100,
                parsed_count=95,
                persisted_count=90,
                skipped_count=5,
                error_count=0,
                errors=[],
            )
            db.add(run)
            db.commit()
            run_id = run.id

        response = client.get(
            f"/api/admin/ingestion-runs/{run_id}",
            headers=get_admin_headers(),
        )
        assert response.status_code == 200
        data = response.json()

        # Verify all expected fields present with correct names
        assert "source_name" in data
        assert "finished_at" in data
        assert "skipped_count" in data
        assert "errors" in data  # NOT "error_log"
        assert "fetched_count" in data
        assert "parsed_count" in data
        assert "persisted_count" in data
        assert "error_count" in data

        # Verify no drifted fields
        assert "source" not in data  # Old drifted name
        assert "completed_at" not in data  # Old drifted name
        assert "error_log" not in data  # Old drifted name
        assert "config_snapshot" not in data  # Non-existent field

        # Cleanup
        with SessionLocal() as db:
            db.query(IngestionRun).filter(IngestionRun.id == run_id).delete()
            db.commit()

    def test_get_run_detail_404(self) -> None:
        """GET /{run_id} returns 404 for nonexistent run."""
        response = client.get(
            "/api/admin/ingestion-runs/999999",
            headers=get_admin_headers(),
        )
        assert response.status_code == 404

    def test_get_run_review_items(self) -> None:
        """GET /{run_id}/review-items returns linked items via ingestion_run_id."""
        with SessionLocal() as db:
            run = IngestionRun(
                source_name="review_test",
                started_at=datetime.now(timezone.utc),
                status="completed",
            )
            db.add(run)
            db.flush()

            item = ReviewItem(
                record_type="test",
                source_quality="test",
                privacy_status="private",
                publish_recommendation="pending",
                status="pending",
                suggested_payload_json={},
                ingestion_run_id=run.id,
            )
            db.add(item)
            db.commit()
            run_id = run.id

        response = client.get(
            f"/api/admin/ingestion-runs/{run_id}/review-items",
            headers=get_admin_headers(),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == run_id
        assert data["source_name"] == "review_test"
        assert data["total_items"] >= 1

        # Cleanup
        with SessionLocal() as db:
            db.query(ReviewItem).filter(ReviewItem.ingestion_run_id == run_id).delete()
            db.query(IngestionRun).filter(IngestionRun.id == run_id).delete()
            db.commit()

    def test_get_run_snapshots(self) -> None:
        """GET /{run_id}/snapshots returns linked snapshots via ingestion_run_id."""
        with SessionLocal() as db:
            run = IngestionRun(
                source_name="snapshot_test",
                started_at=datetime.now(timezone.utc),
                status="completed",
            )
            db.add(run)
            db.flush()

            snapshot = SourceSnapshot(
                source_url="http://test.com",
                fetched_at=datetime.now(timezone.utc),
                content_hash="abc123",
                storage_backend="db",
                ingestion_run_id=run.id,
            )
            db.add(snapshot)
            db.commit()
            run_id = run.id

        response = client.get(
            f"/api/admin/ingestion-runs/{run_id}/snapshots",
            headers=get_admin_headers(),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == run_id
        assert data["source_name"] == "snapshot_test"
        assert data["total_snapshots"] >= 1

        # Cleanup
        with SessionLocal() as db:
            db.query(SourceSnapshot).filter(
                SourceSnapshot.ingestion_run_id == run_id
            ).delete()
            db.query(IngestionRun).filter(IngestionRun.id == run_id).delete()
            db.commit()

    def test_retry_run_not_found(self) -> None:
        """POST /{run_id}/retry returns 404 for nonexistent."""
        response = client.post(
            "/api/admin/ingestion-runs/999999/retry",
            headers=get_admin_headers(),
        )
        assert response.status_code == 404


class TestAdminSourceEndpoints:
    """Regression tests for admin source control plane."""

    def test_list_sources(self) -> None:
        """GET /api/admin/sources returns sources with correct fields."""
        response = client.get("/api/admin/sources", headers=get_admin_headers())
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        if data:
            # Verify SourceResponse fields
            source = data[0]
            assert "source_key" in source
            assert "source_name" in source
            assert "source_type" in source
            assert "is_active" in source

    def test_list_sources_filter_active(self) -> None:
        """Filter by is_active works."""
        response = client.get(
            "/api/admin/sources?is_active=true",
            headers=get_admin_headers(),
        )
        assert response.status_code == 200
        data = response.json()
        assert all(s.get("is_active") is True for s in data)

    def test_get_source_detail(self) -> None:
        """GET /{source_key} returns SourceResponse."""
        # First create a source
        with SessionLocal() as db:
            source = SourceRegistry(
                source_key="test_detail_source",
                source_name="Test Detail Source",
                source_type="test",
            )
            db.add(source)
            db.commit()

        response = client.get(
            "/api/admin/sources/test_detail_source",
            headers=get_admin_headers(),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["source_key"] == "test_detail_source"
        assert "source_name" in data
        assert "source_tier" in data

        # Cleanup
        with SessionLocal() as db:
            db.query(SourceRegistry).filter(
                SourceRegistry.source_key == "test_detail_source"
            ).delete()
            db.commit()

    def test_get_source_404(self) -> None:
        """GET /{source_key} returns 404 for nonexistent."""
        response = client.get(
            "/api/admin/sources/nonexistent_source_12345",
            headers=get_admin_headers(),
        )
        assert response.status_code == 404

    def test_get_source_health(self) -> None:
        """GET /{source_key}/health returns health metrics."""
        with SessionLocal() as db:
            source = SourceRegistry(
                source_key="health_test_source",
                source_name="Health Test",
                source_type="test",
            )
            db.add(source)
            db.commit()

            # Add a run for this source
            run = IngestionRun(
                source_name="health_test_source",
                started_at=datetime.now(timezone.utc),
                status="completed",
                error_count=0,
            )
            db.add(run)
            db.commit()

        response = client.get(
            "/api/admin/sources/health_test_source/health",
            headers=get_admin_headers(),
        )
        assert response.status_code == 200
        data = response.json()
        assert "health_score" in data
        assert "recent_run_count" in data
        assert "recent_error_count" in data

        # Cleanup
        with SessionLocal() as db:
            db.query(IngestionRun).filter(
                IngestionRun.source_name == "health_test_source"
            ).delete()
            db.query(SourceRegistry).filter(
                SourceRegistry.source_key == "health_test_source"
            ).delete()
            db.commit()

    def test_get_source_runs(self) -> None:
        """GET /{source_key}/runs returns linked runs with correct field names."""
        with SessionLocal() as db:
            source = SourceRegistry(
                source_key="runs_test_source",
                source_name="Runs Test",
                source_type="test",
            )
            db.add(source)
            db.commit()

            run = IngestionRun(
                source_name="runs_test_source",
                started_at=datetime.now(timezone.utc),
                status="completed",
            )
            db.add(run)
            db.commit()

        response = client.get(
            "/api/admin/sources/runs_test_source/runs",
            headers=get_admin_headers(),
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        if data:
            # Verify field names match ORM
            run_data = data[0]
            assert "finished_at" in run_data  # NOT completed_at
            assert "source_name" not in run_data  # In this context, source_key is implied

        # Cleanup
        with SessionLocal() as db:
            db.query(IngestionRun).filter(
                IngestionRun.source_name == "runs_test_source"
            ).delete()
            db.query(SourceRegistry).filter(
                SourceRegistry.source_key == "runs_test_source"
            ).delete()
            db.commit()


class TestResponseFieldValidation:
    """Prevent field drift between ORM and Pydantic response models."""

    def test_ingestion_run_summary_fields_match_orm(self) -> None:
        """Verify IngestionRunSummary fields exist on ORM model."""
        from app.api.routes.admin_ingestion import IngestionRunSummary
        from app.models.entities import IngestionRun as IngestionRunORM

        # Get Pydantic fields
        pydantic_fields = set(IngestionRunSummary.model_fields.keys())

        # Get ORM columns
        orm_columns = {c.name for c in IngestionRunORM.__table__.columns}

        # Computed fields are OK
        computed = {"duration_seconds"}
        required_fields = pydantic_fields - computed

        # All required fields must exist in ORM
        for field in required_fields:
            assert field in orm_columns, f"Field '{field}' in response but not in ORM"

        # Specifically check drifted field names are NOT used
        assert "source" not in pydantic_fields, "Use 'source_name' not 'source'"
        assert "completed_at" not in pydantic_fields, "Use 'finished_at' not 'completed_at'"
        assert "rejected_count" not in pydantic_fields, "Use 'skipped_count' not 'rejected_count'"

    def test_ingestion_run_detail_fields_match_orm(self) -> None:
        """Verify IngestionRunDetail fields exist on ORM model."""
        from app.api.routes.admin_ingestion import IngestionRunDetail
        from app.models.entities import IngestionRun as IngestionRunORM

        pydantic_fields = set(IngestionRunDetail.model_fields.keys())
        orm_columns = {c.name for c in IngestionRunORM.__table__.columns}

        computed = {"duration_seconds", "success_rate"}
        required_fields = pydantic_fields - computed

        for field in required_fields:
            assert field in orm_columns, f"Field '{field}' in response but not in ORM"

        # Check for drifted names
        assert "source" not in pydantic_fields
        assert "completed_at" not in pydantic_fields
        assert "error_log" not in pydantic_fields, "Use 'errors' not 'error_log'"
        assert "config_snapshot" not in pydantic_fields, "Field doesn't exist in ORM"

"""Statistics Canada crime data adapter.

Fetches Table 35-10-0177-01 (Incident-based crime statistics) from the
Statistics Canada public CSV download endpoint and maps aggregate rows to
CrimeIncidentRecord objects.

This source is TIER_AUTO (aggregate, no person names, no exact addresses).
Enable with JTA_STATSCAN_ENABLED=true.

Attribution: Statistics Canada. Table 35-10-0177-01.
https://www150.statcan.gc.ca/t1/tbl1/en/dtbl/35100177
"""
from __future__ import annotations

import csv
import hashlib
import io
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx

from app.ingestion.crime_sources.base import CrimeIncidentRecord
from app.ingestion.crime_sources.persistence import (
    CrimeIncidentValidationError,
    normalize_incident_category,
    normalize_precision_level,
    persist_crime_incident,
)

log = logging.getLogger(__name__)

SOURCE_NAME = "statistics_canada"

_DEFAULT_URL = (
    "https://www150.statcan.gc.ca/t1/tbl1/en/dtbl/35100177/35100177.zip"
)

_PROVINCE_CENTROIDS: dict[str, tuple[float, float]] = {
    "Alberta": (53.9333, -116.5765),
    "British Columbia": (53.7267, -127.6476),
    "Manitoba": (56.4150, -98.7390),
    "New Brunswick": (46.5653, -66.4619),
    "Newfoundland and Labrador": (53.1355, -57.6604),
    "Northwest Territories": (64.8255, -124.8457),
    "Nova Scotia": (44.6820, -63.7443),
    "Nunavut": (70.2998, -83.1076),
    "Ontario": (51.2538, -85.3232),
    "Prince Edward Island": (46.5107, -63.4168),
    "Quebec": (52.9399, -73.5491),
    "Saskatchewan": (52.9399, -106.4509),
    "Yukon": (64.2823, -135.0000),
    "Canada": (56.1304, -106.3468),
}


@dataclass
class StatCanImportResult:
    read_count: int = 0
    persisted_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    errors: list[str] = field(default_factory=list)


def import_statscan_csv(
    db,
    file_like: io.StringIO | io.TextIOBase,
) -> StatCanImportResult:
    """Import a Statistics Canada CSV stream into CrimeIncident rows.

    Expects the standard 35-10-0177-01 column layout.
    Auto-publish tier: aggregate rows are published immediately.
    """
    result = StatCanImportResult()
    reader = csv.DictReader(file_like)
    now = datetime.now(timezone.utc)

    for row_num, row in enumerate(reader, start=2):
        result.read_count += 1
        try:
            geography = (row.get("GEO") or "").strip()
            violation = (row.get("Violations") or row.get("violation") or "").strip()
            value_str = (row.get("VALUE") or row.get("value") or "0").strip()

            if not geography or not violation:
                result.skipped_count += 1
                continue

            coords = _province_coords(geography)
            if coords is None:
                result.skipped_count += 1
                continue

            lat, lng = coords
            ext_id = "SC-" + hashlib.sha256(
                f"{geography}|{violation}".encode()
            ).hexdigest()[:16].upper()
            record = CrimeIncidentRecord(
                source_id=SOURCE_NAME,
                external_id=ext_id,
                incident_type=violation,
                incident_category=normalize_incident_category(_category_from_violation(violation)),
                reported_at=now,
                occurred_at=None,
                city=None,
                province_state=geography,
                country="Canada",
                public_area_label=geography,
                latitude_public=lat,
                longitude_public=lng,
                precision_level=normalize_precision_level("province_centroid"),
                source_url="https://www150.statcan.gc.ca/t1/tbl1/en/dtbl/35100177",
                source_name=SOURCE_NAME,
                verification_status="aggregate_official",
                data_last_seen_at=now,
                is_public=False,
                is_aggregate=True,
                notes=f"Aggregate count: {value_str}. Statistics Canada Table 35-10-0177-01.",
            )
            persist_crime_incident(db, record)
            result.persisted_count += 1
        except CrimeIncidentValidationError as exc:
            result.skipped_count += 1
            result.errors.append(f"row {row_num}: skipped:{exc}")
        except Exception as exc:  # noqa: BLE001
            result.error_count += 1
            result.errors.append(f"row {row_num}: error:{exc}")

    db.commit()
    return result


def fetch_statscan_csv(client: httpx.Client | None = None) -> str | None:
    """Fetch the Statistics Canada CSV. Returns raw CSV text or None on error.

    Note: The official download is a ZIP. In production, extract the CSV
    from the ZIP before passing to import_statscan_csv.
    This function returns the raw response body for flexibility.
    """
    owns = client is None
    if owns:
        client = httpx.Client(timeout=30)
    try:
        resp = client.get(_DEFAULT_URL)
        resp.raise_for_status()
        return resp.text
    except Exception as exc:  # noqa: BLE001
        log.warning("StatsCan fetch error: %s", exc)
        return None
    finally:
        if owns:
            client.close()


def _province_coords(geography: str) -> tuple[float, float] | None:
    return _PROVINCE_CENTROIDS.get(geography)


def _category_from_violation(violation: str) -> str:
    v = violation.lower()
    if any(k in v for k in ("assault", "homicide", "robbery", "sexual")):
        return "violent"
    if any(k in v for k in ("theft", "fraud", "break", "mischief", "property")):
        return "property"
    return "other"

"""Saskatoon Police Service crime-map adapter.

Imports CSV exports from the Saskatoon Police crime map
(https://www.saskatoonpolice.ca/crime-map) using generalized
public-area coordinates only.

Source tier: TIER_AUTO for structured fields.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.ingestion.crime_sources.base import CrimeIncidentRecord
from app.ingestion.crime_sources.persistence import (
    CrimeIncidentValidationError,
    normalize_incident_category,
    normalize_precision_level,
    persist_crime_incident,
)

SOURCE_NAME = "saskatoon_police"

_CITY_CENTROID = (52.1332, -106.6700)


@dataclass
class SaskatoonImportResult:
    read_count: int = 0
    persisted_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    errors: list[str] = field(default_factory=list)


def import_saskatoon_csv(
    db,
    file_like: io.StringIO | io.TextIOBase,
) -> SaskatoonImportResult:
    """Import Saskatoon Police CSV rows into CrimeIncident records.

    Expected columns: ``IncidentType``, ``ReportedDate``, ``Neighbourhood``.
    Coordinates are always snapped to the city centroid (precision=city_centroid).
    """
    result = SaskatoonImportResult()
    reader = csv.DictReader(file_like)
    now = datetime.now(timezone.utc)

    for row_num, row in enumerate(reader, start=2):
        result.read_count += 1
        try:
            incident_type = (row.get("IncidentType") or row.get("incident_type") or "").strip()
            neighbourhood = (row.get("Neighbourhood") or row.get("neighbourhood") or "Saskatoon").strip()
            date_str = (row.get("ReportedDate") or row.get("reported_date") or "").strip()

            if not incident_type:
                result.skipped_count += 1
                continue

            record = CrimeIncidentRecord(
                source_id=SOURCE_NAME,
                external_id=None,
                incident_type=incident_type,
                incident_category=normalize_incident_category(
                    _category(incident_type)
                ),
                reported_at=_parse_dt(date_str) or now,
                occurred_at=None,
                city="Saskatoon",
                province_state="SK",
                country="Canada",
                public_area_label=neighbourhood,
                latitude_public=_CITY_CENTROID[0],
                longitude_public=_CITY_CENTROID[1],
                precision_level=normalize_precision_level("city_centroid"),
                source_url="https://www.saskatoonpolice.ca/crime-map",
                source_name=SOURCE_NAME,
                verification_status="reported",
                data_last_seen_at=now,
                is_public=False,
                is_aggregate=False,
                notes=None,
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


def _parse_dt(value: str) -> datetime | None:
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _category(incident_type: str) -> str:
    t = incident_type.lower()
    if any(k in t for k in ("assault", "robbery", "threat", "homicide", "weapon")):
        return "violent"
    if any(k in t for k in ("theft", "break", "mischief", "fraud")):
        return "property"
    return "other"

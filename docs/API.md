# JudgeTracker Atlas API

Base URL: `http://localhost:8000`

## Health

`GET /health`

Returns:

```json
{ "status": "OK" }
```

## Map Events

`GET /api/map/events`

Returns a GeoJSON `FeatureCollection`.

Filters:

- `start`
- `end`
- `court_id`
- `judge_id`
- `event_type`
- `repeat_offender`
- `verified_only`
- `source_type`
- `limit` default `500`, max `2000`
- `offset` default `0`

## Crime Incident Map

`GET /api/map/crime-incidents`

Returns a GeoJSON `FeatureCollection` for the separate recent reported crime incidents layer. Public output uses generalized public-area coordinates only and does not include suspect names, victim details, private addresses, DOBs, family details, or person profiles.

Filters:

- `start`
- `end`
- `city`
- `province_state`
- `country`
- `incident_category`
- `verification_status`
- `source_name`
- `last_hours`
- `limit` default `500`, max `2000`
- `offset` default `0`

Every feature includes the disclaimer:

```text
Reported incident; not proof of guilt or conviction.
```

## Events

- `GET /api/events`
- `GET /api/events/{event_id}`
- `POST /api/events`

Public event endpoints exclude records whose review status is `pending_review`, `rejected`, or `removed_from_public`.

Public event responses expose repeat-offender matches as indicator-only fields:

- `repeat_offender_indicator_flag`
- `repeat_offender_indicators`
- `verification_status`
- `source_excerpt`
- `is_mappable`
- `location_status`

Defendant public names are not included in public event responses.
Repeat-offender keyword matches are indicators only. They are not legal conclusions and do not establish a verified repeat-offender finding.

Missing outcomes return:

```text
Outcome unknown — no public post-decision record located.
```

## Judges

- `GET /api/judges`
- `GET /api/judges/{judge_id}`
- `GET /api/judges/{judge_id}/events`

## Cases

- `GET /api/cases/{case_id}`
- `GET /api/cases/{case_id}/timeline`

## Defendants

- `GET /api/defendants/{defendant_id}`
- `GET /api/defendants/{defendant_id}/timeline`

Defendant responses default to anonymized labels and include no personal location fields.

## Sources

- `GET /api/sources`
- `GET /api/sources/{source_id}`

Public source endpoints exclude records whose review status is `pending_review`, `rejected`, or `removed_from_public`.

## Source Panels

`GET /api/evidence/source-panel/{entity_type}/{entity_id}`

Supported `entity_type` values:

- `event`
- `crime_incident`
- `source`

Returns reviewed public evidence metadata:

- source name and type
- source URL
- retrieved date
- published date when available
- quoted excerpt when safe and available
- verification status
- trust reason
- reviewer and reviewed date
- current review status

Source panel responses must not expose defendant public names, suspect/victim details, private addresses, DOBs, family details, medical details, or private residences.

## Ingestion

`POST /api/ingest/courtlistener?since=2026-01-01T00:00:00Z`

Runs the CourtListener adapter for a date window start. The prototype records ingestion run metadata, persists classified docket events, and isolates per-record parsing failures.

Response counters include:

- `fetched_count`
- `parsed_count`
- `persisted_count`
- `skipped_count`
- `error_count`

## Admin Imports

`POST /api/admin/import/crime-incidents/manual-csv`

Disabled by default with `JTA_ENABLE_ADMIN_IMPORTS=false`. When disabled, the endpoint returns `403`.

When explicitly enabled in a trusted local/admin environment, upload a CSV file field named `file`. This is a controlled manual/import path for official police/open-data records. It does not create links to judges, defendants, cases, or court events.

## Admin Review

`GET /api/admin/review-queue`

Filters:

- `entity_type`
- `review_status`
- `source_type`
- `limit` default `100`, max `500`
- `offset` default `0`

`POST /api/admin/review-queue/{entity_type}/{entity_id}/decision`

Disabled by default with `JTA_ENABLE_ADMIN_REVIEW=false`. Requests require `X-JTA-Admin-Token` to match `JTA_ADMIN_REVIEW_TOKEN`; otherwise the API returns `403`.

Decision payload examples:

```json
{ "decision": "approve", "reviewed_by": "reviewer@example", "notes": "Court order reviewed." }
```

```json
{ "decision": "dispute", "reviewed_by": "reviewer@example", "notes": "Awaiting corrected docket entry." }
```

Supported review statuses:

- `pending_review`
- `verified_court_record`
- `official_police_open_data_report`
- `news_only_context`
- `disputed`
- `corrected`
- `rejected`
- `removed_from_public`

`rejected` and `removed_from_public` hide the record from public map/list endpoints and create an `evidence_reviews` audit row.

## AI-Assisted Review Items

`GET /api/admin/review/items`

`GET /api/admin/review/items/{id}`

`POST /api/admin/review/items/{id}/approve`

`POST /api/admin/review/items/{id}/reject`

`POST /api/admin/review/items/{id}/needs-more-sources`

`POST /api/admin/review/items/{id}/block`

`POST /api/admin/review/items/{id}/publish`

`POST /api/admin/ai/process-source/{source_id}`

These endpoints are disabled by default through `JTA_ENABLE_ADMIN_IMPORTS=false`. AI review items are draft evidence-clerk outputs only. Publishing a safe approved legal-event draft creates a hidden `pending_review` event; it does not automatically publish high-risk legal claims.

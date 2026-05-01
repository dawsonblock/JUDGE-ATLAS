# Judge Atlas

**A map-first platform for tracking court events with verified sources.**

[![License](https://img.shields.io/badge/license-MIT-blue)]()
[![Status](https://img.shields.io/badge/status-research%20alpha-orange)]()

[Live Demo](#) • [Documentation](./docs) • [Report Issue](../../issues)

---

## What is Judge Atlas?

Judge Atlas is a transparency tool that maps federal court events—sentencing, detention orders, release decisions, and appeal outcomes—connecting them to judges, cases, and **verified public sources**.

### Key Features

- **Interactive Map** — Explore court events geographically with filterable markers
- **Verified Sources** — Every record links to official court documents or police open data
- **Privacy Protection** — Automatic redaction of personal information; anonymized defendant identities
- **Review Workflow** — Human review of all records before public display
- **Open Data** — GeoJSON API for researchers and journalists

### What Makes It Different?

| Feature | Judge Atlas | Typical Court Databases |
|---------|-------------|------------------------|
| Source linking | ✅ Required for every record | ❌ Often missing |
| Privacy-safe | ✅ Automatic redaction | ❌ Raw data dumps |
| Map visualization | ✅ Built-in interactive map | ❌ Text-only lists |
| Judge tracking | ✅ Judge-event connections | ❌ Rarely available |
| Free & open source | ✅ MIT License | ❌ Usually proprietary |

**⚠️ Important:** Judge Atlas is a **research alpha / hardened prototype**, not production legal infrastructure. See [Known Gaps](#known-gaps) for limitations and [Verification Status](#verification-status) for current test results.

---

## Screenshots

> _Screenshot placeholder: Map view with court event markers and detail panel_

> _Screenshot placeholder: Admin review queue showing pending records_

> _Screenshot placeholder: Source evidence panel with linked documents_

---

## Technology Stack

Judge Atlas is built with modern, open-source technologies:

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Backend** | Python 3.11, FastAPI | API server with automatic OpenAPI docs |
| **Database** | PostgreSQL + PostGIS | Geographic data storage |
| **Frontend** | Next.js 14, React, Leaflet | Interactive map and dashboard |
| **Data Sources** | CourtListener API, manual CSV | Court records and police open data |
| **Testing** | pytest | Run verify scripts for current status |

---

## Data Sources

Records in Judge Atlas come from verified sources only:

1. **Court Records** — Federal court dockets via [CourtListener](https://www.courtlistener.com/) (RECAP/PACER)
2. **Police Open Data** — Official crime statistics from participating departments
3. **Government Statistics** — Verified aggregate reports
4. **News Context** — Secondary context only (never primary source)

All records must pass a **publication gate** before appearing on the map:
- ✅ Valid source URL required
- ✅ Reviewed and approved by admin
- ✅ No personal addresses or identifying details
- ✅ Privacy-safe location precision (city/neighborhood level)

---

## Repository Layout

```text
.
├── backend/
│   ├── alembic/                    Alembic migrations
│   │   └── versions/
│   │       └── 20250427_1720_initial_schema.py
│   ├── app/
│   │   ├── ai/                     Deterministic evidence-clerk pipeline
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── admin_review.py  Review queue + audit history
│   │   │       ├── ai_review.py     AI review item actions
│   │   │       ├── ingestion.py     Admin import trigger endpoints
│   │   │       ├── map.py           GeoJSON map endpoints
│   │   │       └── public_events.py Public event/case/judge API
│   │   ├── auth/                   Token auth + feature flag guards
│   │   ├── core/                   Settings (pydantic-settings)
│   │   ├── db/                     SQLAlchemy engine, session, PostGIS init
│   │   ├── ingestion/
│   │   │   ├── adapters.py         ParsedRecord / RawRecord schema
│   │   │   ├── courtlistener.py    CourtListener v4 adapter
│   │   │   ├── persistence.py      Court-event upsert logic
│   │   │   ├── runner.py           Ingestion run orchestration + lock
│   │   │   └── crime_sources/      CSV import, validation, persistence
│   │   ├── models/entities.py      SQLAlchemy ORM models
│   │   ├── schemas/                Pydantic request/response schemas
│   │   ├── seed/                   Sample data seeded on startup
│   │   ├── serializers/public.py   Privacy-safe serialization + disclaimers
│   │   ├── services/               Outcome, text, constants helpers
│   │   ├── tests/                  pytest test suite
│   │   └── workers/                Background task stubs
│   ├── Dockerfile.backend
│   └── pyproject.toml
├── frontend/
│   ├── app/
│   │   ├── admin/review/page.tsx   Admin review queue + history UI
│   │   ├── map/page.tsx            Full-screen map page
│   │   └── page.tsx                Dashboard home
│   ├── components/
│   │   ├── AtlasDashboard.tsx      Main map + filter + detail panel
│   │   ├── JudgeNorthAmericaMap.tsx Leaflet map wrapper
│   │   └── SourcePanel.tsx         Expandable source evidence panel
│   ├── lib/api.ts                  API types + fetch helpers
│   ├── Dockerfile
│   └── package.json
├── docs/
│   ├── AI_PIPELINE.md
│   ├── API.md
│   ├── schema_audit.md
│   ├── SOURCES.md
│   └── frontend_verification.md
├── scripts/
│   ├── verify_backend.sh           Syntax + pytest + artifact log
│   ├── verify_frontend.sh          npm lint + typecheck + build
│   ├── verify_docker.sh            Docker Compose smoke test
│   └── verify_local.sh             Local dev smoke test
├── artifacts/proof/backend/        Timestamped verification logs
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Quick Start

### Option 1: Docker Compose (Recommended for First Run)

```bash
cd JUDGE-main
cp .env.example .env
docker compose up --build
```

### Option 2: Direct Local Development

**Prerequisites:**
- Python 3.12+
- Node.js 20
- PostgreSQL 16 with PostGIS extension

**Backend (Terminal 1):**
```bash
cd JUDGE-main/backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[test]"
# Ensure PostgreSQL is running with judgetracker database
createdb judgetracker  # If database doesn't exist
python -m alembic upgrade head  # Run migrations
uvicorn app.main:app --reload --port 8000
```

**Frontend (Terminal 2):**
```bash
cd JUDGE-main/frontend
npm install
npm run dev
```

### Verify Local Setup

| URL | What |
|---|---|
| <http://localhost:3000> | Frontend dashboard |
| <http://localhost:3000/map> | Interactive map |
| <http://localhost:8000/health> | Backend health check |
| <http://localhost:8000/docs> | Interactive API docs (Swagger UI) |
| <http://localhost:8000/api/map/events> | GeoJSON court events |
| <http://localhost:8000/api/map/crime-incidents> | GeoJSON crime incidents |

```bash
# Quick verification commands
curl http://localhost:8000/health
curl http://localhost:8000/api/map/events
curl http://localhost:8000/api/map/crime-incidents
```

Sample data is seeded automatically on backend startup (when `JTA_AUTO_SEED=true`). No CourtListener token is needed for local development.

---

## Environment Variables

All variables are in `.env.example`. Key ones:

| Variable | Default | Purpose |
|---|---|---|
| `JTA_DATABASE_URL` | (required) | PostgreSQL connection string |
| `JTA_CORS_ORIGINS` | `http://localhost:3000` | Allowed CORS origins |
| `JTA_ENABLE_ADMIN_REVIEW` | `false` | Enable the review queue API |
| `JTA_ADMIN_REVIEW_TOKEN` | (empty) | Token required for `X-JTA-Admin-Token` header |
| `JTA_ENABLE_ADMIN_IMPORTS` | `false` | Enable ingestion trigger endpoints |
| `JTA_ADMIN_TOKEN` | (empty) | Token for import endpoints |
| `COURTLISTENER_API_TOKEN` | (empty) | CourtListener v4 API token |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | Frontend → backend (browser) |
| `BACKEND_INTERNAL_URL` | `http://backend:8000` | Frontend → backend (server-side, Docker) |

Both `JTA_ENABLE_ADMIN_REVIEW` and `JTA_ENABLE_ADMIN_IMPORTS` are **false by default**. The system is fail-closed: if they are off, all admin endpoints return 403.

---

## API Endpoints

### Public

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `GET` | `/api/events` | Paginated list of public-visible events |
| `GET` | `/api/events/{event_id}` | Single event detail |
| `GET` | `/api/cases` | Public cases |
| `GET` | `/api/judges` | Public judges |
| `GET` | `/api/map/events` | GeoJSON FeatureCollection of mapped events |
| `GET` | `/api/map/crime-incidents` | GeoJSON FeatureCollection of crime incidents |
| `GET` | `/api/evidence/source-panel/{entity_type}/{entity_id}` | Source evidence panel for an entity |

Map endpoints support `?bbox=west,south,east,north` (WGS84 decimal degrees) for spatial filtering **using latitude/longitude column comparisons only** (PostGIS geometry is not used for bbox filtering). Returns a response envelope:

```json
{
  "type": "FeatureCollection",
  "features": [...],
  "returned_count": 12,
  "truncated": false,
  "filters_applied": { "bbox": [-114.07, 51.0, -113.9, 51.1] },
  "disclaimer": "..."
}
```

### Admin (requires `JTA_ENABLE_ADMIN_REVIEW=true` + `X-JTA-Admin-Token`)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/admin/review-queue` | Paginated review queue for events, crime incidents, sources |
| `POST` | `/api/admin/review-queue/{entity_type}/{entity_id}/decision` | Apply a review decision |
| `GET` | `/api/admin/review-history` | Paginated `EvidenceReview` audit trail |

Valid decisions: `approve`, `reject`, `correct`, `dispute`, `remove`. Each decision is persisted to `EvidenceReview` and updates `public_visibility` on the entity.

### Admin Imports (requires `JTA_ENABLE_ADMIN_IMPORTS=true` + `X-JTA-Admin-Token`)

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/ingest/courtlistener` | Trigger a CourtListener REST API ingestion run |
| `POST` | `/api/admin/import/crime-incidents/manual-csv` | Upload a crime incidents CSV (admin) |
| `POST` | `/api/admin/ai/verify-source/{record_type}/{record_id}` | Verify source with Ollama (event or crime_incident) |
| `GET` | `/api/admin/review/items` | AI review item queue |
| `POST` | `/api/admin/review/items/{id}/{action}` | Act on an AI review item |

---

## Data Model (key entities)

```
Judge ──< Event >── Case ──< CaseParty >── Defendant
              │
              ├── EventSource ──> LegalSource
              ├── EventDefendant ──> Defendant
              ├── EventOutcome
              └── Location (court coordinates)

CrimeIncident   (separate layer — NOT linked to judges/cases)
EvidenceReview  (audit log of every review decision)
ReviewItem      (AI-generated evidence-clerk draft)
```

All entities carry `review_status` and `public_visibility`. Nothing appears on the public API until `public_visibility=True` and `review_status` is in an approved set (`verified_court_record`, `official_police_open_data_report`, etc.).

---

## Privacy and Safety Rules

These are enforced in code, not just policy:

- **Defendants are anonymized.** Public API returns `DEF-000001`-style labels. Real names never appear in public responses.
- **No personal addresses, DOBs, family details, victim locations, or residence indicators** are exposed anywhere in the public API. The serializer and AI pipeline both run redaction passes.
- **Map points are courthouse locations**, not home or incident addresses.
- **Crime incidents use generalized coordinates** — neighbourhood, community, or city-level centroid. `exact_address` precision is rejected at import. Zero-coordinate records are rejected.
- **Crime incident CSV imports default to `is_public=False`.** Records do not become public until manually reviewed and approved.
- **`source_url` on crime incidents must be a valid HTTP/HTTPS URL** or the record is rejected at import.
- **CourtListener-ingested events default to `pending_review` / `public_visibility=False`**. They do not appear on the public map or events API until reviewed.
- **Repeat-offender flags** come only from explicit matched phrases in source text. They are not inferred.
- **Outcomes require verified court, appeal, or official sources.** News is secondary context only and cannot create outcomes.
- **Review status is preserved on re-ingestion** unless safety-sensitive fields change, in which case the record drops back to `pending_review`.
- Crime incidents are not linked to judges, cases, or defendants unless a future verified legal record explicitly supports that linkage.

---

## Ingestion

### CourtListener / RECAP

Set `COURTLISTENER_API_TOKEN` in `.env`. The adapter targets the v4 REST API (`/api/rest/v4/dockets/`), fetches RECAP/PACER-derived docket entries, parses them with a deterministic classifier, and persists them as `Event` + `LegalSource` rows.

Run caps: configurable max pages, dockets per run, and a timeout. Retry/backoff on 429 and 5xx. Ingestion lock prevents concurrent runs. PACER-direct fetching (purchasing documents) is intentionally not implemented.

### Manual CSV Import

Upload a CSV with columns: `source_id`, `incident_type`, `incident_category`, `reported_at`, `occurred_at`, `latitude_public`, `longitude_public`, `precision_level`, `city`, `province_state`, `country`, `public_area_label`, `notes`, `source_name`, `source_url`, `is_public`.

Validation rejects: `exact_address` precision, zero coordinates, residence/victim terms in notes or area labels, non-HTTP source URLs. All imported records start `is_public=False` regardless of the CSV column.

---

## AI-Assisted Evidence Clerk

A deterministic (no external LLM call) pipeline that:

1. Redacts private data patterns from ingested text
2. Classifies record type and source quality
3. Writes a neutral plain-language summary
4. Suggests entity links (judge, case, defendant)
5. Creates a `ReviewItem` draft for admin review

AI outputs are **not authoritative**. All high-risk fields (repeat-offender indicators, crime-to-case links, post-release outcomes, news-only allegations) require human admin review before any public display. See `docs/AI_PIPELINE.md`.

---

## Review Workflow

```
Ingested record
    │
    ▼
review_status = "pending_review"
public_visibility = False
    │
    ▼
Admin reviews via /api/admin/review-queue
    │
    ├── approve  → review_status = "verified_court_record" (or appropriate), public_visibility = True
    ├── reject   → review_status = "rejected",              public_visibility = False
    ├── correct  → review_status = "corrected",             public_visibility = True,  correction_note set
    ├── dispute  → review_status = "disputed",              public_visibility = False, dispute_note set
    └── remove   → review_status = "removed_from_public",  public_visibility = False
    │
    ▼
EvidenceReview row written (previous_status, new_status, reviewer, timestamp, notes)
```

Every decision is logged to `EvidenceReview` and queryable via `GET /api/admin/review-history`.

---

### Current verification status

```bash
# Backend: creates backend/.venv, installs deps, runs alembic + pytest
./scripts/verify_backend.sh

# Frontend: requires Node 20 exactly — fails if wrong version
./scripts/verify_frontend.sh

# Docker: compose build + health check
./scripts/verify_docker.sh
```

## Verification Status

Current verification status is determined by CI. Committed proof logs in `artifacts/proof/` are historical artifacts only and do not reflect the current state of the codebase.

To verify the current state, run:

```bash
# Backend verification
./scripts/verify_backend.sh

# Frontend verification  
./scripts/verify_frontend.sh
```

### What each script does

**`verify_backend.sh`** (steps run in order, hard-fail on any error):
1. Locate Python 3 interpreter
2. Create or reuse `backend/.venv` and run `pip install -e ".[test]"`
3. Print `python --version` and `pip freeze`
4. `python -m compileall -q app`
5. `JTA_DATABASE_URL=sqlite:///./verify_migration_test.db python -m alembic upgrade head` — deletes DB before and after, **no skip clause**
6. `python -m pytest -q`

Timestamped logs written to `artifacts/proof/backend/<timestamp>.log`.

**`verify_frontend.sh`** (requires Node 20 — hard-fails if `node --version` is not `v20.*`):
1. Node version check — exit 1 if not v20
2. `npm ci`
3. `npm run lint`
4. `npm run typecheck`
5. `npm run build`

Timestamped logs written to `artifacts/proof/frontend/<timestamp>.log`.

### Manual backend (without the script)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"
python -m compileall -q app
JTA_DATABASE_URL=sqlite:///./verify_migration_test.db python -m alembic upgrade head
python -m pytest -q
```

### Current verification status

| Check | Status | Notes |
|---|---|---|
| `python -m compileall -q app` | See CI | Run `./scripts/verify_backend.sh` for current status |
| `python -m pytest -q` | See CI | Run `./scripts/verify_backend.sh` for current count |
| Alembic `upgrade head` (SQLite) | See CI | Run `./scripts/verify_backend.sh` to verify migrations |
| Frontend lint / typecheck / build | See CI | Run `./scripts/verify_frontend.sh` for current status |
| Docker Compose build | Manual | Manual verification required |
| PostGIS geometry | Ready | Migration exists; column added on PostgreSQL only |
| API split (incidents/aggregates) | Complete | Separate endpoints: `/api/map/crime-incidents?exclude_aggregate=true`, `/api/map/crime-aggregates` |

---

## Known Gaps

This is a prototype. The following are real gaps that would need to be closed before any production use:

**Auth and access control**
- No real authentication system. Admin access uses a single shared secret token (`X-JTA-Admin-Token`). There are no user accounts, sessions, roles, or per-user audit trails.
- The token is compared in plaintext. No rate limiting on auth attempts.

**Database and migrations**
- Alembic `upgrade head` has not been exercised in CI. The migration file matches the ORM (audited in `docs/schema_audit.md`) but there is no automated migration test in this runtime environment.
- `Base.metadata.create_all()` is used on startup when `AUTO_SEED=true`, bypassing Alembic entirely for local development.

**Security (Partially Hardened)**
- Rate limiting: SlowAPI-based limits configured (100/min public, 30/min admin, 60/min map, 10/min ingestion). In-memory storage; Redis recommended for production.
- Request size limits: Content-Length header check + chunked file reading with max_csv_upload_size enforcement.
- CORS: Strict origin validation in production (HTTPS-only, no wildcards). Fails startup if origins empty.
- Source verification: SourceSnapshot persistence with SSRF protection and content hashing.
- Source control: SourceRegistry ingestion control plane (fail-closed on missing sources).
- No security headers (CSP, HSTS, etc.).
- No secrets management — tokens are plain `.env` values.
- No complete security audit has been performed.

**Data and legal**
- Only SAMPLE data is seeded. No real court data is included.
- CourtListener ingestion has not been exercised end-to-end in this environment.
- Source licensing for any real data has not been reviewed.
- Crime incident layer uses manually imported sample records only (Saskatoon is manual CSV only; no full automatic collector exists yet). No live official police open-data adapter exists yet.
- No geocoding pipeline. Court coordinates are pre-seeded or manual.

**Operational**
- No production monitoring, alerting, or structured logging pipeline.
- No automated backups.
- No audit log retention policy or storage backend.
- `on_event("startup")` is deprecated in FastAPI; needs migration to `lifespan`.
- Frontend verified under Node 20.20.2 (2026-04-29). Build, lint, and typecheck pass.
- Frontend: See CI for current test counts (varies by environment).
- PostGIS geometry migration ready (PostgreSQL deployments only). **Bbox filtering uses lat/lon only; geom column exists but is not yet trusted for spatial queries.**
- Crime incidents and aggregates now fetched via separate API endpoints.
- Docker Compose requires manual verification (Docker unavailable in this environment).
- Docker Compose deployment has not been smoke-tested in this environment.

**Features not implemented**
- Source correction and dispute resolution workflow UI.
- User-facing source dispute submission.
- Full CourtListener coverage (PACER-direct document fetching intentionally excluded).
- Court-location geocoding (courthouse coordinates are manually seeded).
- Real-time ingestion / webhooks.
- Export or bulk download.

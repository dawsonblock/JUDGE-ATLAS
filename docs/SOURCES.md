# Source Registry and Data Boundaries

JudgeTracker Atlas separates legal decision records from reported crime incident context. Court records verify legal outcomes. Police/open-data records are reported incidents, not proof of guilt or conviction. News is secondary context only.

## Source Tiers

1. Court record, docket, court order, judgment, or appeal decision
2. Official police, prosecutor, corrections, or government release
3. Official city or police open-data portal
4. Reputable news article as secondary context
5. User submission pending moderator review

## Crime Incident Source Targets

Canada:

- Saskatoon Police Crime Mapping
- Toronto Police Public Safety Data Portal
- Calgary Police crime/statistics dashboards
- Vancouver Police open data, if available and licensing permits
- Statistics Canada geospatial crime explorer for aggregate context

United States:

- FBI Crime Data API for national context
- BJS NIBRS estimates API for estimates and trend analysis
- Chicago Data Portal crimes dataset
- Los Angeles Open Data crime dataset
- NYC Open Data complaint data, if licensing permits

## Crime Layer Rules

- Use generalized public-area coordinates only.
- Do not expose exact private locations, suspect names, victim details, private residences, DOBs, family details, or person profiles.
- Do not visually connect crime dots and judge/court dots unless a court record, official docket, police release, or official outcome document supports that connection.
- Treat reported incidents as mutable records that may change due to late reporting, reclassification, correction, or unfounded reports.
- Manual/import adapters are the only Phase 1 ingestion path. No aggressive scraping or terms-of-service bypassing is implemented.

## Legal Decision Rules

- CourtListener/RECAP remains the first court-data integration.
- PACER-direct access is a later option when RECAP does not contain required records.
- News cannot create a verified legal outcome by itself.
- Repeat-offender wording must remain indicator-based unless a source explicitly supports the legal fact.

## Review Workflow

New ingested legal events, legal sources, and crime incidents enter `pending_review` by default. Public endpoints only show records with public review statuses: `verified_court_record`, `official_police_open_data_report`, `news_only_context`, or `corrected`. Statuses `pending_review`, `disputed`, `rejected`, and `removed_from_public` are never exposed on public endpoints.

Review decisions are auditable through `evidence_reviews` and should capture:

- previous and new status
- reviewer
- reviewed date
- notes, correction notes, or dispute notes
- public visibility decision

Rejected and removed records should remain in the database for auditability, but they should not appear in public maps, timelines, or source lists.

## Web Monitoring (Crawlee)

Judge Atlas uses Crawlee for **controlled source monitoring only** — not open-ended web crawling.

### Purpose

Monitor known public pages for:
- Court announcement pages
- Police media release pages
- City/open data pages without APIs
- RSS/news feeds for source snapshots

### Safety Rules

1. **Strict allowlists** — Only domains explicitly configured (e.g., `saskatoonpolice.ca`)
2. **Disabled by default** — All targets require explicit admin enablement
3. **Request limits** — Max 100 requests per run (default: 25)
4. **Depth limits** — Max crawl depth 3 (default: 1)
5. **Low concurrency** — Max 5 concurrent requests (default: 2)
6. **Robots.txt compliance** — Enabled by default
7. **Never auto-publish** — All crawled content → `pending_review`
8. **Low confidence** — Max 0.5 confidence for crawled content
9. **Evidence snapshots** — Store source_url, fetched_at, content_hash, raw_content
10. **Pass through safety gates** — source_verifier, public_safety, publish_rules

### Flow

```
known source target → Crawlee fetch → snapshot → extractor → candidate item
→ pending_review → publication gate → public map (after approval only)
```

### Extractors

- `police_release_index/detail` — Police news releases
- `court_news_index/detail` — Court announcement pages
- `city_open_data_landing_page` — Open data portals
- `rss_or_news_listing` — RSS feeds

All extractors flag:
- Private address patterns
- Person names (for review)
- Low confidence scores

### CLI Usage

```bash
# List targets
python scripts/run_web_monitor.py --list

# Run specific target
python scripts/run_web_monitor.py --target saskatoon_police_news --limit 25

# Dry run (config check only)
python scripts/run_web_monitor.py --target saskatoon_police_news --dry-run
```

### Example Target (Disabled by Default)

```python
{
  "name": "Saskatoon Police News Releases",
  "source_type": "official_police_media",
  "base_url": "https://saskatoonpolice.ca",
  "allowed_domains": ["saskatoonpolice.ca"],
  "start_urls": ["https://saskatoonpolice.ca/news/"],
  "max_depth": 1,
  "max_requests": 25,
  "concurrency": 2,
  "source_tier": "official_police_open_data",
  "enabled": false,  // Must enable in admin panel
  "extractor_type": "police_release_index"
}
```

### Do NOT Use Crawlee For

- Open-ended web crawling
- Scraping entire websites
- Bypassing terms of service
- Collecting private social media profiles
- Collecting personal addresses or contact info
- Mass downloading documents
- Any use that violates robots.txt or site terms

### Data Retention

Raw HTML snapshots stored for provenance (up to configured retention). Extracted text limited to 2000 chars. Source URLs and content hashes retained permanently for audit trail.

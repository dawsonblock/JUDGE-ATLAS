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

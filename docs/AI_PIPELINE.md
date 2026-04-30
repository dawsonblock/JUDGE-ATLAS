# AI-Assisted Ingestion Pipeline

JudgeTracker Atlas treats AI as an evidence clerk, not an authority. The v1 pipeline is deterministic and local: it uses rules to redact, classify, summarize, suggest links, and create review items. It does not call an external model provider.

## Rules

- AI outputs require schema validation before storage.
- AI-created records enter admin review as drafts.
- High-risk claims require human/admin review before any public display.
- News-only records cannot verify legal outcomes.
- Crime incidents are reported incidents, not proof of guilt or conviction.
- Private addresses, victim/suspect private data, DOBs, phone numbers, emails, family details, medical details, minor identities, and exact residential coordinates must be redacted or blocked.
- AI must not visually or legally link crime dots to judge decisions unless a court record, docket, police release, or other official outcome document supports the link.

## Pipeline

```text
raw source
-> privacy redaction
-> deterministic classification
-> neutral summary
-> entity-link suggestions
-> ReviewItem
-> admin approve/reject/block/publish decision
```

Publishing a legal-event draft creates a hidden `pending_review` event. It does not automatically create public accusations, repeat-offender conclusions, crime-to-case links, post-release outcome links, or news-only allegations.

## Admin Endpoints

All AI admin endpoints are disabled by default through `JTA_ENABLE_ADMIN_IMPORTS=false`.

- `GET /api/admin/review/items`
- `GET /api/admin/review/items/{id}`
- `POST /api/admin/review/items/{id}/approve`
- `POST /api/admin/review/items/{id}/reject`
- `POST /api/admin/review/items/{id}/needs-more-sources`
- `POST /api/admin/review/items/{id}/block`
- `POST /api/admin/review/items/{id}/publish`
- `POST /api/admin/ai/process-source/{source_id}`

This is a prototype control, not production auth or role management.


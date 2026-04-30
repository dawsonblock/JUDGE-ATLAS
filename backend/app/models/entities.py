from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Location(Base, TimestampMixin):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location_type: Mapped[str] = mapped_column(String(80), nullable=False, default="courthouse")
    city: Mapped[str | None] = mapped_column(String(120))
    state: Mapped[str | None] = mapped_column(String(80))
    region: Mapped[str | None] = mapped_column(String(80))
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    # NOTE: geom column exists only on PostgreSQL (PostGIS), managed by Alembic.
    # The ORM does not map it because bbox filtering uses lat/lon only.
    # Future: Add geom mapping when triggers/generated columns maintain it.


class Court(Base, TimestampMixin):
    __tablename__ = "courts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    courtlistener_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    jurisdiction: Mapped[str | None] = mapped_column(String(80))
    region: Mapped[str | None] = mapped_column(String(80))
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False)

    location: Mapped[Location] = relationship()
    cases: Mapped[list["Case"]] = relationship(back_populates="court")
    events: Mapped[list["Event"]] = relationship(back_populates="court")
    cl_provenance: Mapped[dict | None] = mapped_column(JSON)


class Judge(Base, TimestampMixin):
    __tablename__ = "judges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    court_id: Mapped[int | None] = mapped_column(ForeignKey("courts.id"))
    cl_person_id: Mapped[str | None] = mapped_column(
        String(80), unique=True, index=True
    )

    court: Mapped[Court | None] = relationship()
    events: Mapped[list["Event"]] = relationship(back_populates="judge")


class Case(Base, TimestampMixin):
    __tablename__ = "cases"
    __table_args__ = (UniqueConstraint("court_id", "normalized_docket_number", name="uq_case_court_normalized_docket"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    court_id: Mapped[int] = mapped_column(ForeignKey("courts.id"), nullable=False)
    docket_number: Mapped[str] = mapped_column(String(120), nullable=False)
    normalized_docket_number: Mapped[str] = mapped_column(String(120), nullable=False)
    caption: Mapped[str] = mapped_column(String(500), nullable=False)
    case_type: Mapped[str] = mapped_column(String(80), default="criminal")
    filed_date: Mapped[date | None] = mapped_column(Date)
    terminated_date: Mapped[date | None] = mapped_column(Date)
    courtlistener_docket_id: Mapped[str | None] = mapped_column(String(80), index=True)

    court: Mapped[Court] = relationship(back_populates="cases")
    parties: Mapped[list["CaseParty"]] = relationship(back_populates="case")
    events: Mapped[list["Event"]] = relationship(back_populates="case")
    cl_provenance: Mapped[dict | None] = mapped_column(JSON)


class Defendant(Base, TimestampMixin):
    __tablename__ = "defendants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    anonymized_id: Mapped[str] = mapped_column(String(24), nullable=False, unique=True, index=True)
    public_name: Mapped[str | None] = mapped_column(String(255))
    normalized_public_name: Mapped[str | None] = mapped_column(String(255), index=True)

    parties: Mapped[list["CaseParty"]] = relationship(back_populates="defendant")
    event_links: Mapped[list["EventDefendant"]] = relationship(back_populates="defendant")


class CaseParty(Base, TimestampMixin):
    __tablename__ = "case_parties"
    __table_args__ = (UniqueConstraint("case_id", "normalized_name", "party_type", name="uq_case_party_name_type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), nullable=False)
    defendant_id: Mapped[int | None] = mapped_column(ForeignKey("defendants.id"))
    party_type: Mapped[str] = mapped_column(String(80), nullable=False)
    public_name: Mapped[str | None] = mapped_column(String(255))
    normalized_name: Mapped[str | None] = mapped_column(String(255), index=True)

    case: Mapped[Case] = relationship(back_populates="parties")
    defendant: Mapped[Defendant | None] = relationship(back_populates="parties")


class Event(Base, TimestampMixin):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    court_id: Mapped[int] = mapped_column(ForeignKey("courts.id"), nullable=False)
    judge_id: Mapped[int | None] = mapped_column(ForeignKey("judges.id"))
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), nullable=False)
    primary_location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    event_subtype: Mapped[str | None] = mapped_column(String(120))
    decision_result: Mapped[str | None] = mapped_column(String(120))
    decision_date: Mapped[date | None] = mapped_column(Date, index=True)
    posted_date: Mapped[date | None] = mapped_column(Date)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    repeat_offender_indicator: Mapped[bool] = mapped_column("repeat_offender_flag", Boolean, default=False, nullable=False)
    verified_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source_quality: Mapped[str] = mapped_column(String(80), default="court_record")
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    classifier_metadata: Mapped[dict | None] = mapped_column(JSON)
    review_status: Mapped[str] = mapped_column(String(80), default="pending_review", nullable=False, index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[str | None] = mapped_column(String(120))
    review_notes: Mapped[str | None] = mapped_column(Text)
    correction_note: Mapped[str | None] = mapped_column(Text)
    dispute_note: Mapped[str | None] = mapped_column(Text)
    public_visibility: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    court: Mapped[Court] = relationship(back_populates="events")
    judge: Mapped[Judge | None] = relationship(back_populates="events")
    case: Mapped[Case] = relationship(back_populates="events")
    primary_location: Mapped[Location] = relationship()
    defendant_links: Mapped[list["EventDefendant"]] = relationship(
        back_populates="event"
    )
    source_links: Mapped[list["EventSource"]] = relationship(
        back_populates="event"
    )
    outcomes: Mapped[list["Outcome"]] = relationship(back_populates="event")
    cl_provenance: Mapped[dict | None] = mapped_column(JSON)


class EventDefendant(Base):
    __tablename__ = "event_defendants"
    __table_args__ = (UniqueConstraint("event_id", "defendant_id", name="uq_event_defendant"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False)
    defendant_id: Mapped[int] = mapped_column(ForeignKey("defendants.id"), nullable=False)

    event: Mapped[Event] = relationship(back_populates="defendant_links")
    defendant: Mapped[Defendant] = relationship(back_populates="event_links")


class Topic(Base, TimestampMixin):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)


class EventTopic(Base):
    __tablename__ = "event_topics"
    __table_args__ = (UniqueConstraint("event_id", "topic_id", name="uq_event_topic"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), nullable=False)


class LegalSource(Base, TimestampMixin):
    __tablename__ = "legal_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    api_url: Mapped[str | None] = mapped_column(Text)
    url_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    source_quality: Mapped[str] = mapped_column(String(80), nullable=False)
    verified_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_status: Mapped[str] = mapped_column(String(80), default="pending_review", nullable=False, index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[str | None] = mapped_column(String(120))
    review_notes: Mapped[str | None] = mapped_column(Text)
    correction_note: Mapped[str | None] = mapped_column(Text)
    dispute_note: Mapped[str | None] = mapped_column(Text)
    public_visibility: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    cl_provenance: Mapped[dict | None] = mapped_column(JSON)

    event_links: Mapped[list["EventSource"]] = relationship(
        back_populates="source"
    )


class CrimeIncident(Base, TimestampMixin):
    __tablename__ = "crime_incidents"
    __table_args__ = (UniqueConstraint("source_name", "external_id", name="uq_crime_incident_source_external"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str | None] = mapped_column(String(120), index=True)
    external_id: Mapped[str | None] = mapped_column(String(120), index=True)
    incident_type: Mapped[str] = mapped_column(String(120), nullable=False)
    incident_category: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    reported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    city: Mapped[str | None] = mapped_column(String(120), index=True)
    province_state: Mapped[str | None] = mapped_column(String(120), index=True)
    country: Mapped[str | None] = mapped_column(String(80), index=True)
    public_area_label: Mapped[str | None] = mapped_column(String(255))
    latitude_public: Mapped[float | None] = mapped_column(Float)
    longitude_public: Mapped[float | None] = mapped_column(Float)
    precision_level: Mapped[str] = mapped_column(String(80), default="general_area", nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    verification_status: Mapped[str] = mapped_column(String(80), default="reported", nullable=False, index=True)
    data_last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    review_status: Mapped[str] = mapped_column(String(80), default="pending_review", nullable=False, index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[str | None] = mapped_column(String(120))
    review_notes: Mapped[str | None] = mapped_column(Text)
    correction_note: Mapped[str | None] = mapped_column(Text)
    dispute_note: Mapped[str | None] = mapped_column(Text)

    is_aggregate: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )

    source_links: Mapped[list["CrimeIncidentSource"]] = relationship(
        back_populates="incident"
    )
    event_links: Mapped[list["CrimeIncidentEventLink"]] = relationship(
        back_populates="incident"
    )


class EvidenceReview(Base):
    __tablename__ = "evidence_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    previous_status: Mapped[str | None] = mapped_column(String(80))
    new_status: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(120))
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    public_visibility: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ReviewItem(Base):
    __tablename__ = "review_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    record_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    raw_source_id: Mapped[int | None] = mapped_column(Integer, index=True)
    suggested_payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    source_quality: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    privacy_status: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    publish_recommendation: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(80), default="pending", nullable=False, index=True)
    reviewer_id: Mapped[str | None] = mapped_column(String(120))
    reviewer_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    action_logs: Mapped[list["ReviewActionLog"]] = relationship(back_populates="review_item")


class ReviewActionLog(Base):
    __tablename__ = "review_action_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    review_item_id: Mapped[int] = mapped_column(ForeignKey("review_items.id"), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(120), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    before_json: Mapped[dict | None] = mapped_column(JSON)
    after_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    review_item: Mapped[ReviewItem] = relationship(back_populates="action_logs")


class EventSource(Base):
    __tablename__ = "event_sources"
    __table_args__ = (UniqueConstraint("event_id", "source_id", name="uq_event_source"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False)
    source_id: Mapped[int] = mapped_column(ForeignKey("legal_sources.id"), nullable=False)
    supports_outcome: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    event: Mapped[Event] = relationship(back_populates="source_links")
    source: Mapped[LegalSource] = relationship(back_populates="event_links")


class Outcome(Base, TimestampMixin):
    __tablename__ = "outcomes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False)
    outcome_type: Mapped[str] = mapped_column(String(120), nullable=False)
    outcome_date: Mapped[date | None] = mapped_column(Date)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    verified_source_id: Mapped[int] = mapped_column(ForeignKey("legal_sources.id"), nullable=False)

    event: Mapped[Event] = relationship(back_populates="outcomes")
    verified_source: Mapped[LegalSource] = relationship()


class IngestionRun(Base, TimestampMixin):
    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_name: Mapped[str] = mapped_column(String(120), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(80), default="running")
    fetched_count: Mapped[int] = mapped_column(Integer, default=0)
    parsed_count: Mapped[int] = mapped_column(Integer, default=0)
    persisted_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[list | None] = mapped_column(JSON)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(80), index=True)
    entity_id: Mapped[str | None] = mapped_column(String(255), index=True)
    payload: Mapped[dict | None] = mapped_column(JSON)
    actor_ip: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class CrimeIncidentSource(Base):
    __tablename__ = "crime_incident_sources"
    __table_args__ = (
        UniqueConstraint("crime_incident_id", "source_id", name="uq_crime_incident_source"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crime_incident_id: Mapped[int] = mapped_column(ForeignKey("crime_incidents.id"), nullable=False, index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("legal_sources.id"), nullable=False, index=True)
    relationship_status: Mapped[str] = mapped_column(String(80), default="verified_source_link", nullable=False)
    supports_claim: Mapped[str | None] = mapped_column(Text)

    incident: Mapped["CrimeIncident"] = relationship(back_populates="source_links")
    source: Mapped["LegalSource"] = relationship()


class CrimeIncidentEventLink(Base):
    __tablename__ = "crime_incident_event_links"
    __table_args__ = (
        UniqueConstraint("crime_incident_id", "event_id", name="uq_crime_incident_event"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crime_incident_id: Mapped[int] = mapped_column(ForeignKey("crime_incidents.id"), nullable=False, index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False, index=True)
    relationship_status: Mapped[str] = mapped_column(String(80), default="unverified_context", nullable=False)
    link_note: Mapped[str | None] = mapped_column(Text)

    incident: Mapped["CrimeIncident"] = relationship(back_populates="event_links")
    event: Mapped["Event"] = relationship()


class Boundary(Base, TimestampMixin):
    """Simplified administrative boundary from Natural Earth."""

    __tablename__ = "boundaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    iso_code: Mapped[str | None] = mapped_column(String(10), index=True)
    boundary_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    parent_iso: Mapped[str | None] = mapped_column(String(10))
    source: Mapped[str] = mapped_column(String(80), default="natural_earth", nullable=False)
    geojson_simplified: Mapped[str | None] = mapped_column(Text)


class AICorrectnessCheck(Base):
    """Structured correctness report for a single map record.

    The AI checks accuracy only — no guilt scores, no judge scores,
    no danger scores, no automated accusations.
    """

    __tablename__ = "ai_correctness_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    record_type: Mapped[str] = mapped_column(
        String(80), nullable=False, index=True
    )
    record_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(40), nullable=False)
    event_type_supported: Mapped[bool] = mapped_column(Boolean, nullable=False)
    date_supported: Mapped[bool] = mapped_column(Boolean, nullable=False)
    location_supported: Mapped[bool] = mapped_column(Boolean, nullable=False)
    status_supported: Mapped[bool] = mapped_column(Boolean, nullable=False)
    source_supports_claim: Mapped[bool] = mapped_column(Boolean, nullable=False)
    duplicate_candidate: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    possible_duplicate_ids: Mapped[list | None] = mapped_column(JSON)
    privacy_risk: Mapped[str] = mapped_column(
        String(20), default="low", nullable=False, index=True
    )
    map_quality: Mapped[str] = mapped_column(
        String(40), nullable=False, index=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    result_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    findings: Mapped[list["AICorrectnessFinding"]] = relationship(
        back_populates="check", cascade="all, delete-orphan"
    )


class AICorrectnessFinding(Base):
    """Individual finding attached to a correctness check."""

    __tablename__ = "ai_correctness_findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    check_id: Mapped[int] = mapped_column(
        ForeignKey("ai_correctness_checks.id"), nullable=False, index=True
    )
    finding_type: Mapped[str] = mapped_column(
        String(80), nullable=False, index=True
    )
    field_name: Mapped[str | None] = mapped_column(String(80))
    expected: Mapped[str | None] = mapped_column(Text)
    found: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(
        String(20), default="info", nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text)

    check: Mapped["AICorrectnessCheck"] = relationship(
        back_populates="findings"
    )


class CLBulkProvenance(Base):
    """One row per record normalized from a CourtListener bulk snapshot.

    Allows every normalized court/case/event/source to be traced back to:
    - CourtListener table and source row ID
    - source CSV file and snapshot date
    - import run ID
    """

    __tablename__ = "cl_bulk_provenance"
    __table_args__ = (
        UniqueConstraint(
            "run_id", "cl_table", "cl_row_id",
            name="uq_cl_bulk_provenance",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("courtlistener_bulk_runs.id"),
        nullable=False,
        index=True,
    )
    cl_table: Mapped[str] = mapped_column(String(80), nullable=False)
    cl_row_id: Mapped[str] = mapped_column(String(80), nullable=False)
    source_file: Mapped[str] = mapped_column(String(120), nullable=False)
    snapshot_date: Mapped[str] = mapped_column(String(20), nullable=False)
    record_type: Mapped[str] = mapped_column(String(40), nullable=False)
    record_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class CourtListenerBulkRun(Base):
    """Tracks one file from one CourtListener quarterly snapshot.

    The unique constraint on (snapshot_date, file_name) prevents the
    same file from being imported twice unless force=True is passed,
    which deletes the old row first.
    """

    __tablename__ = "courtlistener_bulk_runs"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_date", "file_name", name="uq_cl_bulk_run"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_date: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )
    file_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False, index=True
    )
    rows_read: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_persisted: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    rows_skipped: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    errors: Mapped[list | None] = mapped_column(JSON)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class SourceSnapshot(Base):
    """Source content snapshots for provenance and archival."""

    __tablename__ = "source_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_content: Mapped[str | None] = mapped_column(Text)
    extracted_text: Mapped[str | None] = mapped_column(Text)
    http_status: Mapped[int | None] = mapped_column(Integer)
    content_type: Mapped[str | None] = mapped_column(String(255))
    headers_json: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    storage_backend: Mapped[str] = mapped_column(
        String(20), nullable=False, default="db"
    )
    storage_path: Mapped[str | None] = mapped_column(String(1024))
    retention_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class SourceRegistry(Base, TimestampMixin):
    """Registry of ingestion sources with metadata and health tracking."""

    __tablename__ = "source_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_key: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True
    )
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str | None] = mapped_column(String(80))
    province_state: Mapped[str | None] = mapped_column(String(80))
    city: Mapped[str | None] = mapped_column(String(120))
    source_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="unknown"
    )
    license: Mapped[str | None] = mapped_column(String(50))
    license_url: Mapped[str | None] = mapped_column(String(2048))
    fetch_method: Mapped[str] = mapped_column(
        String(20), nullable=False, default="manual"
    )
    update_cadence: Mapped[str] = mapped_column(
        String(20), nullable=False, default="manual"
    )
    fields_supported: Mapped[str | None] = mapped_column(Text)
    precision_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="city_centroid"
    )
    auto_publish_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    requires_manual_review: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    parser_version: Mapped[str | None] = mapped_column(String(20))
    last_successful_fetch: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    last_error: Mapped[str | None] = mapped_column(Text)
    last_error_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    config_json: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

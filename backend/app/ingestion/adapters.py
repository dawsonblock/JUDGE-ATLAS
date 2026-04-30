from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass
class RawRecord:
    source_name: str
    payload: dict[str, Any]


@dataclass
class ParsedRecord:
    source_name: str
    docket_id: str | None = None
    docket_number: str | None = None
    court_code: str | None = None
    court_name: str | None = None
    caption: str | None = None
    date_filed: date | None = None
    date_terminated: date | None = None
    judge_name: str | None = None
    docket_text: str | None = None
    # Docket entry fields for per-entry event creation
    docket_entry_id: str | None = None
    recap_document_id: str | None = None
    entry_number: int | None = None
    entry_date: date | None = None
    entry_description: str | None = None
    document_links: list[str] = field(default_factory=list)
    parties: list[dict[str, Any]] = field(default_factory=list)
    source_url: str | None = None
    source_api_url: str | None = None
    source_public_url: str | None = None
    source_quality: str = "court_record"
    raw: dict[str, Any] = field(default_factory=dict)


class SourceAdapter(ABC):
    @abstractmethod
    def fetch(self, since: datetime) -> list[RawRecord]:
        raise NotImplementedError

    @abstractmethod
    def parse(self, raw: RawRecord) -> ParsedRecord:
        raise NotImplementedError

    def parse_many(self, raw: RawRecord) -> list[ParsedRecord]:
        """Parse a raw record into multiple parsed records (one per docket entry).

        Default implementation returns a single record from parse().
        Subclasses can override to emit multiple records per docket.
        """
        return [self.parse(raw)]


class CourtOpinionRSSAdapter(SourceAdapter):
    """Placeholder for official opinion/order feeds."""

    def fetch(self, since: datetime) -> list[RawRecord]:
        return []

    def parse(self, raw: RawRecord) -> ParsedRecord:
        return ParsedRecord(source_name="court_opinion_rss", raw=raw.payload)


class NewsAdapter(SourceAdapter):
    """Placeholder only. News is secondary context and never a primary legal record."""

    def fetch(self, since: datetime) -> list[RawRecord]:
        return []

    def parse(self, raw: RawRecord) -> ParsedRecord:
        return ParsedRecord(source_name="news", source_quality="secondary_context", raw=raw.payload)

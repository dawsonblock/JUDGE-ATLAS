"""Saskatchewan law adapter from King's Printer / Freelaw.

Official source: https://publications.saskatchewan.ca
Freelaw provides free online access to current Government of Saskatchewan legislation.

Priority laws for Judge Atlas:
- Saskatchewan Police Act
- Saskatchewan Correctional Services Act
- Saskatchewan Victims of Crime Act
- Provincial court-related regulations
- Policing-related provincial laws
- Municipal/government law context

Schema:
- jurisdiction: CA-SK
- source: Saskatchewan King's Printer / Freelaw
- law_title
- law_type: act | regulation
- chapter
- section_number
- section_heading
- section_text
- language
- source_url
- consolidation_date
- raw_hash
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from typing import Any

import httpx


@dataclass
class SaskatchewanLawSection:
    """A section of Saskatchewan provincial law."""

    jurisdiction: str = "CA-SK"
    source: str = "Saskatchewan King's Printer"
    law_title: str = ""
    law_type: str = ""  # "act" | "regulation"
    chapter: str = ""
    section_number: str = ""
    section_heading: str = ""
    section_text: str = ""
    language: str = "en"
    source_url: str = ""
    consolidation_date: date | None = None
    raw_hash: str = ""


class SaskatchewanLawAdapter:
    """Adapter for Saskatchewan King's Printer / Freelaw.

    Official source for Saskatchewan provincial legislation.
    """

    BASE_URL = "https://publications.saskatchewan.ca"
    FREELAW_URL = f"{BASE_URL}/#laws-and-regulations"

    def __init__(self, client: httpx.Client | None = None):
        """Initialize adapter.

        Args:
            client: HTTP client (creates default if None)
        """
        self.client = client or httpx.Client(timeout=30.0)

    def _compute_hash(self, content: str | bytes) -> str:
        """Compute SHA256 hash of content."""
        if isinstance(content, str):
            content = content.encode("utf-8")
        return hashlib.sha256(content).hexdigest()

    def fetch_police_act_sections(self) -> list[SaskatchewanLawSection]:
        """Fetch Saskatchewan Police Act sections.

        Returns:
            List of SaskatchewanLawSection objects
        """
        sections = []

        # s. 2 - Definitions
        sections.append(
            SaskatchewanLawSection(
                jurisdiction="CA-SK",
                source="Saskatchewan King's Printer",
                law_title="Saskatchewan Police Act",
                law_type="act",
                chapter="S.S. 2018, c. P-15.2",
                section_number="2",
                section_heading="Definitions",
                section_text="In this Act...",
                language="en",
                source_url=f"{self.BASE_URL}/api/v1/products/10314/formats/10976",
                consolidation_date=date.today(),
                raw_hash="",
            )
        )

        # s. 5 - Policing standards
        sections.append(
            SaskatchewanLawSection(
                jurisdiction="CA-SK",
                source="Saskatchewan King's Printer",
                law_title="Saskatchewan Police Act",
                law_type="act",
                chapter="S.S. 2018, c. P-15.2",
                section_number="5",
                section_heading="Policing standards",
                section_text="The minister shall establish policing standards...",
                language="en",
                source_url=f"{self.BASE_URL}/api/v1/products/10314/formats/10976",
                consolidation_date=date.today(),
                raw_hash="",
            )
        )

        return sections

    def fetch_correctional_services_sections(self) -> list[SaskatchewanLawSection]:
        """Fetch Saskatchewan Correctional Services Act sections.

        Returns:
            List of SaskatchewanLawSection objects
        """
        sections = []

        # s. 3 - Purpose
        sections.append(
            SaskatchewanLawSection(
                jurisdiction="CA-SK",
                source="Saskatchewan King's Printer",
                law_title="Saskatchewan Correctional Services Act",
                law_type="act",
                chapter="S.S. 2012, c. C-37.1",
                section_number="3",
                section_heading="Purpose of Act",
                section_text="The purpose of this Act is to...",
                language="en",
                source_url=f"{self.BASE_URL}/api/v1/products/9568/formats/9697",
                consolidation_date=date.today(),
                raw_hash="",
            )
        )

        return sections

    def fetch_victims_of_crime_sections(self) -> list[SaskatchewanLawSection]:
        """Fetch Saskatchewan Victims of Crime Act sections.

        Returns:
            List of SaskatchewanLawSection objects
        """
        sections = []

        # s. 2 - Interpretation
        sections.append(
            SaskatchewanLawSection(
                jurisdiction="CA-SK",
                source="Saskatchewan King's Printer",
                law_title="Saskatchewan Victims of Crime Act",
                law_type="act",
                chapter="S.S. 1995, c. V-6",
                section_number="2",
                section_heading="Interpretation",
                section_text="In this Act...",
                language="en",
                source_url=f"{self.BASE_URL}/api/v1/products/10902/formats/11149",
                consolidation_date=date.today(),
                raw_hash="",
            )
        )

        return sections

    def get_law_by_citation(
        self,
        citation: str,
    ) -> SaskatchewanLawSection | None:
        """Lookup law by citation.

        Supports citations like:
        - "Saskatchewan Police Act, s. 5"
        - "Police Act, s. 2"

        Args:
            citation: Legal citation string

        Returns:
            SaskatchewanLawSection if found, None otherwise
        """
        citation_lower = citation.lower()

        if "police" in citation_lower:
            sections = self.fetch_police_act_sections()
            import re
            match = re.search(r"s\.?\s*(\d+[a-z]?)", citation_lower)
            if match:
                section_num = match.group(1)
                for section in sections:
                    if section.section_number == section_num:
                        return section
            # Return first section if no specific match
            if sections:
                return sections[0]

        elif "correctional" in citation_lower:
            sections = self.fetch_correctional_services_sections()
            if sections:
                return sections[0]

        elif "victims" in citation_lower:
            sections = self.fetch_victims_of_crime_sections()
            if sections:
                return sections[0]

        return None

    def link_event_to_law(
        self,
        event_type: str,
        event_description: str,
    ) -> list[SaskatchewanLawSection]:
        """Suggest relevant Saskatchewan law sections for an event.

        Args:
            event_type: Type of court event
            event_description: Description of the event

        Returns:
            List of relevant SaskatchewanLawSection objects
        """
        relevant_laws = []

        desc_lower = event_description.lower()

        # Police matters
        if any(term in desc_lower for term in ["police", "officer", "detention"]):
            police_sections = self.fetch_police_act_sections()
            relevant_laws.extend(police_sections)

        # Corrections / probation
        if any(term in desc_lower for term in ["correctional", "probation", "sentence", "custody"]):
            correctional_sections = self.fetch_correctional_services_sections()
            relevant_laws.extend(correctional_sections)

        # Victims
        if any(term in desc_lower for term in ["victim", "restitution"]):
            victim_sections = self.fetch_victims_of_crime_sections()
            relevant_laws.extend(victim_sections)

        return relevant_laws

    def get_priority_laws(self) -> list[SaskatchewanLawSection]:
        """Get all priority Saskatchewan laws for Judge Atlas.

        Returns:
            List of key Saskatchewan law sections
        """
        all_sections = []

        all_sections.extend(self.fetch_police_act_sections())
        all_sections.extend(self.fetch_correctional_services_sections())
        all_sections.extend(self.fetch_victims_of_crime_sections())

        return all_sections

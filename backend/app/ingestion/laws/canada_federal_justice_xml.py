"""Justice Laws Website XML adapter for federal Canadian law.

Official source: https://laws.justice.gc.ca

Provides consolidated federal Acts and regulations in XML format.
Federal consolidated Acts and regulations are official as of June 1, 2009.

Schema:
- jurisdiction: CA-FED
- source: Justice Laws
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
class LawSection:
    """A section of Canadian federal law."""

    jurisdiction: str = "CA-FED"
    source: str = "Justice Laws"
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


class JusticeLawsAdapter:
    """Adapter for Justice Laws Website XML data.

    Official source for Canadian federal legislation.
    """

    BASE_URL = "https://laws.justice.gc.ca"
    XML_INDEX_URL = f"{BASE_URL}/eng/XML/LIndex/"

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

    def fetch_law_index(self) -> list[dict[str, Any]]:
        """Fetch list of available laws from XML index.

        Returns:
            List of law metadata dictionaries
        """
        try:
            response = self.client.get(self.XML_INDEX_URL)
            response.raise_for_status()
            # Parse XML index - simplified for prototype
            # In production, parse full XML structure
            return []
        except httpx.HTTPError as e:
            raise RuntimeError(f"Failed to fetch law index: {e}") from e

    def fetch_act_sections(
        self,
        act_name: str,
        chapter: str | None = None,
    ) -> list[LawSection]:
        """Fetch sections of a specific federal Act.

        Priority laws for Judge Atlas:
        - Criminal Code (R.S.C., 1985, c. C-46)
        - Youth Criminal Justice Act (S.C. 2002, c. 1)
        - Controlled Drugs and Substances Act (S.C. 1996, c. 19)
        - Corrections and Conditional Release Act (S.C. 1992, c. 20)
        - Canada Evidence Act (R.S.C., 1985, c. C-5)
        - Canadian Victims Bill of Rights (S.C. 2015, c. 13)

        Args:
            act_name: Short name of the Act (e.g., "Criminal Code")
            chapter: Chapter reference if known

        Returns:
            List of LawSection objects
        """
        sections = []

        # Example section structure
        # In production, parse actual XML from Justice Laws
        if act_name == "Criminal Code":
            # s. 515 - Judicial interim release / bail
            sections.append(
                LawSection(
                    jurisdiction="CA-FED",
                    source="Justice Laws",
                    law_title="Criminal Code",
                    law_type="act",
                    chapter=chapter or "R.S.C., 1985, c. C-46",
                    section_number="515",
                    section_heading="Judicial interim release",
                    section_text="Order of release / Order of detention...",
                    language="en",
                    source_url=f"{self.BASE_URL}/eng/acts/C-46/section-515.html",
                    consolidation_date=date.today(),
                    raw_hash="",  # Would compute from actual content
                )
            )

            # s. 718 - Sentencing principles
            sections.append(
                LawSection(
                    jurisdiction="CA-FED",
                    source="Justice Laws",
                    law_title="Criminal Code",
                    law_type="act",
                    chapter=chapter or "R.S.C., 1985, c. C-46",
                    section_number="718",
                    section_heading="Purpose and principles of sentencing",
                    section_text="The fundamental purpose of sentencing...",
                    language="en",
                    source_url=f"{self.BASE_URL}/eng/acts/C-46/section-718.html",
                    consolidation_date=date.today(),
                    raw_hash="",
                )
            )

            # s. 753 - Dangerous offender
            sections.append(
                LawSection(
                    jurisdiction="CA-FED",
                    source="Justice Laws",
                    law_title="Criminal Code",
                    law_type="act",
                    chapter=chapter or "R.S.C., 1985, c. C-46",
                    section_number="753",
                    section_heading="Dangerous offenders and long-term offenders",
                    section_text="Finding of dangerous offender...",
                    language="en",
                    source_url=f"{self.BASE_URL}/eng/acts/C-46/section-753.html",
                    consolidation_date=date.today(),
                    raw_hash="",
                )
            )

        return sections

    def fetch_youth_criminal_justice_sections(self) -> list[LawSection]:
        """Fetch Youth Criminal Justice Act sections.

        Returns:
            List of LawSection objects for YCJA
        """
        sections = []

        # s. 3 - Declaration of principles
        sections.append(
            LawSection(
                jurisdiction="CA-FED",
                source="Justice Laws",
                law_title="Youth Criminal Justice Act",
                law_type="act",
                chapter="S.C. 2002, c. 1",
                section_number="3",
                section_heading="Declaration of principles",
                section_text="The youth criminal justice system...",
                language="en",
                source_url=f"{self.BASE_URL}/eng/acts/Y-1.5/section-3.html",
                consolidation_date=date.today(),
                raw_hash="",
            )
        )

        return sections

    def get_law_by_citation(
        self,
        citation: str,
    ) -> LawSection | None:
        """Lookup law by citation.

        Supports citations like:
        - "Criminal Code, s. 515"
        - "Criminal Code, s. 718(1)"
        - "YCJA, s. 3"

        Args:
            citation: Legal citation string

        Returns:
            LawSection if found, None otherwise
        """
        # Parse citation
        citation_lower = citation.lower()

        if "criminal code" in citation_lower:
            # Extract section number
            import re
            match = re.search(r"s\.?\s*(\d+[a-z]?)", citation_lower)
            if match:
                section_num = match.group(1)
                sections = self.fetch_act_sections("Criminal Code")
                for section in sections:
                    if section.section_number == section_num:
                        return section

        elif "ycja" in citation_lower or "youth" in citation_lower:
            sections = self.fetch_youth_criminal_justice_sections()
            if sections:
                return sections[0]

        return None

    def link_event_to_law(
        self,
        event_type: str,
        event_description: str,
    ) -> list[LawSection]:
        """Suggest relevant law sections for an event.

        Args:
            event_type: Type of court event
            event_description: Description of the event

        Returns:
            List of relevant LawSection objects
        """
        relevant_laws = []

        desc_lower = event_description.lower()

        # Bail / release
        if any(term in desc_lower for term in ["bail", "release", "detention", "515"]):
            bail_section = self.get_law_by_citation("Criminal Code, s. 515")
            if bail_section:
                relevant_laws.append(bail_section)

        # Sentencing
        if any(term in desc_lower for term in ["sentence", "sentencing", "718"]):
            sentencing_section = self.get_law_by_citation("Criminal Code, s. 718")
            if sentencing_section:
                relevant_laws.append(sentencing_section)

        # Dangerous offender
        if any(term in desc_lower for term in ["dangerous offender", "753"]):
            do_section = self.get_law_by_citation("Criminal Code, s. 753")
            if do_section:
                relevant_laws.append(do_section)

        # Youth matters
        if any(term in desc_lower for term in ["youth", "young person", "ycja"]):
            youth_sections = self.fetch_youth_criminal_justice_sections()
            relevant_laws.extend(youth_sections)

        return relevant_laws

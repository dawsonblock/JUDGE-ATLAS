"""Tests for Canadian law ingestion adapters.

Tests Justice Laws and Saskatchewan law adapters.
"""

import pytest

from app.ingestion.laws import JusticeLawsAdapter, SaskatchewanLawAdapter
from app.ingestion.laws.canada_federal_justice_xml import LawSection
from app.ingestion.laws.canada_saskatchewan import SaskatchewanLawSection


class TestJusticeLawsAdapter:
    """Test federal Justice Laws adapter."""

    def test_adapter_initializes(self):
        """Adapter should initialize with default client."""
        adapter = JusticeLawsAdapter()
        assert adapter is not None
        assert adapter.BASE_URL == "https://laws.justice.gc.ca"

    def test_fetch_criminal_code_sections(self):
        """Should return Criminal Code sections."""
        adapter = JusticeLawsAdapter()

        sections = adapter.fetch_act_sections("Criminal Code")

        assert len(sections) > 0
        # Check structure
        for section in sections:
            assert section.jurisdiction == "CA-FED"
            assert section.source == "Justice Laws"
            assert section.law_title == "Criminal Code"
            assert section.law_type == "act"
            assert section.section_number
            assert section.section_heading
            assert section.source_url.startswith("https://")

    def test_section_515_bail_exists(self):
        """Should have s. 515 (bail) in Criminal Code."""
        adapter = JusticeLawsAdapter()

        sections = adapter.fetch_act_sections("Criminal Code")
        section_515 = [s for s in sections if s.section_number == "515"]

        assert len(section_515) == 1
        assert "Judicial interim release" in section_515[0].section_heading

    def test_section_718_sentencing_exists(self):
        """Should have s. 718 (sentencing) in Criminal Code."""
        adapter = JusticeLawsAdapter()

        sections = adapter.fetch_act_sections("Criminal Code")
        section_718 = [s for s in sections if s.section_number == "718"]

        assert len(section_718) == 1
        assert "sentencing" in section_718[0].section_heading.lower()

    def test_section_753_dangerous_offender_exists(self):
        """Should have s. 753 (dangerous offender) in Criminal Code."""
        adapter = JusticeLawsAdapter()

        sections = adapter.fetch_act_sections("Criminal Code")
        section_753 = [s for s in sections if s.section_number == "753"]

        assert len(section_753) == 1
        assert "dangerous" in section_753[0].section_heading.lower()

    def test_get_law_by_citation(self):
        """Should lookup law by citation."""
        adapter = JusticeLawsAdapter()

        section = adapter.get_law_by_citation("Criminal Code, s. 515")

        assert section is not None
        assert section.section_number == "515"
        assert "Criminal Code" in section.law_title

    def test_link_event_to_law_bail(self):
        """Should link bail events to s. 515."""
        adapter = JusticeLawsAdapter()

        laws = adapter.link_event_to_law(
            event_type="bail_hearing",
            event_description="Judicial interim release hearing",
        )

        # Should include s. 515
        section_515 = [l for l in laws if l.section_number == "515"]
        assert len(section_515) == 1

    def test_link_event_to_law_sentencing(self):
        """Should link sentencing events to s. 718."""
        adapter = JusticeLawsAdapter()

        laws = adapter.link_event_to_law(
            event_type="sentencing",
            event_description="Sentencing hearing for offender",
        )

        # Should include s. 718
        section_718 = [l for l in laws if l.section_number == "718"]
        assert len(section_718) == 1

    def test_law_section_has_source_url(self):
        """All sections should have official source URLs."""
        adapter = JusticeLawsAdapter()

        sections = adapter.fetch_act_sections("Criminal Code")

        for section in sections:
            assert section.source_url
            assert "laws.justice.gc.ca" in section.source_url

    def test_law_section_has_jurisdiction(self):
        """All sections should have CA-FED jurisdiction."""
        adapter = JusticeLawsAdapter()

        sections = adapter.fetch_act_sections("Criminal Code")

        for section in sections:
            assert section.jurisdiction == "CA-FED"


class TestSaskatchewanLawAdapter:
    """Test Saskatchewan law adapter."""

    def test_adapter_initializes(self):
        """Adapter should initialize with default client."""
        adapter = SaskatchewanLawAdapter()
        assert adapter is not None
        assert adapter.BASE_URL == "https://publications.saskatchewan.ca"

    def test_fetch_police_act(self):
        """Should fetch Saskatchewan Police Act sections."""
        adapter = SaskatchewanLawAdapter()

        sections = adapter.fetch_police_act_sections()

        assert len(sections) > 0
        for section in sections:
            assert section.jurisdiction == "CA-SK"
            assert section.source == "Saskatchewan King's Printer"
            assert "Police Act" in section.law_title

    def test_fetch_correctional_services(self):
        """Should fetch Correctional Services Act sections."""
        adapter = SaskatchewanLawAdapter()

        sections = adapter.fetch_correctional_services_sections()

        assert len(sections) > 0
        for section in sections:
            assert section.jurisdiction == "CA-SK"
            assert "Correctional Services" in section.law_title

    def test_fetch_victims_of_crime(self):
        """Should fetch Victims of Crime Act sections."""
        adapter = SaskatchewanLawAdapter()

        sections = adapter.fetch_victims_of_crime_sections()

        assert len(sections) > 0
        for section in sections:
            assert section.jurisdiction == "CA-SK"
            assert "Victims of Crime" in section.law_title

    def test_get_law_by_citation_police(self):
        """Should lookup Police Act by citation."""
        adapter = SaskatchewanLawAdapter()

        section = adapter.get_law_by_citation("Saskatchewan Police Act, s. 5")

        assert section is not None
        assert "Police" in section.law_title

    def test_link_event_to_law_police(self):
        """Should link police events to Police Act."""
        adapter = SaskatchewanLawAdapter()

        laws = adapter.link_event_to_law(
            event_type="police_detention",
            event_description="Police officer detention incident",
        )

        police_sections = [l for l in laws if "Police" in l.law_title]
        assert len(police_sections) > 0

    def test_get_priority_laws(self):
        """Should return all priority laws."""
        adapter = SaskatchewanLawAdapter()

        laws = adapter.get_priority_laws()

        # Should include all three priority acts
        titles = [l.law_title for l in laws]
        assert any("Police" in t for t in titles)
        assert any("Correctional" in t for t in titles)
        assert any("Victims" in t for t in titles)

    def test_source_is_kings_printer(self):
        """Source should be Saskatchewan King's Printer."""
        adapter = SaskatchewanLawAdapter()

        sections = adapter.fetch_police_act_sections()

        for section in sections:
            assert "King's Printer" in section.source


class TestLawSectionStructure:
    """Test law section dataclass structure."""

    def test_federal_law_section_fields(self):
        """Federal sections should have all required fields."""
        section = LawSection(
            jurisdiction="CA-FED",
            source="Justice Laws",
            law_title="Criminal Code",
            law_type="act",
            chapter="R.S.C., 1985, c. C-46",
            section_number="515",
            section_heading="Judicial interim release",
            section_text="Order of release...",
            language="en",
            source_url="https://laws.justice.gc.ca/...",
            consolidation_date=None,
            raw_hash="abc123",
        )

        assert section.jurisdiction == "CA-FED"
        assert section.section_number == "515"
        assert len(section.raw_hash) > 0

    def test_provincial_law_section_fields(self):
        """Provincial sections should have all required fields."""
        section = SaskatchewanLawSection(
            jurisdiction="CA-SK",
            source="Saskatchewan King's Printer",
            law_title="Police Act",
            law_type="act",
            chapter="S.S. 2018, c. P-15.2",
            section_number="5",
            section_heading="Policing standards",
            section_text="The minister shall...",
            language="en",
            source_url="https://publications.saskatchewan.ca/...",
            consolidation_date=None,
            raw_hash="def456",
        )

        assert section.jurisdiction == "CA-SK"
        assert section.section_number == "5"

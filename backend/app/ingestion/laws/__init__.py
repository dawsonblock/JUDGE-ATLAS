"""Canadian law ingestion adapters.

Adapters for official Canadian legal sources:
1. Federal: Justice Laws Website XML
2. Saskatchewan: King's Printer / Freelaw
3. CanLII: Case law and legislation browser

All adapters store:
- jurisdiction (CA-FED, CA-SK, etc.)
- source_url
- consolidation_date
- raw_hash for audit trail
"""

from app.ingestion.laws.canada_federal_justice_xml import JusticeLawsAdapter
from app.ingestion.laws.canada_saskatchewan import SaskatchewanLawAdapter

__all__ = [
    "JusticeLawsAdapter",
    "SaskatchewanLawAdapter",
]

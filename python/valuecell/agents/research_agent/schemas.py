from dataclasses import dataclass
from pathlib import Path


@dataclass
class SECFilingMetadata:
    doc_type: str
    company: str
    period_of_report: str
    filing_date: str


@dataclass
class SECFilingResult:
    name: str
    path: Path
    metadata: SECFilingMetadata

import os
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

import aiofiles
from agno.agent import Agent
from agno.models.google import Gemini
from agno.models.openrouter import OpenRouter
from edgar import Company
from edgar.entity.filings import EntityFilings

from valuecell.utils.path import get_knowledge_path

from .knowledge import insert_md_file_to_knowledge
from .schemas import SECFilingMetadata, SECFilingResult


def _ensure_list(value: str | Sequence[str] | None) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)


def _parse_date(d: str | date | None) -> Optional[date]:
    if d is None:
        return None
    if isinstance(d, date):
        return d
    # try common formats
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(d, fmt).date()
        except ValueError:
            continue
    raise ValueError(
        f"Invalid date format: {d}. Expect YYYY-MM-DD, YYYY/MM/DD, or YYYYMMDD."
    )


async def _write_and_ingest(
    filings: Iterable,
    knowledge_dir: Path,
) -> List[SECFilingResult]:
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    results: List[SECFilingResult] = []
    for filing in filings:
        filing_date: str = filing.filing_date.strftime("%Y-%m-%d")
        period_of_report: str = getattr(filing, "period_of_report", "")
        # Convert to markdown; fall back to string if markdown unavailable
        try:
            content: str = filing.document.markdown()
        except Exception:
            try:
                content = str(filing.document)
            except Exception:
                content = ""
        doc_type: str = filing.form
        company_name: str = filing.company

        orig_doc = filing.document.document
        # build stable markdown filename using suffix replacement, keep base name only
        md_doc = Path(orig_doc).with_suffix(".md").name
        file_name = f"{doc_type}_{md_doc}"
        path = knowledge_dir / file_name
        metadata = SECFilingMetadata(
            doc_type=doc_type,
            company=company_name,
            period_of_report=period_of_report,
            filing_date=filing_date,
        )
        async with aiofiles.open(path, "w", encoding="utf-8") as file:
            await file.write(content)

        result = SECFilingResult(file_name, path, metadata)
        results.append(result)

        await insert_md_file_to_knowledge(
            name=file_name, path=path, metadata=metadata.__dict__
        )

    return results


async def fetch_periodic_sec_filings(
    cik_or_ticker: str,
    forms: List[str] | str = "10-Q",
    year: Optional[int | List[int]] = None,
    quarter: Optional[int | List[int]] = None,
    limit: int = 10,
):
    """Fetch periodic SEC filings (10-K/10-Q) and ingest into knowledge.

    - Designed for regular, scheduled reports with filing_date year/quarter filters (edgar API behavior).
    - If year is omitted, fetch latest filings via latest(limit) ordered by filing_date, constrained by forms. If quarter is provided, year must also be provided.

    Date concept guidance:
    - Filing date (filing_date): When the filing was submitted to the SEC. edgar filters by filing_date for year/quarter.
    - Period of report (period_of_report): The reporting period end date covered by the document (fiscal year/quarter-end). It may differ from filing_date.
    - Fiscal vs calendar: Users saying "Q3/FY" usually refer to period_of_report; however, the year/quarter parameters passed to edgar here filter by filing_date.

    Args:
        cik_or_ticker: CIK or ticker symbol (no quotes or backticks).
        forms: "10-K", "10-Q" or a list of these. Defaults to "10-Q".
        year: Single year or list of years to include (by filing_date). When omitted, the tool returns the latest filings using `limit`.
        quarter: Single quarter (1-4) or list of quarters (by filing_date). Requires `year` to be provided.
        limit: When `year` is omitted, number of latest filings to return (by filing_date). Defaults to 10.

    Returns:
        List[SECFilingResult]
    """
    req_forms = set(_ensure_list(forms)) or {"10-Q"}
    company = Company(cik_or_ticker)

    # If year is omitted, use latest(limit). Quarter without year is not supported.
    if year is None:
        if quarter is not None:
            raise ValueError(
                "quarter requires year to be specified for periodic filings"
            )
        filings = company.get_filings(form=list(req_forms)).latest(limit)
        if isinstance(filings, EntityFilings):
            items = list(filings)
        else:
            items = [filings]
        return await _write_and_ingest(items, Path(get_knowledge_path()))

    filings = company.get_filings(form=list(req_forms), year=year, quarter=quarter)

    return await _write_and_ingest(filings, Path(get_knowledge_path()))


async def fetch_event_sec_filings(
    cik_or_ticker: str,
    forms: List[str] | str = "8-K",
    start_date: Optional[str | date] = None,
    end_date: Optional[str | date] = None,
    limit: int = 10,
):
    """Fetch event-driven filings (e.g., 8-K, Forms 3/4/5) with optional date-range and limit.

    Args:
        cik_or_ticker: CIK or ticker symbol (no quotes or backticks).
        forms: One or more of ["8-K", "3", "4", "5"]. Defaults to "8-K".
        start_date: Inclusive start date (YYYY-MM-DD or date).
        end_date: Inclusive end date (YYYY-MM-DD or date).
        limit: Maximum number of filings to fetch after filtering. Defaults to 10.
    (Note: The tool will always ingest written markdown into the knowledge base.)

    Returns:
        List[SECFilingResult]
    """
    sd = _parse_date(start_date)
    ed = _parse_date(end_date)
    if sd and ed and sd > ed:
        raise ValueError("start_date cannot be after end_date")

    req_forms = set(_ensure_list(forms)) or {"8-K"}
    company = Company(cik_or_ticker)

    # If no date range specified, leverage edgar's latest(count) for efficiency
    if not sd and not ed:
        filings = company.get_filings(form=list(req_forms)).latest(limit)
        if isinstance(filings, EntityFilings):
            items = list(filings)
        else:
            items = [filings]
        return await _write_and_ingest(items, Path(get_knowledge_path()))

    # Otherwise, fetch and filter by filing_date range
    filings = company.get_filings(form=list(req_forms))
    if isinstance(filings, EntityFilings):
        items = list(filings)
    else:
        items = [filings]

    filtered: List = []
    for f in items:
        f_date = f.filing_date
        if sd and f_date < sd:
            continue
        if ed and f_date > ed:
            continue
        filtered.append(f)

    # Sort desc and apply limit
    filtered.sort(key=lambda f: f.filing_date, reverse=True)
    if limit is not None and limit > 0:
        filtered = filtered[:limit]

    return await _write_and_ingest(filtered, Path(get_knowledge_path()))


async def web_search(query: str) -> str:
    """Search web for the given query and return a summary of the top results.

    Args:
        query: The search query string.

    Returns:
        A summary of the top search results.
    """

    if os.getenv("WEB_SEARCH_PROVIDER", "google").lower() == "google" and os.getenv(
        "GOOGLE_API_KEY"
    ):
        return await _web_search_google(query)

    model = OpenRouter(id="perplexity/sonar", max_tokens=None)
    response = await Agent(model=model).arun(query)
    return response.content


async def _web_search_google(query: str) -> str:
    """Search Google for the given query and return a summary of the top results.

    Args:
        query: The search query string.

    Returns:
        A summary of the top search results.
    """
    model = Gemini(id="gemini-2.5-flash", search=True)
    response = await Agent(model=model).arun(query)
    return response.content

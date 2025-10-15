from pathlib import Path
from typing import List, Optional

import aiofiles
from edgar import Company
from edgar.entity.filings import EntityFilings

from valuecell.utils.path import get_knowledge_path

from .knowledge import insert_md_file_to_knowledge
from .schemas import SECFilingMetadata, SECFilingResult


async def fetch_sec_filings(
    cik_or_ticker: str,
    form: List[str] | str = "10-Q",
    year: Optional[int | List[int]] = None,
    quarter: Optional[int | List[int]] = None,
):
    """Fetch SEC filings for a given company.
    If year and quarter are provided, filter filings accordingly. If not, fetch the latest filings.

    Args:
        cik_or_ticker (str): CIK or ticker symbol of the company. Never introduce backticks, quotes, or spaces.
        form (List[str] | str, optional): Type of SEC filing form to fetch.
            - Defaults to "10-Q". Can be a list of forms (e.g. ["10-K", "10-Q"]).
            - Choices explained:
                - "10-K": Annual report
                - "10-Q": Quarterly report
                - "8-K": Current report for unscheduled material events or corporate changes
        year (Optional[int | List[int]], optional): Year or list of years to filter filings. Defaults to None.
        quarter (Optional[int | List[int]], optional): Quarter or list of quarters to filter filings. Defaults to None.

    Returns:
        List[Tuple[str, Path, dict]]: A list of tuples containing the name, path, and metadata of each fetched filing.
    """
    company = Company(cik_or_ticker)
    if year or quarter:
        filings = company.get_filings(form=form, year=year, quarter=quarter)
    else:
        filings = company.get_filings(form=form).latest()
        if not isinstance(filings, EntityFilings):
            filings = [filings]

    res = []
    for filing in filings:
        filing_date: str = filing.filing_date.strftime("%Y-%m-%d")
        period_of_report: str = filing.period_of_report
        content: str = filing.document.markdown()
        doc_type: str = filing.form
        company_name: str = filing.company

        orig_doc = filing.document.document
        md_doc = orig_doc.replace(filing.document.extension, ".md")
        file_name = f"{doc_type}_{md_doc}"
        path = Path(get_knowledge_path()) / file_name
        metadata = SECFilingMetadata(
            doc_type=doc_type,
            company=company_name,
            period_of_report=period_of_report,
            filing_date=filing_date,
        )
        async with aiofiles.open(path, "w") as file:
            await file.write(content)

        sec_filing_result = SECFilingResult(file_name, path, metadata)
        res.append(sec_filing_result)
        await insert_md_file_to_knowledge(
            name=file_name, path=path, metadata=metadata.__dict__
        )

    return res

from pathlib import Path
from typing import List, Optional

from edgar import Company
from edgar.enums import FormType


async def fetch_sec_filings(
    cik_or_ticker: str,
    form: FormType = FormType.QUARTERLY_REPORT,
    year: Optional[int | List[int]] = None,
    quarter: Optional[int | List[int]] = None,
):
    company = Company(cik_or_ticker)
    filings = company.get_filings(form=form, year=year, quarter=quarter)

    for filing in filings:
        filing_date = filing.filing_date.strftime("%Y-%m-%d")
        period_of_report = filing.period_of_report
        content = filing.document.markdown()

        path = Path(f"./{filing.company}-{filing_date}-{filing.form}.md")
        path.write_text(content)
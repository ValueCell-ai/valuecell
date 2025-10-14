from pathlib import Path
from typing import List, Optional

import aiofiles
from edgar import Company
from edgar.enums import FormType

from valuecell.utils.path import get_knowledge_path


async def fetch_sec_filings(
    cik_or_ticker: str,
    form: FormType = FormType.QUARTERLY_REPORT,
    year: Optional[int | List[int]] = None,
    quarter: Optional[int | List[int]] = None,
):
    company = Company(cik_or_ticker)
    filings = company.get_filings(form=form, year=year, quarter=quarter)

    res = []
    for filing in filings:
        filing_date: str = filing.filing_date.strftime("%Y-%m-%d")
        period_of_report: str = filing.period_of_report
        content: str = filing.document.markdown()

        name = f"{filing.company}-{filing_date}-{filing.form}"
        path = Path(get_knowledge_path()) / f"{name}.md"
        metadata = {
            "doc_type": filing.form,
            "company": filing.company,
            "period_of_report": period_of_report,
            "filing_date": filing_date,
        }
        async with aiofiles.open(path, "w") as file:
            await file.write(content)

        res.append((name, path, metadata))

    return res

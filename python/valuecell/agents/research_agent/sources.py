import os
import re
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

import aiofiles
import aiohttp
from agno.agent import Agent
from edgar import Company
from edgar.entity.filings import EntityFilings
from loguru import logger

from valuecell.agents.sources import (
    get_person_detail,
    get_project_detail,
    get_vc_detail,
    search_people,
    search_projects,
    search_vcs,
)
from valuecell.utils.path import get_knowledge_path

from .knowledge import insert_md_file_to_knowledge, insert_pdf_file_to_knowledge
from .schemas import (
    AShareFilingMetadata,
    AShareFilingResult,
    SECFilingMetadata,
    SECFilingResult,
)


def _ensure_list(value: str | Sequence[str] | None) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)


def _extract_quarter_from_title(title: str) -> Optional[int]:
    """Extract quarter number from announcement title

    Args:
        title: Announcement title string

    Returns:
        Quarter number (1-4) if found, None otherwise
    """
    if not title:
        return None

    # Common patterns for quarterly reports in Chinese titles
    quarter_patterns = [
        (r"第一季度|一季度|1季度|Q1", 1),
        (r"第二季度|二季度|2季度|Q2|半年度|中期", 2),  # Semi-annual is often Q2
        (r"第三季度|三季度|3季度|Q3", 3),
        (r"第四季度|四季度|4季度|Q4|年度报告|年报", 4),  # Annual is often Q4
    ]

    for pattern, quarter in quarter_patterns:
        if re.search(pattern, title, re.IGNORECASE):
            return quarter

    return None


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

    This function uses the centralized configuration system to create model instances.
    It supports multiple search providers:
    - Google (Gemini with search enabled) - when WEB_SEARCH_PROVIDER=google and GOOGLE_API_KEY is set
    - Perplexity (via OpenRouter) - default fallback

    Args:
        query: The search query string.

    Returns:
        A summary of the top search results.
    """
    from valuecell.utils.model import create_model_with_provider

    # Check which provider to use based on environment configuration
    if os.getenv("WEB_SEARCH_PROVIDER", "google").lower() == "google" and os.getenv(
        "GOOGLE_API_KEY"
    ):
        return await _web_search_google(query)

    # Use Perplexity Sonar via OpenRouter for web search
    # Perplexity models are optimized for web search and real-time information
    model = create_model_with_provider(
        provider="openrouter",
        model_id="perplexity/sonar",
        max_tokens=None,
    )
    response = await Agent(model=model).arun(query)
    return response.content


async def _web_search_google(query: str) -> str:
    """Search Google for the given query and return a summary of the top results.

    Uses Google Gemini with search grounding enabled for real-time web information.

    Args:
        query: The search query string.

    Returns:
        A summary of the top search results.
    """
    from valuecell.utils.model import create_model_with_provider

    # Use Google Gemini with search enabled
    # The search=True parameter enables Google Search grounding for real-time information
    model = create_model_with_provider(
        provider="google",
        model_id="gemini-2.5-flash",
        search=True,  # Enable Google Search grounding
    )
    response = await Agent(model=model).arun(query)
    return response.content


def _normalize_stock_code(stock_code: str) -> str:
    """Normalize stock code format"""
    # Remove possible prefixes and suffixes, keep only digits
    code = re.sub(r"[^\d]", "", stock_code)
    # Ensure it's a 6-digit number
    if len(code) == 6:
        return code
    elif len(code) < 6:
        return code.zfill(6)
    else:
        return code[:6]


async def _write_and_ingest_ashare(
    filings_data: List[dict],
    knowledge_dir: Path,
) -> List[AShareFilingResult]:
    """Write A-share filing data to files and import to knowledge base"""
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    results: List[AShareFilingResult] = []

    for filing_data in filings_data:
        # Build file name
        stock_code = filing_data["stock_code"]
        doc_type = filing_data["doc_type"]
        period = filing_data["period_of_report"]

        # Get PDF URL from filing data
        pdf_url = filing_data.get("pdf_url", "")

        # Create metadata
        metadata = AShareFilingMetadata(
            doc_type=doc_type,
            company=filing_data["company"],
            stock_code=stock_code,
            market=filing_data["market"],
            period_of_report=period,
            filing_date=filing_data["filing_date"],
            announcement_title=filing_data.get("announcement_title", ""),
        )

        # Create result object
        file_name = f"{stock_code}_{doc_type}_{period}.pdf"
        result = AShareFilingResult(name=file_name, path=pdf_url, metadata=metadata)
        results.append(result)

        # Import to knowledge base - use PDF URL if available
        await insert_pdf_file_to_knowledge(url=pdf_url, metadata=metadata.__dict__)

    return results


async def _get_correct_orgid(
    stock_code: str, session: aiohttp.ClientSession
) -> Optional[str]:
    """Get correct orgId for a stock code from CNINFO search API

    Args:
        stock_code: Stock code (e.g., "002460")
        session: aiohttp session

    Returns:
        Optional[str]: The correct orgId, or None if not found
    """
    search_url = "http://www.cninfo.com.cn/new/information/topSearch/query"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Host": "www.cninfo.com.cn",
        "Origin": "http://www.cninfo.com.cn",
        "Referer": "http://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search&lastPage=index",
        "X-Requested-With": "XMLHttpRequest",
    }

    search_data = {"keyWord": stock_code}

    try:
        async with session.post(
            search_url, headers=headers, data=search_data
        ) as response:
            if response.status == 200:
                result = await response.json()

                if result and len(result) > 0:
                    # Find the exact match for the stock code
                    for company_info in result:
                        if company_info.get("code") == stock_code:
                            return company_info.get("orgId")

                    # If no exact match, return the first result's orgId
                    return result[0].get("orgId")

    except Exception as e:
        print(f"Error getting orgId for {stock_code}: {e}")

    return None


async def _fetch_cninfo_data(
    stock_code: str,
    report_types: List[str],
    years: List[int],
    quarters: List[int],
    limit: int,
) -> List[dict]:
    """Fetch real A-share filing data from CNINFO API

    Args:
        stock_code: Normalized stock code
        report_types: List of report types
        years: List of years
        quarters: List of quarters (1-4), empty list means all quarters
        limit: Maximum number of records to fetch

    Returns:
        List[dict]: List of filing data
    """

    # CNINFO API configuration
    base_url = "http://www.cninfo.com.cn/new/hisAnnouncement/query"

    # Request headers configuration
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Host": "www.cninfo.com.cn",
        "Origin": "http://www.cninfo.com.cn",
        "Referer": "http://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search&lastPage=index",
        "X-Requested-With": "XMLHttpRequest",
    }

    # Report type mapping (supports both English and Chinese for backward compatibility)
    category_mapping = {
        "annual": "category_ndbg_szsh",
        "semi-annual": "category_bndbg_szsh",
        "quarterly": "category_sjdbg_szsh",
    }

    # Determine exchange
    column = "szse" if stock_code.startswith(("000", "002", "300")) else "sse"

    filings_data = []
    current_year = datetime.now().year
    target_years = (
        years if years else [current_year, current_year - 1, current_year - 2]
    )

    async with aiohttp.ClientSession() as session:
        # Get correct orgId first
        org_id = await _get_correct_orgid(stock_code, session)
        if not org_id:
            print(f"Warning: Could not get orgId for stock {stock_code}")
            return []

        # Determine plate based on stock code
        if stock_code.startswith(("000", "002", "300")):
            plate = "sz"
        else:
            plate = "sh"

        for report_type in report_types:
            if len(filings_data) >= limit:
                break

            category = category_mapping.get(report_type, "category_ndbg_szsh")

            # Build time range
            for target_year in target_years:
                if len(filings_data) >= limit:
                    break

                # Set search time range
                start_date = f"{target_year}-01-01"
                end_date = f"{target_year + 1}-01-01"
                se_date = f"{start_date}~{end_date}"

                form_data = {
                    "pageNum": "1",
                    "pageSize": "30",
                    "column": column,
                    "tabName": "fulltext",
                    "plate": plate,
                    "stock": f"{stock_code},{org_id}",
                    "searchkey": "",
                    "secid": "",
                    "category": f"{category};",
                    "trade": "",
                    "seDate": se_date,
                    "sortName": "",
                    "sortType": "",
                    "isHLtitle": "true",
                }

                try:
                    async with session.post(
                        base_url, headers=headers, data=form_data
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            announcements = result.get("announcements", [])

                            if announcements is None:
                                continue

                            for announcement in announcements:
                                if len(filings_data) >= limit:
                                    break

                                announcement_title = announcement.get(
                                    "announcementTitle", ""
                                )

                                # Apply quarter filtering for quarterly reports
                                if report_type == "quarterly" and quarters:
                                    # Extract quarter from announcement title
                                    quarter_from_title = _extract_quarter_from_title(
                                        announcement_title
                                    )
                                    if (
                                        quarter_from_title
                                        and quarter_from_title not in quarters
                                    ):
                                        continue  # Skip this announcement if quarter doesn't match

                                # Extract filing information
                                filing_info = {
                                    "stock_code": announcement.get(
                                        "secCode", stock_code
                                    ),
                                    "company": announcement.get("secName", ""),
                                    "market": "SZSE" if column == "szse" else "SSE",
                                    "doc_type": report_type,
                                    "period_of_report": f"{target_year}",
                                    "filing_date": announcement.get("adjunctUrl", "")[
                                        10:20
                                    ]
                                    if announcement.get("adjunctUrl")
                                    else f"{target_year}-04-30",
                                    "announcement_id": announcement.get(
                                        "announcementId", ""
                                    ),
                                    "announcement_title": announcement_title,
                                    "org_id": announcement.get("orgId", ""),
                                    "content": "",  # Will fetch detailed content in subsequent steps
                                }

                                # Fetch PDF URL
                                pdf_url = await _fetch_announcement_content(
                                    session, filing_info
                                )
                                filing_info["pdf_url"] = pdf_url

                                filings_data.append(filing_info)

                except Exception as e:
                    print(
                        f"Error fetching {stock_code} {report_type} {target_year} data: {e}"
                    )
                    continue

    return filings_data


async def _fetch_announcement_content(
    session: aiohttp.ClientSession, filing_info: dict
) -> str:
    """Fetch PDF URL from CNINFO API

    Args:
        session: aiohttp session
        filing_info: Filing information dictionary

    Returns:
        PDF URL string, or empty string if not available
    """
    try:
        # CNINFO announcement detail API
        detail_url = "http://www.cninfo.com.cn/new/announcement/bulletin_detail"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        }

        params = {
            "announceId": filing_info.get("announcement_id", ""),
            "flag": "true",
            "announceTime": filing_info.get("filing_date", ""),
        }

        async with session.post(detail_url, headers=headers, params=params) as response:
            if response.status == 200:
                result = await response.json()

                # Extract PDF link with fallback options
                pdf_url = result.get("fileUrl", "")
                if not pdf_url:
                    # Fallback: construct URL from adjunctUrl if available
                    announcement_data = result.get("announcement", {})
                    adjunct_url = announcement_data.get("adjunctUrl", "")
                    if adjunct_url:
                        pdf_url = f"http://static.cninfo.com.cn/{adjunct_url}"

                return pdf_url

    except Exception as e:
        print(f"Error fetching announcement details: {e}")

    # Return empty string if failed
    return ""


async def fetch_ashare_filings(
    stock_code: str,
    report_types: List[str] | str = "annual",
    year: Optional[int | List[int]] = None,
    quarter: Optional[int | List[int]] = None,
    limit: int = 10,
) -> List[AShareFilingResult]:
    """Fetch A-share filing data from CNINFO and import to knowledge base

    Args:
        stock_code: Stock code (e.g.: 000001, 600036, etc.)
        report_types: Report types (ENGLISH ONLY). Supported values: "annual", "semi-annual", "quarterly".
                     Default is "annual". Chinese parameters are NOT supported.
        year: Year filter, can be a single year or list of years. If not provided, fetch latest reports
        quarter: Quarter filter (1-4), can be a single quarter or list of quarters.
                Only applicable when report_types includes "quarterly". Requires year to be provided.
        limit: Maximum number of records to fetch, default 10

    Returns:
        List[AShareFilingResult]: List of A-share filing results

    Raises:
        ValueError: If report_types contains Chinese parameters or invalid values,
                   or if quarter is provided without year

    Examples:
        # Fetch latest annual report of Ping An Bank
        await fetch_ashare_filings("000001", "annual", limit=1)

        # Fetch 2024 annual and semi-annual reports of Kweichow Moutai
        await fetch_ashare_filings("600519", ["annual", "semi-annual"], year=2024)

        # Fetch 2024 Q3 quarterly report of Kweichow Moutai
        await fetch_ashare_filings("600519", "quarterly", year=2024, quarter=3)

        # Fetch 2024 Q1 and Q3 quarterly reports of Kweichow Moutai
        await fetch_ashare_filings("600519", "quarterly", year=2024, quarter=[1, 3])

        # This will raise ValueError (Chinese parameters not supported):
        # await fetch_ashare_filings("600519", "年报")  # DON'T DO THIS
    """

    # Normalize stock code
    normalized_code = _normalize_stock_code(stock_code)

    # Normalize report types
    report_types_list = _ensure_list(report_types)
    if not report_types_list:
        report_types_list = ["annual"]

    # Validate quarter parameter
    if quarter is not None:
        if year is None:
            raise ValueError("Quarter parameter requires year to be provided")
        if "quarterly" not in report_types_list:
            raise ValueError(
                "Quarter parameter is only applicable when report_types includes 'quarterly'"
            )

    # Normalize years
    years_list = []
    if year is not None:
        if isinstance(year, int):
            years_list = [year]
        else:
            years_list = list(year)

    # Normalize quarters
    quarters_list = []
    if quarter is not None:
        if isinstance(quarter, int):
            quarters_list = [quarter]
        else:
            quarters_list = list(quarter)

        # Validate quarter values
        for q in quarters_list:
            if not isinstance(q, int) or q < 1 or q > 4:
                raise ValueError(f"Quarter must be between 1 and 4, got: {q}")

    # Fetch real data from CNINFO
    filings_data = await _fetch_cninfo_data(
        normalized_code, report_types_list, years_list, quarters_list, limit
    )

    # Write to files and import to knowledge base
    knowledge_dir = Path(get_knowledge_path())
    return await _write_and_ingest_ashare(filings_data, knowledge_dir)


# ============================================================================
# Crypto Project Data Tools (RootData)
# ============================================================================


async def search_crypto_projects(
    query: str,
    limit: int = 10,
) -> str:
    """Search cryptocurrency projects on RootData by keyword.

    Use this tool when users ask about cryptocurrency projects, tokens, or blockchain ecosystems.
    Examples: "What is Ethereum?", "Tell me about DeFi projects", "Find projects related to AI"

    Args:
        query: Search keyword (project name, token symbol, or category like "DeFi", "AI", "GameFi")
        limit: Maximum number of results to return (default: 5, max recommended: 10)

    Returns:
        JSON string with project information including name, description, tags, and key metrics.
    """

    logger.info(f"Searching crypto projects for: {query}")

    try:
        projects = await search_projects(query, limit=limit, use_playwright=True)

        if not projects:
            return f"No cryptocurrency projects found for query: {query}"

        logger.debug(f"Search crypto projects get {len(projects)} results.")

        for i, proj in enumerate(projects, 1):
            proj = await get_project_detail(proj.id)
            if not proj:
                logger.warning(f"No project found with ID: {proj.id}")
                continue
            return proj.model_dump_json(exclude_none=True)

    except Exception as e:
        logger.error(f"Error searching crypto projects: {e}")
        return f"Error searching cryptocurrency projects: {str(e)}"


async def search_crypto_vcs(
    query: str,
    limit: int = 5,
) -> str:
    """Search venture capital firms and crypto investors on RootData.

    Use this tool when users ask about VCs, investment firms, or crypto investors.
    Examples: "Who invested in Ethereum?", "Find VCs focused on DeFi", "Tell me about a16z crypto"

    Args:
        query: Search keyword (VC name, investment focus, or category)
        limit: Maximum number of results to return (default: 5, max recommended: 10)

    Returns:
        Formatted string with VC information including name, description, portfolio, and links.
    """

    logger.info(f"Searching crypto VCs for: {query}")

    try:
        vcs = await search_vcs(query, limit=limit, use_playwright=True)

        if not vcs:
            return f"No venture capital firms found for query: {query}"

        logger.debug(f"Search crypto VCs get {len(vcs)} results.")

        for i, vc in enumerate(vcs, 1):
            vc = await get_vc_detail(vc.id)
            if not vc:
                logger.warning(f"No VC found with ID: {vc.id}")
                continue
            return vc.model_dump_json()

    except Exception as e:
        logger.error(f"Error searching crypto VCs: {e}")
        return f"Error searching venture capital firms: {str(e)}"


async def search_crypto_people(
    query: str,
    limit: int = 5,
) -> str:
    """Search crypto industry people on RootData (founders, executives, investors).

    Use this tool when users ask about people in crypto, founders, or industry leaders.
    Examples: "Who is Vitalik Buterin?", "Find founders of Ethereum", "Tell me about crypto investors"

    Args:
        query: Search keyword (person name, role, or organization)
        limit: Maximum number of results to return (default: 5, max recommended: 10)

    Returns:
        Formatted string with person information including name, title, projects, and links.
    """

    logger.info(f"Searching crypto people for: {query}")

    try:
        people = await search_people(query, limit=limit, use_playwright=True)

        if not people:
            return f"No people found for query: {query}"

        logger.debug(f"Search crypto people get {len(people)} results.")

        for i, person in enumerate(people, 1):
            person = await get_person_detail(person.id)
            if not person:
                logger.warning(f"No person found with ID: {person.id}")
                continue
            return person.model_dump_json()

    except Exception as e:
        logger.error(f"Error searching crypto people: {e}")
        return f"Error searching people: {str(e)}"

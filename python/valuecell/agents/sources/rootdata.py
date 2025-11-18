"""
RootData API Client - Cryptocurrency projects, VCs and people data fetching tool

Extracts comprehensive data from RootData using Playwright browser automation to access
server-side rendered (SSR) data from window.__NUXT__ object.

Features:
---------
- **Rich Project Details**: Get 40+ fields including price, market cap, supply,
  historical prices, contracts, social links, and community sentiment
- **Smart Search**: Search projects by name or keyword with browser interaction
- **VC & People Data**: Search and retrieve venture capital firms and people information
- **Fallback Support**: Automatic fallback to HTML parsing if Playwright unavailable

Quick Start:
------------
```python
import asyncio
from valuecell.agents.sources.rootdata import (
    search_projects,
    get_project_detail
)

async def main():
    # Search for projects
    projects = await search_projects("Aster", limit=10)
    for project in projects:
        print(f"{project.name} ({project.token_symbol})")

    # Get detailed information
    if projects:
        detail = await get_project_detail(projects[0].id)
        print(f"Price: ${detail.token_price}")
        print(f"Market Cap: ${detail.market_cap}")
        print(f"24h Change: {detail.price_change_24h}%")
        print(f"Ecosystems: {', '.join(detail.ecosystems)}")
        print(f"Contracts: {detail.contracts}")
        print(f"Community Hold: {detail.hold_percentage}%")

asyncio.run(main())
```

Requirements:
-------------
- playwright: `pip install playwright && playwright install chromium`
- httpx: `pip install httpx`
- beautifulsoup4: `pip install beautifulsoup4`
"""

import re
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup
from loguru import logger
from pydantic import BaseModel, Field

# ============================================================================
# Data Models
# ============================================================================


class RootDataProject(BaseModel):
    """Cryptocurrency project information"""

    # Basic Info
    id: int
    name: str
    brief_intro: str = Field(default="", description="Brief introduction")
    description: str = Field(default="", description="Detailed description")
    image_url: Optional[str] = Field(None, description="Project logo")
    founded_year: Optional[int] = Field(None, description="Founded year")

    # Status
    status: Optional[str] = Field(None, description="Project status (Active/Inactive)")
    level: Optional[int] = Field(None, description="Project level/tier")
    rank: Optional[int] = Field(None, description="Project rank")

    # Tags and Categories
    tags: List[str] = Field(default_factory=list, description="Project tags")
    ecosystems: List[str] = Field(
        default_factory=list, description="Blockchain ecosystems"
    )

    # Token Information
    token_symbol: Optional[str] = Field(None, description="Token symbol")
    token_price: Optional[float] = Field(None, description="Current token price")
    market_cap: Optional[float] = Field(None, description="Market capitalization")
    fdv: Optional[float] = Field(None, description="Fully diluted valuation")
    volume_24h: Optional[float] = Field(None, description="24h trading volume")
    volume_change_24h: Optional[float] = Field(None, description="24h volume change")

    # Supply Information
    circulating_supply: Optional[float] = Field(None, description="Circulating supply")
    total_supply: Optional[float] = Field(None, description="Total supply")
    max_supply: Optional[float] = Field(None, description="Maximum supply")

    # Price Changes
    price_change_1h: Optional[float] = Field(None, description="1h price change %")
    price_change_24h: Optional[float] = Field(None, description="24h price change %")
    price_change_7d: Optional[float] = Field(None, description="7d price change %")
    price_change_30d: Optional[float] = Field(None, description="30d price change %")
    price_change_60d: Optional[float] = Field(None, description="60d price change %")

    # Historical Prices
    ath: Optional[float] = Field(None, description="All-time high price")
    ath_date: Optional[str] = Field(None, description="All-time high date")
    atl: Optional[float] = Field(None, description="All-time low price")
    atl_date: Optional[str] = Field(None, description="All-time low date")

    # Contract Information
    contracts: List[Dict[str, str]] = Field(
        default_factory=list, description="Smart contract addresses and chains"
    )

    # Social Links
    website: Optional[str] = Field(None, description="Official website")
    twitter: Optional[str] = Field(None, description="Twitter/X account")
    discord: Optional[str] = Field(None, description="Discord server")
    telegram: Optional[str] = Field(None, description="Telegram group")
    github: Optional[str] = Field(None, description="GitHub repository")

    # External Links
    coingecko_url: Optional[str] = Field(None, description="CoinGecko URL")
    coinmarketcap_url: Optional[str] = Field(None, description="CoinMarketCap URL")
    defillama_url: Optional[str] = Field(None, description="DefiLlama URL")

    # Community Sentiment
    hold_percentage: Optional[float] = Field(
        None, description="Percentage of users holding"
    )
    fud_percentage: Optional[float] = Field(
        None, description="Percentage of users FUDing"
    )

    # Special Flags
    is_rootdata_list: Optional[bool] = Field(
        None, description="In RootData featured list"
    )
    is_rootdata_list_2025: Optional[bool] = Field(
        None, description="In RootData 2025 list"
    )

    # Legacy fields for backward compatibility
    members: List[str] = Field(
        default_factory=list, description="Team members (deprecated)"
    )

    class Config:
        populate_by_name = True


class RootDataVC(BaseModel):
    """Venture Capital / Investment firm information"""

    id: int
    name: str
    brief_intro: str = Field(default="", description="Brief introduction")
    description: str = Field(default="", description="Detailed description")
    tags: List[str] = Field(default_factory=list, description="Investment focus tags")
    website: Optional[str] = Field(None, description="Website URL")
    twitter: Optional[str] = Field(None, description="Twitter account")
    image_url: Optional[str] = Field(None, description="Logo URL")
    founded_year: Optional[int] = Field(None, description="Founded year")
    portfolio_count: Optional[int] = Field(
        None, description="Number of portfolio companies"
    )
    total_investments: Optional[int] = Field(
        None, description="Total number of investments"
    )

    class Config:
        populate_by_name = True


class RootDataPerson(BaseModel):
    """Person information (founders, executives, investors)"""

    id: int
    name: str
    title: Optional[str] = Field(None, description="Job title or role")
    brief_intro: str = Field(default="", description="Brief introduction")
    description: str = Field(default="", description="Detailed description")
    tags: List[str] = Field(default_factory=list, description="Role/expertise tags")
    twitter: Optional[str] = Field(None, description="Twitter account")
    linkedin: Optional[str] = Field(None, description="LinkedIn profile")
    image_url: Optional[str] = Field(None, description="Profile picture URL")
    projects: List[str] = Field(default_factory=list, description="Associated projects")
    current_organization: Optional[str] = Field(
        None, description="Current organization"
    )

    class Config:
        populate_by_name = True


# ============================================================================
# Simple HTML Parser Functions
# ============================================================================


async def fetch_page_html(url: str) -> str:
    """Fetch HTML content from a URL"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                return response.text
            else:
                logger.warning(f"Failed to fetch {url}: status {response.status_code}")
                return ""
        except Exception as e:
            logger.warning(f"Error fetching {url}: {e}")
            return ""


def extract_project_id_from_url(url: str) -> Optional[int]:
    """Extract project ID from RootData URL

    Example: https://www.rootdata.com/Projects/detail/Ethereum?k=MTI%3D
    The 'k' parameter is base64-encoded ID
    """
    import base64

    match = re.search(r"[?&]k=([^&]+)", url)
    if match:
        try:
            encoded_id = match.group(1).replace("%3D", "=")
            decoded = base64.b64decode(encoded_id).decode("utf-8")
            return int(decoded)
        except Exception as e:
            logger.warning(f"Failed to decode project ID: {e}")
    return None


async def get_project_from_page(
    project_id_or_url: str | int,
) -> Optional[RootDataProject]:
    """
    Get project information by scraping the project detail page

    Args:
        project_id_or_url: Project ID (int) or full URL (str)

    Returns:
        RootDataProject or None if failed

    Examples:
        # By ID
        project = await get_project_from_page(12)  # Ethereum

        # By URL
        project = await get_project_from_page("https://www.rootdata.com/Projects/detail/Ethereum?k=MTI%3D")
    """
    # Construct URL
    if isinstance(project_id_or_url, int):
        import base64

        encoded_id = base64.b64encode(str(project_id_or_url).encode()).decode()
        url = f"https://www.rootdata.com/Projects/detail/Project?k={encoded_id}"
    else:
        url = project_id_or_url
        project_id_or_url = extract_project_id_from_url(url) or 0

    logger.info(f"Fetching project page: {url}")

    html = await fetch_page_html(url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    try:
        # Extract project data from page
        # Note: This is a basic implementation. Actual selectors may need adjustment
        # based on RootData's HTML structure

        name = ""
        h1 = soup.find("h1")
        if h1:
            name = h1.text.strip()

        token_symbol = ""
        h3 = soup.find("h3")
        if h3:
            token_symbol = h3.text.strip()

        brief_intro = ""
        description = ""
        paras = soup.find_all("p")
        for p in paras:
            text = p.text.strip()
            if len(text) > 20:  # Likely description text
                if not brief_intro:
                    brief_intro = text
                elif len(text) > len(description):
                    description = text

        # Extract tags
        tags = []
        tag_elements = soup.find_all(class_=re.compile(r"tag|label", re.I))
        for tag_el in tag_elements:
            tag_text = tag_el.text.strip()
            if tag_text and len(tag_text) < 30:  # Reasonable tag length
                tags.append(tag_text)

        # Extract links
        website = None
        twitter = None
        links = soup.find_all("a", href=True)
        for link in links:
            href = link["href"]
            if "twitter.com" in href or "x.com" in href:
                twitter = href.split("/")[-1]
            elif href.startswith("http") and "rootdata.com" not in href:
                if not website:
                    website = href

        project = RootDataProject(
            id=project_id_or_url,
            name=name,
            brief_intro=brief_intro,
            description=description,
            tags=list(set(tags))[:10],  # Deduplicate and limit
            token_symbol=token_symbol,
            twitter=twitter,
            website=website,
        )

        logger.info(f"Successfully extracted project: {name}")
        return project

    except Exception as e:
        logger.warning(f"Failed to parse project page: {e}")
        return None


# ============================================================================
# Recommendation: Use a proper web scraping service or browser automation
# ============================================================================


async def get_project_with_playwright(project_id: int) -> Optional[RootDataProject]:
    """
    Get detailed project information using Playwright to access server-side rendered data

    This method extracts data from window.__NUXT__ which contains complete project information
    including price, market cap, supply, social links, and more.

    Args:
        project_id: Project ID

    Returns:
        RootDataProject with comprehensive data or None if failed

    Example:
        project = await get_project_with_playwright(1179)  # Ripae project
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.warning("Playwright not installed. Install with: pip install playwright")
        return None

    import base64

    encoded_id = base64.b64encode(str(project_id).encode()).decode()
    url = f"https://www.rootdata.com/Projects/detail/Project?k={encoded_id}"

    logger.info(f"Fetching project {project_id} with Playwright: {url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(1000)

            # Extract data from window.__NUXT__
            project_data = await page.evaluate("""() => {
                if (!window.__NUXT__ || !window.__NUXT__.data) {
                    return null;
                }
                
                const nuxtArray = window.__NUXT__.data;
                
                // Find the detail object
                for (let i = 0; i < nuxtArray.length; i++) {
                    const item = nuxtArray[i];
                    if (item && item.detail && item.detail.id) {
                        return item.detail;
                    }
                }
                
                return null;
            }""")

            await browser.close()

            if not project_data:
                logger.warning(f"No project data found for ID: {project_id}")
                return None

            # Parse the data into RootDataProject
            project = _parse_project_from_nuxt_data(project_data)
            logger.info(f"Successfully extracted project: {project.name}")
            return project

        except Exception as e:
            logger.warning(f"Playwright scraping failed: {e}")
            await browser.close()
            return None


def _parse_project_from_nuxt_data(data: Dict[str, Any]) -> RootDataProject:
    """
    Parse project data from window.__NUXT__ format to RootDataProject

    Args:
        data: Raw data from window.__NUXT__.data[x].detail

    Returns:
        RootDataProject instance
    """

    # Helper to extract multilingual text
    def get_text(field):
        if isinstance(field, dict):
            return field.get("en_value") or field.get("cn_value") or ""
        return str(field) if field else ""

    # Helper to parse float safely
    def parse_float(value):
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    # Extract name
    name = get_text(data.get("name", ""))

    # Extract tags
    tags = []
    tag_list = data.get("tagList", [])
    if isinstance(tag_list, list):
        for tag in tag_list:
            if isinstance(tag, dict) and "name" in tag:
                tag_name = get_text(tag["name"])
                if tag_name:
                    tags.append(tag_name)

    # Extract ecosystems
    ecosystems = []
    sj_list = data.get("sjList", [])
    if isinstance(sj_list, list):
        for eco in sj_list:
            if isinstance(eco, dict) and "name" in eco:
                ecosystems.append(str(eco["name"]))

    # Extract contracts
    contracts = []
    contract_list = data.get("contracts", [])
    if isinstance(contract_list, list):
        for contract in contract_list:
            if isinstance(contract, dict):
                contracts.append(
                    {
                        "address": contract.get("contractAddress", ""),
                        "chain": contract.get("contractPlatform", ""),
                        "explorer_url": contract.get("contractExplorerUrl", ""),
                    }
                )

    # Determine status
    status = None
    operate_status = data.get("operateStatus")
    if operate_status == 1:
        status = "Active"
    elif operate_status == 2:
        status = "Inactive"

    # Calculate sentiment percentages
    hold_num = parse_float(data.get("holdNum"))
    fud_num = parse_float(data.get("fudNum"))
    hold_percentage = None
    fud_percentage = None
    if hold_num is not None and fud_num is not None:
        total = hold_num + fud_num
        if total > 0:
            hold_percentage = (hold_num / total) * 100
            fud_percentage = (fud_num / total) * 100

    return RootDataProject(
        id=data.get("id", 0),
        name=name,
        brief_intro=get_text(data.get("briefIntd", "")),
        description=get_text(data.get("intd", "")),
        image_url=data.get("logoImg"),
        founded_year=int(data.get("establishDate"))
        if data.get("establishDate")
        else None,
        # Status
        status=status,
        level=data.get("level"),
        rank=data.get("rank"),
        # Tags and categories
        tags=tags,
        ecosystems=ecosystems,
        # Token info
        token_symbol=data.get("lssuingCode") or data.get("symbol"),
        token_price=parse_float(data.get("price")),
        market_cap=parse_float(data.get("marketCap")),
        fdv=parse_float(data.get("fullyDilutedMarketCap")),
        volume_24h=parse_float(data.get("volume24")),
        volume_change_24h=parse_float(data.get("volumeChange24")),
        # Supply
        circulating_supply=parse_float(data.get("circulatingSupply")),
        total_supply=parse_float(data.get("totalSupply")),
        max_supply=parse_float(data.get("maxSupply")),
        # Price changes
        price_change_1h=parse_float(data.get("percentChange1h")),
        price_change_24h=parse_float(data.get("percentChange24")),
        price_change_7d=parse_float(data.get("percentChange7d")),
        price_change_30d=parse_float(data.get("percentChange30d")),
        price_change_60d=parse_float(data.get("percentChange60d")),
        # Historical prices
        ath=parse_float(data.get("ath")),
        ath_date=data.get("athDate"),
        atl=parse_float(data.get("atl")),
        atl_date=data.get("atlDate"),
        # Contracts
        contracts=contracts,
        # Social links
        website=data.get("website"),
        twitter=data.get("twitterUrl"),
        discord=data.get("discordUrl"),
        telegram=data.get("telegramUrl"),
        github=data.get("githubUrl"),
        # External links
        coingecko_url=data.get("coingeckoUrl"),
        coinmarketcap_url=data.get("coinmarketcapUrl"),
        defillama_url=data.get("defillamaUrl"),
        # Community sentiment
        hold_percentage=hold_percentage,
        fud_percentage=fud_percentage,
        # Special flags
        is_rootdata_list=bool(data.get("isRootdataList")),
        is_rootdata_list_2025=bool(data.get("isRootdataList2025")),
    )


# ============================================================================
# Main Functions
# ============================================================================


async def search_projects_with_browser_interaction(
    query: str, limit: int = 10
) -> List[RootDataProject]:
    """
    Search projects by interacting with the website's search functionality using Playwright

    This method actually uses the website's search box and extracts results from the rendered page,
    ensuring we get the same results as a user would see.

    Args:
        query: Search keyword
        limit: Maximum results

    Returns:
        List of projects
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.error(
            "Playwright not installed. Install with: "
            "pip install playwright && playwright install chromium"
        )
        return []

    logger.info(f"Searching projects via browser interaction for: {query}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # Navigate to homepage
            await page.goto(
                "https://www.rootdata.com", wait_until="networkidle", timeout=30000
            )

            # Wait for page to load
            await page.wait_for_timeout(500)

            # Click on the search area to reveal the search input
            try:
                # Try to click the search trigger element
                await page.click(
                    'text="Search project, VC, person, X account, token, archive."',
                    timeout=1000,
                )
                await page.wait_for_timeout(500)
            except Exception as e:
                logger.warning(
                    f"Could not click search trigger: {e}, trying alternative method"
                )
                # Try alternative selector
                try:
                    await page.click('[class*="search"]', timeout=1000)
                    await page.wait_for_timeout(500)
                except Exception:
                    pass

            # Now find and use the search input that appeared
            search_input = await page.query_selector('input[placeholder*="Search"]')
            if not search_input:
                logger.error("Could not find search input after clicking search area")
                await browser.close()
                return []

            # Type the query
            await search_input.fill(query)

            # Wait for search results to load
            # We need to wait longer than before to ensure API results are loaded
            try:
                # Wait for project links to appear in the dialog
                await page.wait_for_selector(
                    'dialog a[href*="/Projects/detail/"], [role="dialog"] a[href*="/Projects/detail/"]',
                    timeout=5000,
                )
                # Extra wait to ensure all results are rendered
                await page.wait_for_timeout(500)
            except Exception as e:
                logger.warning(f"Timeout waiting for search results: {e}")
                await page.wait_for_timeout(500)  # Give it more time anyway

            # Extract search results from the search dropdown
            projects_data = await page.evaluate("""() => {
                // Find the search results dialog
                const dialog = document.querySelector('dialog, [role="dialog"]');
                if (!dialog) {
                    return [];
                }
                
                // Find the Projects section that contains project links
                // The search results are organized by category (All, Projects, VC, People, etc.)
                let projectsContainer = null;
                
                // Look for a div/section that contains both "Projects" text and project links
                const allDivs = dialog.querySelectorAll('div, section');
                for (const div of allDivs) {
                    const text = div.textContent;
                    if (text.includes('Projects') && div.querySelector('a[href*="/Projects/detail/"]')) {
                        projectsContainer = div;
                        break;
                    }
                }
                
                // If we couldn't find a specific projects container, use the whole dialog
                if (!projectsContainer) {
                    projectsContainer = dialog;
                }
                
                // Find all project links in the Projects section
                const projectLinks = projectsContainer.querySelectorAll('a[href*="/Projects/detail/"]');
                const projects = [];
                
                for (const link of projectLinks) {
                    // Extract project data from link
                    const href = link.getAttribute('href');
                    const idMatch = href.match(/Projects\\/detail\\/([^?]+)\\?k=([^&]+)/);
                    const nameSlug = idMatch ? idMatch[1] : '';
                    const idBase64 = idMatch ? idMatch[2] : '';
                    
                    // Try to extract ID from base64 (URL-encoded)
                    let id = 0;
                    try {
                        // Decode URL encoding first, then base64
                        const decodedBase64 = decodeURIComponent(idBase64);
                        id = parseInt(atob(decodedBase64));
                    } catch (e) {
                        // If decode fails, continue without ID
                    }
                    
                    // The link itself contains all the text, parse it
                    const linkText = link.textContent.trim();
                    
                    // Extract name from h4 heading within the link
                    const nameEl = link.querySelector('h4');
                    const name = nameEl ? nameEl.textContent.trim() : nameSlug.replace(/%20/g, ' ');
                    
                    // Extract token symbol (usually right after the name)
                    const symbolMatch = linkText.match(/([A-Z]{2,10})(?=\\s+\\$|\\s+[A-Z#])/);
                    const symbol = symbolMatch ? symbolMatch[1] : null;
                    
                    // Extract price
                    const priceMatch = linkText.match(/\\$([0-9.]+)/);
                    const price = priceMatch ? parseFloat(priceMatch[1]) : null;
                    
                    // Extract tags (look for words after price)
                    const tags = [];
                    const tagMatches = linkText.matchAll(/([A-Z][a-zA-Z]+)(?=\\s|$)/g);
                    for (const match of tagMatches) {
                        const tag = match[1];
                        if (tag !== symbol && tags.length < 5) {
                            tags.push(tag);
                        }
                    }
                    
                    // Extract description (paragraph within the link)
                    const descEl = link.querySelector('p');
                    const description = descEl ? descEl.textContent.trim() : '';
                    
                    projects.push({
                        id: id,
                        name: name,
                        nameSlug: nameSlug,
                        token_symbol: symbol,
                        price: price,
                        tags: tags,
                        description: description,
                        href: href
                    });
                }
                
                return projects;
            }""")

            await browser.close()

            if not projects_data:
                logger.warning(f"No projects found for query: {query}")
                return []

            # Parse projects
            projects = []
            for proj_data in projects_data[:limit]:
                try:
                    # Extract ID from href if not found
                    proj_id = proj_data.get("id", 0)
                    if proj_id == 0 and proj_data.get("href"):
                        # Try to extract from URL
                        import base64

                        href = proj_data["href"]
                        k_match = re.search(r"\\?k=([^&]+)", href)
                        if k_match:
                            try:
                                proj_id = int(
                                    base64.b64decode(k_match.group(1)).decode()
                                )
                            except Exception as e:
                                logger.warning(f"Failed to decode project ID: {e}")

                    # Note: Search results have limited data, full details require get_project_detail()
                    project = RootDataProject(
                        id=proj_id,
                        name=proj_data.get("name", ""),
                        brief_intro=proj_data.get("description", ""),
                        description=proj_data.get("description", ""),
                        tags=proj_data.get("tags", []),
                        token_symbol=proj_data.get("token_symbol"),
                        token_price=proj_data.get("price"),
                    )

                    projects.append(project)

                except Exception as e:
                    logger.warning(f"Failed to parse project: {e}")
                    continue

            logger.info(f"Found {len(projects)} projects for query: {query}")
            return projects

        except Exception as e:
            logger.error(f"Browser interaction error: {e}")
            await browser.close()
            return []


async def search_projects(
    query: str, limit: int = 10, use_playwright: bool = True
) -> List[RootDataProject]:
    """
    Search crypto projects using browser interaction to get accurate results

    This method simulates a user searching on the RootData website, ensuring
    we get the same results that a real user would see.

    Args:
        query: Search keyword
        limit: Maximum number of results
        use_playwright: Kept for backward compatibility (always uses browser interaction)

    Returns:
        List of projects

    Examples:
        # Search for "Aster"
        projects = await search_projects("Aster", limit=10)

        # Search for "DeFi"
        projects = await search_projects("DeFi", limit=5)
    """

    # Use browser interaction search (only reliable method)
    try:
        projects = await search_projects_with_browser_interaction(query, limit)
        if projects:
            return projects
        logger.warning(f"No projects found for query: {query}")
        return []
    except Exception as e:
        logger.error(f"Browser interaction search failed: {e}")
        return []


async def get_project_detail(
    project_id: int, use_playwright: bool = True
) -> Optional[RootDataProject]:
    """
    Get comprehensive project details

    This function first tries to use Playwright to extract complete data from
    window.__NUXT__. If that fails or Playwright is not available, it falls back
    to HTML parsing (with less detailed information).

    Args:
        project_id: Project ID (e.g., 12 for Ethereum, 1179 for Ripae)
        use_playwright: If True, use Playwright for detailed data extraction

    Returns:
        RootDataProject with comprehensive information or None if failed

    Examples:
        # Get full project details (recommended)
        project = await get_project_detail(1179)

        # Fallback to HTML parsing only
        project = await get_project_detail(1179, use_playwright=False)
    """
    if use_playwright:
        try:
            project = await get_project_with_playwright(project_id)
            if project:
                return project
            logger.warning(
                f"Playwright extraction failed for project {project_id}, "
                "falling back to HTML parsing"
            )
        except Exception as e:
            logger.warning(
                f"Playwright error for project {project_id}: {e}, "
                "falling back to HTML parsing"
            )

    # Fallback to HTML parsing (less detailed)
    return await get_project_from_page(project_id)


# Backward compatibility aliases
get_project_detail_simple = get_project_detail
search_projects_simple = search_projects


# ============================================================================
# VC Search Functions
# ============================================================================


async def search_vcs_with_playwright(query: str, limit: int = 10) -> List[RootDataVC]:
    """
    Search VCs using Playwright (browser automation)

    Args:
        query: Search keyword
        limit: Maximum number of results

    Returns:
        List of VCs
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.error(
            "Playwright not installed. Install with: "
            "pip install playwright && playwright install chromium"
        )
        return []

    url = f"https://www.rootdata.com/Investors?k={query}"
    logger.info(f"Searching VCs with Playwright: {url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(500)

            # Extract data from __NUXT__
            vcs_data = await page.evaluate("""() => {
                if (!window.__NUXT__ || !window.__NUXT__.data) {
                    return [];
                }
                
                const dataArray = window.__NUXT__.data;
                for (let i = 0; i < dataArray.length; i++) {
                    const item = dataArray[i];
                    if (item && typeof item === 'object') {
                        const keys = ['list', 'investors', 'items', 'data', 'records'];
                        for (const key of keys) {
                            if (item[key] && Array.isArray(item[key])) {
                                return item[key];
                            }
                        }
                    }
                }
                return [];
            }""")

            await browser.close()

            if not vcs_data:
                logger.warning(f"No VCs found for query: {query}")
                return []

            # Parse VCs
            vcs = []
            for vc_data in vcs_data[:limit]:
                try:
                    name = vc_data.get("name", {})
                    if isinstance(name, dict):
                        name = name.get("en_value") or name.get("cn_value") or ""

                    tags = []
                    if "enTagNames" in vc_data:
                        tags_str = vc_data["enTagNames"]
                        if tags_str:
                            tags = [t.strip() for t in str(tags_str).split(",")]

                    vc = RootDataVC(
                        id=vc_data.get("id", 0),
                        name=str(name),
                        brief_intro=vc_data.get("enBriefIntd") or "",
                        description=vc_data.get("enIntd") or "",
                        tags=tags,
                        twitter=vc_data.get("twitter"),
                        website=vc_data.get("website"),
                        image_url=vc_data.get("imgUrl"),
                        portfolio_count=vc_data.get("portfolioCount"),
                        total_investments=vc_data.get("totalInvestments"),
                    )

                    vcs.append(vc)

                except Exception as e:
                    logger.warning(f"Failed to parse VC: {e}")
                    continue

            logger.info(f"Found {len(vcs)} VCs for query: {query}")
            return vcs

        except Exception as e:
            logger.error(f"Playwright error: {e}")
            await browser.close()
            return []


async def search_vcs(
    query: str, limit: int = 10, use_playwright: bool = True
) -> List[RootDataVC]:
    """
    Search venture capital firms and investors

    Args:
        query: Search keyword
        limit: Maximum number of results
        use_playwright: If True, use browser automation (more reliable)

    Returns:
        List of VCs

    Examples:
        # Search for "a16z"
        vcs = await search_vcs("a16z", limit=5)

        # Search for VCs focused on DeFi
        vcs = await search_vcs("DeFi", limit=10)
    """

    if use_playwright:
        try:
            return await search_vcs_with_playwright(query, limit)
        except Exception as e:
            logger.warning(f"Playwright VC search failed: {e}")

    # Fallback: return empty list (HTML parsing for VCs would be similar to projects)
    logger.warning(
        "VC search requires Playwright. Install with: pip install playwright"
    )
    return []


async def get_vc_detail(vc_id: int) -> Optional[RootDataVC]:
    """
    Get VC details by ID

    Args:
        vc_id: VC ID

    Returns:
        RootDataVC or None
    """
    import base64

    encoded_id = base64.b64encode(str(vc_id).encode()).decode()
    url = f"https://www.rootdata.com/Investors/detail/Investor?k={encoded_id}"

    logger.info(f"Fetching VC page: {url}")

    html = await fetch_page_html(url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    try:
        name = ""
        h1 = soup.find("h1")
        if h1:
            name = h1.text.strip()

        brief_intro = ""
        description = ""
        paras = soup.find_all("p")
        for p in paras:
            text = p.text.strip()
            if len(text) > 20:
                if not brief_intro:
                    brief_intro = text
                elif len(text) > len(description):
                    description = text

        tags = []
        tag_elements = soup.find_all(class_=re.compile(r"tag|label", re.I))
        for tag_el in tag_elements:
            tag_text = tag_el.text.strip()
            if tag_text and len(tag_text) < 30:
                tags.append(tag_text)

        website = None
        twitter = None
        links = soup.find_all("a", href=True)
        for link in links:
            href = link["href"]
            if "twitter.com" in href or "x.com" in href:
                twitter = href.split("/")[-1]
            elif href.startswith("http") and "rootdata.com" not in href:
                if not website:
                    website = href

        vc = RootDataVC(
            id=vc_id,
            name=name,
            brief_intro=brief_intro,
            description=description,
            tags=list(set(tags))[:10],
            twitter=twitter,
            website=website,
        )

        logger.info(f"Successfully extracted VC: {name}")
        return vc

    except Exception as e:
        logger.warning(f"Failed to parse VC page: {e}")
        return None


# ============================================================================
# People Search Functions
# ============================================================================


async def search_people_with_playwright(
    query: str, limit: int = 10
) -> List[RootDataPerson]:
    """
    Search people using Playwright (browser automation)

    Args:
        query: Search keyword
        limit: Maximum number of results

    Returns:
        List of people
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.error(
            "Playwright not installed. Install with: "
            "pip install playwright && playwright install chromium"
        )
        return []

    url = f"https://www.rootdata.com/People?k={query}"
    logger.info(f"Searching people with Playwright: {url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(500)

            # Extract data from __NUXT__
            people_data = await page.evaluate("""() => {
                if (!window.__NUXT__ || !window.__NUXT__.data) {
                    return [];
                }
                
                const dataArray = window.__NUXT__.data;
                for (let i = 0; i < dataArray.length; i++) {
                    const item = dataArray[i];
                    if (item && typeof item === 'object') {
                        const keys = ['list', 'people', 'persons', 'items', 'data', 'records'];
                        for (const key of keys) {
                            if (item[key] && Array.isArray(item[key])) {
                                return item[key];
                            }
                        }
                    }
                }
                return [];
            }""")

            await browser.close()

            if not people_data:
                logger.warning(f"No people found for query: {query}")
                return []

            # Parse people
            people = []
            for person_data in people_data[:limit]:
                try:
                    name = person_data.get("name", {})
                    if isinstance(name, dict):
                        name = name.get("en_value") or name.get("cn_value") or ""

                    tags = []
                    if "enTagNames" in person_data:
                        tags_str = person_data["enTagNames"]
                        if tags_str:
                            tags = [t.strip() for t in str(tags_str).split(",")]

                    projects = []
                    if "projects" in person_data and isinstance(
                        person_data["projects"], list
                    ):
                        projects = [
                            p.get("name", "")
                            for p in person_data["projects"]
                            if isinstance(p, dict)
                        ]

                    person = RootDataPerson(
                        id=person_data.get("id", 0),
                        name=str(name),
                        title=person_data.get("title"),
                        brief_intro=person_data.get("enBriefIntd") or "",
                        description=person_data.get("enIntd") or "",
                        tags=tags,
                        twitter=person_data.get("twitter"),
                        linkedin=person_data.get("linkedin"),
                        image_url=person_data.get("imgUrl"),
                        projects=projects,
                        current_organization=person_data.get("organization"),
                    )

                    people.append(person)

                except Exception as e:
                    logger.warning(f"Failed to parse person: {e}")
                    continue

            logger.info(f"Found {len(people)} people for query: {query}")
            return people

        except Exception as e:
            logger.error(f"Playwright error: {e}")
            await browser.close()
            return []


async def search_people(
    query: str, limit: int = 10, use_playwright: bool = True
) -> List[RootDataPerson]:
    """
    Search people (founders, executives, investors)

    Args:
        query: Search keyword (person name or role)
        limit: Maximum number of results
        use_playwright: If True, use browser automation (more reliable)

    Returns:
        List of people

    Examples:
        # Search for "Vitalik Buterin"
        people = await search_people("Vitalik Buterin", limit=5)

        # Search for founders
        people = await search_people("founder", limit=10)
    """

    if use_playwright:
        try:
            return await search_people_with_playwright(query, limit)
        except Exception as e:
            logger.warning(f"Playwright people search failed: {e}")

    logger.warning(
        "People search requires Playwright. Install with: pip install playwright"
    )
    return []


async def get_person_detail(person_id: int) -> Optional[RootDataPerson]:
    """
    Get person details by ID

    Args:
        person_id: Person ID

    Returns:
        RootDataPerson or None
    """
    import base64

    encoded_id = base64.b64encode(str(person_id).encode()).decode()
    url = f"https://www.rootdata.com/People/detail/Person?k={encoded_id}"

    logger.info(f"Fetching person page: {url}")

    html = await fetch_page_html(url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    try:
        name = ""
        h1 = soup.find("h1")
        if h1:
            name = h1.text.strip()

        title = ""
        h2 = soup.find("h2")
        if h2:
            title = h2.text.strip()

        brief_intro = ""
        description = ""
        paras = soup.find_all("p")
        for p in paras:
            text = p.text.strip()
            if len(text) > 20:
                if not brief_intro:
                    brief_intro = text
                elif len(text) > len(description):
                    description = text

        tags = []
        tag_elements = soup.find_all(class_=re.compile(r"tag|label", re.I))
        for tag_el in tag_elements:
            tag_text = tag_el.text.strip()
            if tag_text and len(tag_text) < 30:
                tags.append(tag_text)

        twitter = None
        linkedin = None
        links = soup.find_all("a", href=True)
        for link in links:
            href = link["href"]
            if "twitter.com" in href or "x.com" in href:
                twitter = href.split("/")[-1]
            elif "linkedin.com" in href:
                linkedin = href

        person = RootDataPerson(
            id=person_id,
            name=name,
            title=title,
            brief_intro=brief_intro,
            description=description,
            tags=list(set(tags))[:10],
            twitter=twitter,
            linkedin=linkedin,
        )

        logger.info(f"Successfully extracted person: {name}")
        return person

    except Exception as e:
        logger.warning(f"Failed to parse person page: {e}")
        return None

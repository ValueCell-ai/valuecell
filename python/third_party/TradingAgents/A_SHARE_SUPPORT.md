# A-Share (中国A股) Support for TradingAgents

This document describes the A-share market support that has been added to TradingAgents.

## Overview

TradingAgents now supports analyzing A-share (Chinese stock market) stocks in addition to US stocks. The system automatically detects the stock type based on the ticker symbol and uses the appropriate data sources and analysis methods.

## Features

### 1. Automatic Market Detection

The system automatically detects if a stock is an A-share based on the ticker format:
- **A-share stocks**: 6-digit codes starting with 0, 3, 6, or 8
  - `6xxxxx`: Shanghai Stock Exchange (SSE)
  - `00xxxx`: Shenzhen Main Board
  - `002xxx`: SME Board
  - `3xxxxx`: Growth Enterprise Market (GEM/创业板)
  - `688xxx`: STAR Market (科创板)
  - `8xxxxx`: Beijing Stock Exchange

### 2. Data Sources

#### For A-Share Stocks:
- **AKShare** (akshare library) - Primary data source for Chinese markets
  - Company financials (balance sheet, income statement, cash flow)
  - News from East Money (东方财富)
  - Official company announcements
  - Major shareholder trading data
  - Guba (股吧) sentiment data

#### For US Stocks:
- Finnhub
- Yahoo Finance
- SimFin
- Reddit sentiment

### 3. Specialized Analysts

All analyst agents have been enhanced to support A-share stocks:

#### Fundamentals Analyst
- **A-share**: Analyzes financial statements from Chinese companies, major shareholder trades, and regulatory announcements
- **US stocks**: Uses traditional SEC filings and insider trading data

#### News Analyst
- **A-share**: Aggregates news from East Money and official company announcements
- **US stocks**: Uses Finnhub and global news sources

#### Social Media/Sentiment Analyst
- **A-share**: Analyzes East Money Guba (股吧) discussions and sentiment
- **US stocks**: Uses Reddit sentiment

#### Market/Technical Analyst
- **Both markets**: Uses the same technical indicators (universal application)

### 4. A-Share Trading Rules

The system includes A-share specific trading rules:

#### T+1 Trading
- Stocks bought on day T can only be sold on day T+1 or later
- System validates this restriction before executing sell orders

#### Price Limits (涨跌停)
- **Normal stocks**: ±10% daily price limit
- **ST stocks**: ±5% daily price limit
- **STAR Market/GEM**: ±20% daily price limit

#### Lot Size Requirements
- Minimum trade size: 100 shares (1 lot)
- All trades must be in multiples of 100 shares

#### Trading Hours
- Morning session: 09:30-11:30
- Afternoon session: 13:00-15:00
- Call auction: 09:15-09:25 (open), 14:57-15:00 (close, STAR/GEM only)

## Installation

### Prerequisites

Install the required dependencies:

```bash
# Install AKShare for A-share data
pip install akshare

# Or if using uv (recommended)
uv pip install akshare
```

### Configuration

No special configuration is needed. The system automatically uses the appropriate tools based on the ticker format.

However, you can verify AKShare is installed:

```python
import akshare as ak
print("AKShare version:", ak.__version__)
```

## Usage Examples

### Example 1: Analyze A-Share Stock (贵州茅台)

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

# Initialize with config
config = DEFAULT_CONFIG.copy()
config["online_tools"] = True  # Use online data sources

ta = TradingAgentsGraph(debug=True, config=config)

# Analyze Moutai (贵州茅台)
_, decision = ta.propagate("600519", "2024-05-10")
print(decision)
```

### Example 2: Analyze US Stock (NVIDIA)

```python
# Same code, just different ticker - system auto-detects market
_, decision = ta.propagate("NVDA", "2024-05-10")
print(decision)
```

### Example 3: Risk Assessment for A-Share Trade

```python
from tradingagents.agents.risk_mgmt.a_share_trading_rules import AShareTradingRules

# Check if trade meets A-share requirements
rules = AShareTradingRules()

# Validate trade size
is_valid, msg = rules.validate_trade_size(250)  # Not multiple of 100
print(f"Valid: {is_valid}, Message: {msg}")
# Output: Valid: False, Message: Trade size must be in multiples of 100 shares

# Calculate price limits
ticker = "600519"  # Moutai
prev_close = 1800.00
lower, upper = rules.calculate_price_limits(ticker, prev_close)
print(f"Price limits: {lower} - {upper}")
# Output: Price limits: 1620.00 - 1980.00 (±10% for normal stock)

# Full risk assessment
assessment = rules.generate_risk_assessment(
    ticker="600519",
    trade_action="BUY",
    trade_price=1850.00,
    trade_shares=200,
    prev_close=1800.00,
    company_name="贵州茅台"
)
print(assessment)
```

## Supported A-Share Stocks

You can analyze any A-share stock using its 6-digit code:

- **600519**: 贵州茅台 (Kweichow Moutai)
- **000001**: 平安银行 (Ping An Bank)
- **000002**: 万科A (China Vanke)
- **600036**: 招商银行 (China Merchants Bank)
- **300750**: 宁德时代 (CATL)
- **688981**: 中芯国际 (SMIC)
- And many more...

## Architecture

```
User Input (Ticker)
       ↓
[Market Detector]
       ↓
  ┌────┴────┐
  │         │
A-Share   US Stock
  │         │
  ↓         ↓
AKShare   Finnhub/YFin
  │         │
  └────┬────┘
       ↓
 [Analyst Agents]
  - Fundamentals
  - News
  - Sentiment
  - Technical
       ↓
 [Risk Management]
  - A-share: T+1, Price Limits
  - US: Pattern Day Trading
       ↓
  [Decision]
```

## Data Availability

### Online Mode (`online_tools=True`)
- Uses real-time APIs (AKShare for A-shares, OpenAI/Finnhub for US)
- Recommended for live trading analysis
- Requires internet connection

### Offline Mode (`online_tools=False`)
- Uses cached historical data
- Good for backtesting
- Limited to available cached data range

## Limitations

1. **AKShare API Stability**: AKShare APIs may change; ensure you're using the latest version
2. **Data Freshness**: Some AKShare data may have delays compared to real-time feeds
3. **Guba Sentiment**: Sentiment analysis is based on engagement metrics (reads, comments), not NLP sentiment
4. **Market Hours**: System doesn't enforce trading hour restrictions (analysis can run anytime)

## Troubleshooting

### Issue: "AKShare not installed"
```bash
pip install akshare
# or
uv pip install akshare
```

### Issue: "No data available for ticker XXXXXX"
- Verify the ticker is correct (6 digits for A-shares)
- Check if the stock was listed before the analysis date
- Some newly listed stocks may have limited historical data

### Issue: AKShare API errors
```python
# Try updating AKShare to the latest version
pip install --upgrade akshare
```

## Future Enhancements

Planned improvements:
1. Hong Kong Stock Exchange (HKEX) support
2. Advanced sentiment analysis using Chinese NLP models
3. Cross-market correlation analysis (A-share vs US markets)
4. Integration with more Chinese data sources (Tushare, Wind)
5. Support for A-share options and convertible bonds

## Contributing

If you'd like to contribute A-share specific features:
1. Check the ticker is an A-share: `AShareDataAdapter.is_a_share_symbol(ticker)`
2. Use appropriate data sources from `akshare_china_adapter.py`
3. Follow existing agent patterns for market-specific logic
4. Add appropriate Chinese language support in prompts

## References

- [AKShare Documentation](https://akshare.akfamily.xyz/)
- [A-Share Trading Rules (中国证监会)](http://www.csrc.gov.cn/)
- [Shanghai Stock Exchange](http://www.sse.com.cn/)
- [Shenzhen Stock Exchange](http://www.szse.cn/)

## License

Same as TradingAgents - see LICENSE file.

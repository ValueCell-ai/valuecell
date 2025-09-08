# ValueCell Asset Data Adapter System

A comprehensive financial asset data management system that supports multiple data sources, internationalization, and user watchlist management.

## Features

### 🌐 Multi-Source Data Adapters
- **Yahoo Finance**: Free stock market data for global markets
- **TuShare**: Professional Chinese stock market data (requires API key)  
- **AKShare**: Free Chinese financial data library (no API key required)
- **Finnhub**: Professional global stock market data (requires API key)
- **CoinMarketCap**: Cryptocurrency market data (requires API key)
- **Extensible**: Easy to add new data sources

### 📊 Asset Types Support
- Stocks (US, Chinese, Hong Kong, etc.)
- Cryptocurrencies
- ETFs, Mutual Funds
- Bonds, Commodities
- Forex, Indices
- Options, Futures

### 🔄 Standardized Ticker Format
All assets use the format `[EXCHANGE]:[SYMBOL]`:
- `NASDAQ:AAPL` - Apple Inc.
- `SSE:600519` - Kweichow Moutai
- `CRYPTO:BTC` - Bitcoin
- `HKEX:00700` - Tencent Holdings

### 🌍 Internationalization (i18n)
- Multi-language asset names
- Localized UI text and messages
- Currency and number formatting
- Support for Chinese, English, and more

### 📝 User Watchlist Management
- Create multiple watchlists per user
- Add/remove assets with personal notes
- Real-time price updates
- Persistent storage ready

## Quick Start

### 1. Installation

```bash
# Install required dependencies

pip install yfinance tushare requests pydantic
```

### 2. Basic Usage

```python
from valuecell.adapters.assets import get_adapter_manager
from valuecell.services.assets import (
    search_assets, add_to_watchlist, get_watchlist
)

# Configure data adapters
manager = get_adapter_manager()
manager.configure_yfinance()  # Free, no API key needed

# Search for assets (now via service layer)
results = search_assets("AAPL", language="zh-Hans")
print(f"Found {results['count']} assets")

# Add to watchlist (now via service layer)
add_to_watchlist(
    user_id="user123", 
    ticker="NASDAQ:AAPL", 
    notes="苹果公司股票"
)

# Get watchlist with prices (now via service layer)
watchlist = get_watchlist(user_id="user123", include_prices=True)
```

### 3. Configure Data Sources

```python
# Yahoo Finance (Free)
manager.configure_yfinance()

# AKShare (Free Chinese markets)
manager.configure_akshare()

# TuShare (Chinese markets, requires API key)
manager.configure_tushare(api_key="your_tushare_token")

# Finnhub (Global markets, requires API key)
manager.configure_finnhub(api_key="your_finnhub_token")

# CoinMarketCap (Crypto, requires API key) 
manager.configure_coinmarketcap(api_key="your_cmc_api_key")
```

## API Reference

### Asset Search

```python
from valuecell.services.assets import search_assets

# Basic search
results = search_assets("Apple")

# Advanced search with filters
results = search_assets(
    query="tech",
    asset_types=["stock", "etf"],
    exchanges=["NASDAQ", "NYSE"],
    countries=["US"],
    limit=20,
    language="zh-Hans"
)
```

### Asset Information

```python
from valuecell.services.assets import get_asset_info, get_asset_price

# Get detailed asset information
info = get_asset_info("NASDAQ:AAPL", language="zh-Hans")
print(info["display_name"])  # "苹果公司"

# Get current price
price = get_asset_price("NASDAQ:AAPL", language="zh-Hans")
print(price["price_formatted"])  # "¥150.25"
print(price["change_percent_formatted"])  # "+2.5%"
```

### Watchlist Management

```python
from valuecell.services.assets import get_asset_service

service = get_asset_service()

# Create watchlist
service.create_watchlist(
    user_id="user123",
    name="My Tech Stocks", 
    description="Technology companies"
)

# Add assets
service.add_to_watchlist("user123", "NASDAQ:AAPL", notes="iPhone maker")
service.add_to_watchlist("user123", "NASDAQ:GOOGL", notes="Search engine")

# Get watchlist with prices
watchlist = service.get_watchlist("user123", include_prices=True)
```

## Data Source Configuration

### Yahoo Finance
- **Cost**: Free
- **Coverage**: Global stocks, ETFs, indices, crypto
- **Rate Limits**: Reasonable for personal use
- **Setup**: No API key required

```python
manager.configure_yfinance()
```

### TuShare
- **Cost**: Free tier available, paid plans for more data
- **Coverage**: Chinese stocks (A-shares), indices, financials
- **Rate Limits**: Based on subscription plan
- **Setup**: Register at [tushare.pro](https://tushare.pro)

```python
manager.configure_tushare(api_key="your_token_here")
```

### AKShare
- **Cost**: Free
- **Coverage**: Chinese stocks, funds, bonds, economic data
- **Rate Limits**: Reasonable for personal use
- **Setup**: No registration required

```python
manager.configure_akshare()
```

### Finnhub
- **Cost**: Free tier (60 calls/minute), paid plans available
- **Coverage**: Global stocks, forex, crypto, company data
- **Rate Limits**: Based on plan (free: 60 calls/minute)
- **Setup**: Register at [finnhub.io](https://finnhub.io)

```python
manager.configure_finnhub(api_key="your_api_key_here")
```

### CoinMarketCap
- **Cost**: Free tier (10,000 calls/month), paid plans available
- **Coverage**: 9,000+ cryptocurrencies
- **Rate Limits**: Based on plan (free: 333 calls/day)
- **Setup**: Register at [coinmarketcap.com](https://coinmarketcap.com/api/)

```python
manager.configure_coinmarketcap(api_key="your_api_key_here")
```

## Internationalization

### Supported Languages
- English US (`en-US`)
- English UK (`en-GB`)
- Simplified Chinese (`zh-Hans`)
- Traditional Chinese (`zh-Hant`)
- Easy to add more languages

### Asset Name Translation
The system includes built-in translations for popular assets:

```python
# Apple Inc. in different languages
"NASDAQ:AAPL": {
    "en-US": "Apple Inc.",
    "zh-Hans": "苹果公司", 
    "zh-Hant": "蘋果公司"
}
```

### Custom Translations
Add your own asset translations:

```python
from valuecell.adapters.assets import get_asset_i18n_service

i18n_service = get_asset_i18n_service()
i18n_service.add_asset_translation(
    ticker="NASDAQ:TSLA",
    language="zh-Hans", 
    name="特斯拉"
)
```

## Architecture

### Core Components

1. **Types** (`types.py`): Data structures and models
2. **Base Adapter** (`base.py`): Abstract interface for data sources
3. **Specific Adapters**: Implementation for each data source
4. **Manager** (`manager.py`): Coordinates multiple adapters
5. **I18n Integration** (`i18n_integration.py`): Localization support
6. **Service Layer** (`valuecell.services.assets`): High-level business logic interface

### Data Flow

```
User Request → Service Layer → Manager → Adapter → Data Source
                     ↓
              I18n Service → Localized Response
```

### Ticker Conversion

Internal format: `EXCHANGE:SYMBOL`
- `NASDAQ:AAPL` → `AAPL` (Yahoo Finance)
- `SSE:600519` → `600519.SH` (TuShare)
- `CRYPTO:BTC` → `BTC` (CoinMarketCap)

## Error Handling

The system provides comprehensive error handling:

```python
# All API functions return structured responses
result = search_assets("invalid_query")

if result["success"]:
    # Process results
    assets = result["results"]
else:
    # Handle error
    error_message = result["error"]
    print(f"Search failed: {error_message}")
```

### Common Error Types
- `AdapterError`: General adapter issues
- `RateLimitError`: API rate limit exceeded
- `AuthenticationError`: Invalid API credentials
- `DataNotAvailableError`: Requested data not found
- `InvalidTickerError`: Malformed ticker format

## Performance Considerations

### Batch Operations
Use batch operations for better performance:

```python
# Get multiple prices at once (more efficient)
prices = api.get_multiple_prices(["NASDAQ:AAPL", "NASDAQ:GOOGL", "NASDAQ:MSFT"])

# Instead of individual calls
# price1 = get_asset_price("NASDAQ:AAPL")  # Slower
# price2 = get_asset_price("NASDAQ:GOOGL") # Slower
```

### Caching
- Asset information is cached automatically
- Price data is real-time (not cached)
- Translation cache improves i18n performance

### Rate Limiting
- Built-in rate limiting for each data source
- Automatic retry with exponential backoff
- Respects API provider limits

## Testing

Run the example to test your setup:

```python
python -m valuecell.examples.asset_adapter_example
```

### Health Check
Monitor adapter status:

```python
from valuecell.services.assets import get_asset_service

service = get_asset_service()
health = service.get_system_health()
print(f"System status: {health['overall_status']}")
```

## Extending the System

### Adding New Data Sources

1. Create a new adapter class inheriting from `BaseDataAdapter`
2. Implement required methods (`search_assets`, `get_asset_info`, etc.)
3. Add ticker conversion logic
4. Register with the manager

```python
class MyDataAdapter(BaseDataAdapter):
    def search_assets(self, query):
        # Implementation
        pass
    
    def get_asset_info(self, ticker):
        # Implementation  
        pass
    
    # ... other methods

# Register the adapter
manager.register_adapter(MyDataAdapter())
```

### Adding New Asset Types

1. Add to `AssetType` enum in `types.py`
2. Update adapter priority mapping
3. Add i18n translations

## Best Practices

### API Keys Security
- Store API keys in environment variables
- Never commit API keys to version control
- Use different keys for development/production

### Error Handling
- Always check the `success` field in responses
- Implement proper retry logic for transient failures
- Log errors for debugging

### Performance
- Use batch operations when possible
- Implement client-side caching for static data
- Monitor API usage to avoid rate limits

### Internationalization
- Always specify language parameter for consistent results
- Provide fallback translations
- Test with different locales

## Troubleshooting

### Common Issues

**"No suitable adapter found for ticker"**
- Check ticker format: `EXCHANGE:SYMBOL`
- Verify the exchange is supported by configured adapters
- Ensure at least one adapter is configured

**"Rate limit exceeded"**
- Wait for the specified retry period
- Consider upgrading to paid API plan
- Implement request batching

**"Authentication failed"**
- Verify API key is correct and active
- Check API key permissions/subscription status
- Ensure API key is properly configured

### Debug Mode
Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Update documentation
5. Submit a pull request

## License

This project is part of the ValueCell platform and follows the project's licensing terms.

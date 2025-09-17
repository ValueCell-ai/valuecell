# ValueCell Watchlist API Documentation

A comprehensive API for managing financial asset watchlists with multi-market support, real-time price data, and internationalization.

## Table of Contents

- [Overview](#overview)
- [Ticker Naming Conventions](#ticker-naming-conventions)
- [API Endpoints](#api-endpoints)
- [Authentication](#authentication)
- [Request/Response Format](#requestresponse-format)
- [Error Handling](#error-handling)
- [Examples](#examples)

## Overview

The ValueCell Watchlist API provides a complete solution for managing financial asset watchlists across multiple markets including US stocks, Hong Kong stocks, A-shares (Chinese stocks), and cryptocurrencies. The API supports real-time price data, multi-language localization, and comprehensive asset search capabilities.

### Key Features

- ✅ **Multi-Market Support**: US stocks (NASDAQ, NYSE), Hong Kong stocks (HKEX), Chinese A-shares (SSE, SZSE), and cryptocurrencies
- ✅ **Real-time Price Data**: Current prices, market data, and price history
- ✅ **Internationalization**: Multi-language support for asset names and descriptions
- ✅ **User Watchlists**: Create, manage, and organize multiple watchlists per user
- ✅ **Asset Search**: Powerful search with filtering by market, asset type, and country
- ✅ **RESTful API**: Standard HTTP methods with JSON responses

## Ticker Naming Conventions

The ValueCell system uses a standardized ticker format: `[EXCHANGE]:[SYMBOL]`

### US Stocks
```
NASDAQ:AAPL    # Apple Inc.
NYSE:JPM       # JPMorgan Chase & Co.
NYSE:JNJ       # Johnson & Johnson
NASDAQ:MSFT    # Microsoft Corporation
NASDAQ:GOOGL   # Alphabet Inc.
```

### Hong Kong Stocks (HKEX)
```
HKEX:00700     # Tencent Holdings Ltd (padded to 4 digits)
HKEX:09988     # Alibaba Group Holding Ltd
HKEX:03690     # Meituan
HKEX:01299     # AIA Group Ltd
HKEX:00005     # HSBC Holdings plc
```

### Chinese A-Shares
#### Shanghai Stock Exchange (SSE)
```
SSE:600519     # Kweichow Moutai Co Ltd
SSE:600036     # China Merchants Bank Co Ltd
SSE:600000     # Pudong Development Bank Co Ltd
SSE:601318     # Ping An Insurance Group Co of China Ltd
```

#### Shenzhen Stock Exchange (SZSE)
```
SZSE:000858    # Wuliangye Yibin Co Ltd
SZSE:000001    # Ping An Bank Co Ltd
SZSE:000002    # China Vanke Co Ltd
SZSE:300059    # East Money Information Co Ltd
```

#### Beijing Stock Exchange (BSE)
```
BSE:430047     # Jinguan Co Ltd
BSE:832885     # Jilin Carbon Co Ltd
```

### Cryptocurrencies
```
CRYPTO:BTC     # Bitcoin
CRYPTO:ETH     # Ethereum
CRYPTO:USDT    # Tether
CRYPTO:BNB     # Binance Coin
CRYPTO:ADA     # Cardano
CRYPTO:SOL     # Solana
```

### Exchange Code Reference
| Exchange Code | Full Name | Market |
|---------------|-----------|---------|
| `NASDAQ` | NASDAQ Stock Market | US |
| `NYSE` | New York Stock Exchange | US |
| `HKEX` | Hong Kong Stock Exchange | Hong Kong |
| `SSE` | Shanghai Stock Exchange | China |
| `SZSE` | Shenzhen Stock Exchange | China |
| `BSE` | Beijing Stock Exchange | China |
| `CRYPTO` | Cryptocurrency | Global |

## API Endpoints

Base URL: `http://localhost:8000/api/v1/watchlist`

### 1. Search Assets

Search for financial assets with filtering options.

**Endpoint:** `GET /search`

**Parameters:**
- `q` (required): Search query string
- `asset_types` (optional): Comma-separated asset types
- `exchanges` (optional): Comma-separated exchange codes
- `countries` (optional): Comma-separated country codes
- `limit` (optional): Maximum results (1-200, default: 50)
- `language` (optional): Language code for localized results

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/watchlist/search?q=Apple&limit=10&language=en-US"
```

**Example Response:**
```json
{
  "code": 0,
  "msg": "Asset search completed successfully",
  "data": {
    "results": [
      {
        "ticker": "NASDAQ:AAPL",
        "asset_type": "stock",
        "asset_type_display": "Stock",
        "names": {
          "en-US": "Apple Inc.",
          "zh-Hans": "苹果公司",
          "zh-Hant": "蘋果公司"
        },
        "display_name": "Apple Inc.",
        "exchange": "NASDAQ",
        "country": "US",
        "currency": "USD",
        "market_status": "open",
        "market_status_display": "Market Open",
        "relevance_score": 0.95
      }
    ],
    "count": 1,
    "query": "Apple",
    "filters": {},
    "language": "en-US"
  }
}
```

### 2. Get Asset Details

Get detailed information about a specific asset.

**Endpoint:** `GET /asset/{ticker}`

**Parameters:**
- `ticker` (path): Asset ticker in standardized format
- `language` (optional): Language code for localized content

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/watchlist/asset/NASDAQ:AAPL?language=en-US"
```

**Example Response:**
```json
{
  "code": 0,
  "msg": "Asset details retrieved successfully",
  "data": {
    "ticker": "NASDAQ:AAPL",
    "asset_type": "stock",
    "asset_type_display": "Stock",
    "names": {
      "en-US": "Apple Inc.",
      "zh-Hans": "苹果公司",
      "zh-Hant": "蘋果公司"
    },
    "display_name": "Apple Inc.",
    "descriptions": {
      "en-US": "Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide."
    },
    "market_info": {
      "exchange": "NASDAQ",
      "country": "US",
      "currency": "USD",
      "timezone": "America/New_York",
      "market_hours": {
        "open": "09:30",
        "close": "16:00"
      }
    },
    "source_mappings": {
      "yfinance": "AAPL",
      "finnhub": "AAPL"
    },
    "properties": {
      "sector": "Technology",
      "industry": "Consumer Electronics"
    },
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-15T12:00:00Z",
    "is_active": true
  }
}
```

### 3. Get Asset Price

Get current price information for an asset.

**Endpoint:** `GET /asset/{ticker}/price`

**Parameters:**
- `ticker` (path): Asset ticker in standardized format
- `language` (optional): Language code for localized formatting

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/watchlist/asset/NASDAQ:AAPL/price?language=en-US"
```

**Example Response:**
```json
{
  "code": 0,
  "msg": "Asset price retrieved successfully",
  "data": {
    "ticker": "NASDAQ:AAPL",
    "price": 185.25,
    "price_formatted": "$185.25",
    "currency": "USD",
    "timestamp": "2024-01-15T21:00:00Z",
    "volume": 45678900,
    "open_price": 184.50,
    "high_price": 186.75,
    "low_price": 183.80,
    "close_price": 185.25,
    "change": 0.75,
    "change_percent": 0.41,
    "change_percent_formatted": "+0.41%",
    "market_cap": 2890000000000,
    "market_cap_formatted": "$2.89T",
    "source": "yfinance"
  }
}
```

### 4. Get User Watchlists

Get all watchlists for a specific user.

**Endpoint:** `GET /{user_id}`

**Parameters:**
- `user_id` (path): User identifier

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/watchlist/user123"
```

**Example Response:**
```json
{
  "code": 0,
  "msg": "Retrieved 2 watchlists",
  "data": [
    {
      "id": 1,
      "user_id": "user123",
      "name": "My Stocks",
      "description": "My favorite tech stocks",
      "is_default": true,
      "is_public": false,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-15T12:00:00Z",
      "items_count": 3,
      "items": [
        {
          "id": 1,
          "ticker": "NASDAQ:AAPL",
          "notes": "Strong quarterly results",
          "order_index": 1,
          "added_at": "2024-01-01T00:00:00Z",
          "updated_at": "2024-01-10T08:00:00Z",
          "exchange": "NASDAQ",
          "symbol": "AAPL"
        },
        {
          "id": 2,
          "ticker": "HKEX:00700",
          "notes": "Gaming revenue growth",
          "order_index": 2,
          "added_at": "2024-01-02T00:00:00Z",
          "updated_at": "2024-01-02T00:00:00Z",
          "exchange": "HKEX",
          "symbol": "00700"
        }
      ]
    },
    {
      "id": 2,
      "user_id": "user123",
      "name": "Crypto Portfolio",
      "description": "Cryptocurrency investments",
      "is_default": false,
      "is_public": false,
      "created_at": "2024-01-05T00:00:00Z",
      "updated_at": "2024-01-12T15:00:00Z",
      "items_count": 2,
      "items": [
        {
          "id": 3,
          "ticker": "CRYPTO:BTC",
          "notes": "Long-term hold",
          "order_index": 1,
          "added_at": "2024-01-05T00:00:00Z",
          "updated_at": "2024-01-05T00:00:00Z",
          "exchange": "CRYPTO",
          "symbol": "BTC"
        }
      ]
    }
  ]
}
```

### 5. Get Specific Watchlist

Get a specific watchlist by name with optional price data.

**Endpoint:** `GET /{user_id}/{watchlist_name}`

**Parameters:**
- `user_id` (path): User identifier
- `watchlist_name` (path): Watchlist name
- `include_prices` (optional): Include current prices (default: true)
- `language` (optional): Language code for localized content

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/watchlist/user123/My%20Stocks?include_prices=true&language=en-US"
```

**Example Response:**
```json
{
  "code": 0,
  "msg": "Watchlist retrieved successfully",
  "data": {
    "id": 1,
    "user_id": "user123",
    "name": "My Stocks",
    "description": "My favorite tech stocks",
    "is_default": true,
    "is_public": false,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-15T12:00:00Z",
    "items_count": 2,
    "items": [
      {
        "id": 1,
        "ticker": "NASDAQ:AAPL",
        "notes": "Strong quarterly results",
        "order_index": 1,
        "added_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-10T08:00:00Z",
        "exchange": "NASDAQ",
        "symbol": "AAPL"
      },
      {
        "id": 2,
        "ticker": "HKEX:00700",
        "notes": "Gaming revenue growth",
        "order_index": 2,
        "added_at": "2024-01-02T00:00:00Z",
        "updated_at": "2024-01-02T00:00:00Z",
        "exchange": "HKEX",
        "symbol": "00700"
      }
    ]
  }
}
```

### 6. Create Watchlist

Create a new watchlist for a user.

**Endpoint:** `POST /{user_id}`

**Parameters:**
- `user_id` (path): User identifier

**Request Body:**
```json
{
  "name": "Tech Stocks",
  "description": "Technology sector investments",
  "is_default": false,
  "is_public": false
}
```

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/watchlist/user123" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Tech Stocks",
    "description": "Technology sector investments",
    "is_default": false,
    "is_public": false
  }'
```

**Example Response:**
```json
{
  "code": 0,
  "msg": "Watchlist created successfully",
  "data": {
    "id": 3,
    "user_id": "user123",
    "name": "Tech Stocks",
    "description": "Technology sector investments",
    "is_default": false,
    "is_public": false,
    "created_at": "2024-01-15T12:30:00Z",
    "updated_at": "2024-01-15T12:30:00Z",
    "items_count": 0,
    "items": []
  }
}
```

### 7. Add Stock to Watchlist

Add a stock to a user's watchlist.

**Endpoint:** `POST /{user_id}/stocks`

**Parameters:**
- `user_id` (path): User identifier

**Request Body:**
```json
{
  "ticker": "SSE:600519",
  "watchlist_name": "My Stocks",
  "notes": "Chinese liquor company with strong brand"
}
```

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/watchlist/user123/stocks" \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "SSE:600519",
    "watchlist_name": "My Stocks",
    "notes": "Chinese liquor company with strong brand"
  }'
```

**Example Response:**
```json
{
  "code": 0,
  "msg": "Stock added to watchlist successfully",
  "data": {
    "ticker": "SSE:600519",
    "user_id": "user123",
    "watchlist_name": "My Stocks",
    "notes": "Chinese liquor company with strong brand"
  }
}
```

### 8. Remove Stock from Watchlist

Remove a stock from a user's watchlist.

**Endpoint:** `DELETE /{user_id}/stocks/{ticker}`

**Parameters:**
- `user_id` (path): User identifier
- `ticker` (path): Stock ticker to remove
- `watchlist_name` (optional): Watchlist name (uses default if not provided)

**Example Request:**
```bash
curl -X DELETE "http://localhost:8000/api/v1/watchlist/user123/stocks/SSE:600519?watchlist_name=My%20Stocks"
```

**Example Response:**
```json
{
  "code": 0,
  "msg": "Stock removed from watchlist successfully",
  "data": {
    "ticker": "SSE:600519",
    "user_id": "user123",
    "watchlist_name": "My Stocks"
  }
}
```

### 9. Update Stock Notes

Update notes for a stock in a watchlist.

**Endpoint:** `PUT /{user_id}/stocks/{ticker}/notes`

**Parameters:**
- `user_id` (path): User identifier
- `ticker` (path): Stock ticker
- `watchlist_name` (optional): Watchlist name (uses default if not provided)

**Request Body:**
```json
{
  "notes": "Updated analysis: Strong growth potential in AI sector"
}
```

**Example Request:**
```bash
curl -X PUT "http://localhost:8000/api/v1/watchlist/user123/stocks/NASDAQ:AAPL/notes?watchlist_name=My%20Stocks" \
  -H "Content-Type: application/json" \
  -d '{
    "notes": "Updated analysis: Strong growth potential in AI sector"
  }'
```

**Example Response:**
```json
{
  "code": 0,
  "msg": "Stock notes updated successfully",
  "data": {
    "ticker": "NASDAQ:AAPL",
    "user_id": "user123",
    "notes": "Updated analysis: Strong growth potential in AI sector",
    "watchlist_name": "My Stocks"
  }
}
```

### 10. Delete Watchlist

Delete a user's watchlist.

**Endpoint:** `DELETE /{user_id}/{watchlist_name}`

**Parameters:**
- `user_id` (path): User identifier
- `watchlist_name` (path): Watchlist name to delete

**Example Request:**
```bash
curl -X DELETE "http://localhost:8000/api/v1/watchlist/user123/Tech%20Stocks"
```

**Example Response:**
```json
{
  "code": 0,
  "msg": "Watchlist deleted successfully",
  "data": {
    "user_id": "user123",
    "watchlist_name": "Tech Stocks"
  }
}
```

## Authentication

Currently, the API does not require authentication. User identification is handled through the `user_id` parameter in the URL path. In production environments, you should implement proper authentication and authorization mechanisms.

## Request/Response Format

### Standard Response Format

All API responses follow a consistent format:

```json
{
  "code": 0,           // Status code (0 = success, others = error)
  "msg": "success",    // Response message
  "data": {...}        // Response data (varies by endpoint)
}
```

### Status Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `400` | Bad Request |
| `401` | Unauthorized |
| `403` | Forbidden |
| `404` | Not Found |
| `500` | Internal Server Error |

### Content Type

All requests and responses use `application/json` content type.

## Error Handling

### Error Response Format

```json
{
  "code": 404,
  "msg": "Asset 'INVALID:TICKER' not found",
  "data": null
}
```

### Common Error Scenarios

1. **Invalid Ticker Format**
   ```json
   {
     "code": 400,
     "msg": "Invalid ticker format. Expected 'EXCHANGE:SYMBOL'",
     "data": null
   }
   ```

2. **Asset Not Found**
   ```json
   {
     "code": 404,
     "msg": "Asset 'NASDAQ:INVALID' not found",
     "data": null
   }
   ```

3. **Watchlist Not Found**
   ```json
   {
     "code": 404,
     "msg": "Watchlist 'NonExistent' not found for user 'user123'",
     "data": null
   }
   ```

4. **Validation Error**
   ```json
   {
     "code": 400,
     "msg": "Validation error: name field is required",
     "data": null
   }
   ```

## Examples

### Complete Workflow Example

Here's a complete example showing how to create a watchlist and manage assets:

```bash
# 1. Search for assets
curl -X GET "http://localhost:8000/api/v1/watchlist/search?q=Apple&limit=5"

# 2. Create a new watchlist
curl -X POST "http://localhost:8000/api/v1/watchlist/user123" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Tech Portfolio",
    "description": "My technology stock investments",
    "is_default": false,
    "is_public": false
  }'

# 3. Add stocks to the watchlist
curl -X POST "http://localhost:8000/api/v1/watchlist/user123/stocks" \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "NASDAQ:AAPL",
    "watchlist_name": "Tech Portfolio",
    "notes": "Strong iPhone sales"
  }'

curl -X POST "http://localhost:8000/api/v1/watchlist/user123/stocks" \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "HKEX:00700",
    "watchlist_name": "Tech Portfolio",
    "notes": "Leading Chinese tech company"
  }'

# 4. Get watchlist with current prices
curl -X GET "http://localhost:8000/api/v1/watchlist/user123/Tech%20Portfolio?include_prices=true"

# 5. Update stock notes
curl -X PUT "http://localhost:8000/api/v1/watchlist/user123/stocks/NASDAQ:AAPL/notes" \
  -H "Content-Type: application/json" \
  -d '{
    "notes": "Strong iPhone sales + AI integration potential"
  }'

# 6. Get asset price details
curl -X GET "http://localhost:8000/api/v1/watchlist/asset/NASDAQ:AAPL/price"

# 7. Remove a stock from watchlist
curl -X DELETE "http://localhost:8000/api/v1/watchlist/user123/stocks/HKEX:00700?watchlist_name=Tech%20Portfolio"
```

### Multi-Language Example

```bash
# Search with Chinese localization
curl -X GET "http://localhost:8000/api/v1/watchlist/search?q=苹果&language=zh-Hans"

# Get asset details in Traditional Chinese
curl -X GET "http://localhost:8000/api/v1/watchlist/asset/NASDAQ:AAPL?language=zh-Hant"

# Get price data with Chinese formatting
curl -X GET "http://localhost:8000/api/v1/watchlist/asset/SSE:600519/price?language=zh-Hans"
```

### Cryptocurrency Example

```bash
# Search for cryptocurrencies
curl -X GET "http://localhost:8000/api/v1/watchlist/search?q=Bitcoin&asset_types=crypto"

# Add Bitcoin to watchlist
curl -X POST "http://localhost:8000/api/v1/watchlist/user123/stocks" \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "CRYPTO:BTC",
    "watchlist_name": "Crypto Portfolio",
    "notes": "Digital gold hedge against inflation"
  }'

# Get Bitcoin price
curl -X GET "http://localhost:8000/api/v1/watchlist/asset/CRYPTO:BTC/price"
```

## Development and Testing

### Running the API Server

```bash
# Navigate to the project directory
cd /Users/guoyuliang/Project/valuecell

# Activate virtual environment
source python/.venv/bin/activate

# Install dependencies
uv sync

# Start the API server
uvicorn python.valuecell.server.main:app --host 0.0.0.0 --port 8000 --reload
```

### API Documentation

Once the server is running, you can access:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Testing with Different Markets

```bash
# US Stock
curl -X GET "http://localhost:8000/api/v1/watchlist/asset/NASDAQ:MSFT/price"

# Hong Kong Stock
curl -X GET "http://localhost:8000/api/v1/watchlist/asset/HKEX:00700/price"

# Chinese A-Share
curl -X GET "http://localhost:8000/api/v1/watchlist/asset/SSE:600519/price"

# Cryptocurrency
curl -X GET "http://localhost:8000/api/v1/watchlist/asset/CRYPTO:ETH/price"
```

## Data Sources

The API integrates with multiple data sources:

- **Yahoo Finance**: Free global stock data
- **AKShare**: Free Chinese financial data
- **TuShare**: Professional Chinese stock data (API key required)
- **Finnhub**: Professional global stock data (API key required)
- **CoinMarketCap**: Cryptocurrency data (API key required)

## Support

For questions, issues, or feature requests, please refer to the ValueCell project documentation or contact the development team.

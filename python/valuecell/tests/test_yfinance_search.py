"""Comprehensive tests for YFinanceAdapter search functionality.

This module tests the updated search_assets function that uses yfinance.Search
for improved search results across stocks, ETFs, and other financial assets.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
from datetime import datetime

from valuecell.adapters.assets.yfinance_adapter import YFinanceAdapter
from valuecell.adapters.assets.types import (
    AssetSearchQuery,
    AssetSearchResult,
    AssetType,
    MarketStatus,
    DataSource,
)


class TestYFinanceAdapterSearch:
    """Test suite for YFinanceAdapter search functionality."""

    @pytest.fixture
    def adapter(self):
        """Create a YFinanceAdapter instance for testing."""
        with patch('valuecell.adapters.assets.yfinance_adapter.yf') as mock_yf:
            mock_yf.Ticker.return_value.info = {"symbol": "AAPL"}
            adapter = YFinanceAdapter()
            return adapter

    @pytest.fixture
    def sample_search_query(self):
        """Create a sample search query for testing."""
        return AssetSearchQuery(
            query="Apple",
            asset_types=[AssetType.STOCK],
            limit=10,
            language="en-US"
        )

    @pytest.fixture
    def mock_search_quotes(self):
        """Mock search results from yfinance.Search."""
        return [
            {
                "symbol": "AAPL",
                "shortname": "Apple Inc.",
                "longname": "Apple Inc.",
                "quoteType": "EQUITY",
                "exchange": "NMS",
                "currency": "USD",
                "marketCap": 3000000000000,  # 3T market cap
            },
            {
                "symbol": "APPL",
                "shortname": "Appleton Papers Inc",
                "longname": "Appleton Papers Inc.",
                "quoteType": "EQUITY",
                "exchange": "NYQ",
                "currency": "USD",
                "marketCap": 1000000000,  # 1B market cap
            },
            {
                "symbol": "MSFT",
                "shortname": "Microsoft Corporation",
                "longname": "Microsoft Corporation",
                "quoteType": "EQUITY",
                "exchange": "NMS",
                "currency": "USD",
                "marketCap": 2800000000000,  # 2.8T market cap
            }
        ]

    def test_search_assets_with_yfinance_search_success(self, adapter, sample_search_query, mock_search_quotes):
        """Test successful search using yfinance.Search API."""
        with patch('valuecell.adapters.assets.yfinance_adapter.yf') as mock_yf:
            # Mock the Search object
            mock_search = Mock()
            mock_search.quotes = mock_search_quotes
            mock_yf.Search.return_value = mock_search
            
            # Perform search
            results = adapter.search_assets(sample_search_query)
            
            # Verify results
            assert len(results) > 0
            assert isinstance(results[0], AssetSearchResult)
            
            # Check that yfinance.Search was called
            mock_yf.Search.assert_called_once_with("Apple")
            
            # Verify first result (should be AAPL with highest relevance)
            first_result = results[0]
            assert first_result.ticker == "NASDAQ:AAPL"
            assert first_result.asset_type == AssetType.STOCK
            assert "Apple Inc." in first_result.names["en-US"]
            assert first_result.exchange == "NASDAQ"
            assert first_result.currency == "USD"
            assert first_result.relevance_score > 0.5

    def test_search_assets_fallback_to_direct_lookup(self, adapter, sample_search_query):
        """Test fallback to direct ticker lookup when Search API fails."""
        with patch('valuecell.adapters.assets.yfinance_adapter.yf') as mock_yf:
            # Mock Search to raise an exception
            mock_yf.Search.side_effect = Exception("Search API failed")
            
            # Mock direct ticker lookup
            mock_ticker = Mock()
            mock_ticker.info = {
                "symbol": "AAPL",
                "longName": "Apple Inc.",
                "shortName": "Apple Inc.",
                "quoteType": "EQUITY",
                "exchange": "NASDAQ",
                "currency": "USD",
                "country": "US"
            }
            mock_yf.Ticker.return_value = mock_ticker
            
            # Update query to search for specific ticker
            sample_search_query.query = "AAPL"
            
            # Perform search
            results = adapter.search_assets(sample_search_query)
            
            # Verify fallback was used
            assert len(results) > 0
            mock_yf.Ticker.assert_called()

    def test_search_assets_with_filters(self, adapter, mock_search_quotes):
        """Test search with various filters applied."""
        with patch('valuecell.adapters.assets.yfinance_adapter.yf') as mock_yf:
            mock_search = Mock()
            mock_search.quotes = mock_search_quotes
            mock_yf.Search.return_value = mock_search
            
            # Test with asset type filter
            query = AssetSearchQuery(
                query="Apple",
                asset_types=[AssetType.ETF],  # Filter for ETF only
                limit=10,
                language="en-US"
            )
            
            results = adapter.search_assets(query)
            
            # Should return no results since all mock results are stocks
            assert len(results) == 0

    def test_search_assets_with_exchange_filter(self, adapter, mock_search_quotes):
        """Test search with exchange filter."""
        with patch('valuecell.adapters.assets.yfinance_adapter.yf') as mock_yf:
            mock_search = Mock()
            mock_search.quotes = mock_search_quotes
            mock_yf.Search.return_value = mock_search
            
            # Test with exchange filter
            query = AssetSearchQuery(
                query="Apple",
                exchanges=["NYSE"],  # Filter for NYSE only
                limit=10,
                language="en-US"
            )
            
            results = adapter.search_assets(query)
            
            # Should return only NYSE results
            for result in results:
                assert result.exchange == "NYSE"

    def test_search_assets_with_country_filter(self, adapter, mock_search_quotes):
        """Test search with country filter."""
        with patch('valuecell.adapters.assets.yfinance_adapter.yf') as mock_yf:
            mock_search = Mock()
            # Add international stock to mock data
            international_quotes = mock_search_quotes + [{
                "symbol": "0700.HK",
                "shortname": "Tencent Holdings Ltd",
                "longname": "Tencent Holdings Limited",
                "quoteType": "EQUITY",
                "exchange": "HKG",
                "currency": "HKD",
                "marketCap": 500000000000,
            }]
            mock_search.quotes = international_quotes
            mock_yf.Search.return_value = mock_search
            
            # Test with country filter
            query = AssetSearchQuery(
                query="Tencent",
                countries=["HK"],  # Filter for Hong Kong only
                limit=10,
                language="en-US"
            )
            
            results = adapter.search_assets(query)
            
            # Should return only HK results
            for result in results:
                assert result.country == "HK"

    def test_search_assets_limit_results(self, adapter, mock_search_quotes):
        """Test that search respects the limit parameter."""
        with patch('valuecell.adapters.assets.yfinance_adapter.yf') as mock_yf:
            mock_search = Mock()
            mock_search.quotes = mock_search_quotes
            mock_yf.Search.return_value = mock_search
            
            # Test with small limit
            query = AssetSearchQuery(
                query="Apple",
                limit=2,
                language="en-US"
            )
            
            results = adapter.search_assets(query)
            
            # Should return at most 2 results
            assert len(results) <= 2

    def test_search_assets_relevance_scoring(self, adapter, mock_search_quotes):
        """Test that results are sorted by relevance score."""
        with patch('valuecell.adapters.assets.yfinance_adapter.yf') as mock_yf:
            mock_search = Mock()
            mock_search.quotes = mock_search_quotes
            mock_yf.Search.return_value = mock_search
            
            query = AssetSearchQuery(
                query="Apple",
                limit=10,
                language="en-US"
            )
            
            results = adapter.search_assets(query)
            
            # Results should be sorted by relevance (highest first)
            if len(results) > 1:
                for i in range(len(results) - 1):
                    assert results[i].relevance_score >= results[i + 1].relevance_score

    def test_create_search_result_from_quote(self, adapter):
        """Test creation of search result from quote data."""
        quote = {
            "symbol": "AAPL",
            "shortname": "Apple Inc.",
            "longname": "Apple Inc.",
            "quoteType": "EQUITY",
            "exchange": "NMS",
            "currency": "USD",
            "marketCap": 3000000000000,
        }
        
        result = adapter._create_search_result_from_quote(quote, "en-US")
        
        assert result is not None
        assert result.ticker == "NASDAQ:AAPL"
        assert result.asset_type == AssetType.STOCK
        assert result.names["en-US"] == "Apple Inc."
        assert result.exchange == "NASDAQ"
        assert result.currency == "USD"
        assert result.relevance_score > 0

    def test_create_search_result_from_quote_invalid(self, adapter):
        """Test handling of invalid quote data."""
        invalid_quote = {}  # Empty quote
        
        result = adapter._create_search_result_from_quote(invalid_quote, "en-US")
        
        assert result is None

    def test_calculate_search_relevance(self, adapter):
        """Test relevance score calculation."""
        # High relevance quote (exact match, large market cap)
        high_relevance_quote = {
            "symbol": "AAPL",
            "longname": "Apple Inc.",
            "currency": "USD",
            "exchange": "NMS",
            "marketCap": 3000000000000,
        }
        
        score = adapter._calculate_search_relevance(high_relevance_quote, "AAPL", "Apple Inc.")
        assert score > 0.8  # Should be high relevance
        
        # Low relevance quote (no match, small market cap)
        low_relevance_quote = {
            "symbol": "UNKNOWN",
            "marketCap": 1000000,
        }
        
        score = adapter._calculate_search_relevance(low_relevance_quote, "AAPL", "Apple Inc.")
        assert score < 0.7  # Should be lower relevance

    def test_fallback_ticker_search(self, adapter):
        """Test fallback ticker search functionality."""
        with patch('valuecell.adapters.assets.yfinance_adapter.yf') as mock_yf:
            # Mock ticker info
            mock_ticker = Mock()
            mock_ticker.info = {
                "symbol": "AAPL",
                "longName": "Apple Inc.",
                "shortName": "Apple Inc.",
                "quoteType": "EQUITY",
                "exchange": "NASDAQ",
                "currency": "USD",
                "country": "US"
            }
            mock_yf.Ticker.return_value = mock_ticker
            
            query = AssetSearchQuery(
                query="AAPL",
                limit=10,
                language="en-US"
            )
            
            results = adapter._fallback_ticker_search("AAPL", query)
            
            assert len(results) > 0
            assert results[0].ticker.endswith("AAPL")

    def test_fallback_ticker_search_with_suffixes(self, adapter):
        """Test fallback search with international market suffixes."""
        with patch('valuecell.adapters.assets.yfinance_adapter.yf') as mock_yf:
            # Mock first call to fail, second call with suffix to succeed
            def mock_ticker_side_effect(symbol):
                mock_ticker = Mock()
                if symbol == "0700":
                    mock_ticker.info = {}  # Empty info (failure)
                elif symbol == "0700.HK":
                    mock_ticker.info = {
                        "symbol": "0700.HK",
                        "longName": "Tencent Holdings Limited",
                        "shortName": "Tencent",
                        "quoteType": "EQUITY",
                        "exchange": "HKG",
                        "currency": "HKD",
                        "country": "HK"
                    }
                else:
                    mock_ticker.info = {}
                return mock_ticker
            
            mock_yf.Ticker.side_effect = mock_ticker_side_effect
            
            query = AssetSearchQuery(
                query="0700",
                limit=10,
                language="en-US"
            )
            
            results = adapter._fallback_ticker_search("0700", query)
            
            assert len(results) > 0
            # Should find the HK version
            found_hk = any("HK" in result.ticker for result in results)
            assert found_hk

    def test_search_assets_empty_query(self, adapter):
        """Test search with empty query."""
        query = AssetSearchQuery(
            query="",
            limit=10,
            language="en-US"
        )
        
        with patch('valuecell.adapters.assets.yfinance_adapter.yf') as mock_yf:
            mock_search = Mock()
            mock_search.quotes = []
            mock_yf.Search.return_value = mock_search
            
            results = adapter.search_assets(query)
            
            # Should return empty results for empty query
            assert len(results) == 0

    def test_search_assets_no_results(self, adapter):
        """Test search when no results are found."""
        query = AssetSearchQuery(
            query="NONEXISTENTSTOCK",
            limit=10,
            language="en-US"
        )
        
        with patch('valuecell.adapters.assets.yfinance_adapter.yf') as mock_yf:
            # Mock Search to return empty results
            mock_search = Mock()
            mock_search.quotes = []
            mock_yf.Search.return_value = mock_search
            
            # Mock direct ticker lookup to also fail
            mock_ticker = Mock()
            mock_ticker.info = {}
            mock_yf.Ticker.return_value = mock_ticker
            
            results = adapter.search_assets(query)
            
            assert len(results) == 0

    @pytest.mark.parametrize("exchange_code,expected_exchange", [
        ("NMS", "NASDAQ"),
        ("NYQ", "NYSE"),
        ("ASE", "AMEX"),
        ("HKG", "HKEX"),
        ("TYO", "TSE"),
        ("LSE", "LSE"),
    ])
    def test_exchange_mapping(self, adapter, exchange_code, expected_exchange):
        """Test exchange code mapping from yfinance to internal format."""
        quote = {
            "symbol": "TEST",
            "shortname": "Test Company",
            "longname": "Test Company Inc.",
            "quoteType": "EQUITY",
            "exchange": exchange_code,
            "currency": "USD",
        }
        
        result = adapter._create_search_result_from_quote(quote, "en-US")
        
        assert result is not None
        assert result.exchange == expected_exchange

    def test_search_with_crypto_assets(self, adapter):
        """Test search functionality with cryptocurrency assets."""
        crypto_quotes = [
            {
                "symbol": "BTC-USD",
                "shortname": "Bitcoin",
                "longname": "Bitcoin USD",
                "quoteType": "CRYPTOCURRENCY",
                "exchange": "CCC",
                "currency": "USD",
                "marketCap": 800000000000,
            }
        ]
        
        with patch('valuecell.adapters.assets.yfinance_adapter.yf') as mock_yf:
            mock_search = Mock()
            mock_search.quotes = crypto_quotes
            mock_yf.Search.return_value = mock_search
            
            query = AssetSearchQuery(
                query="Bitcoin",
                asset_types=[AssetType.CRYPTO],
                limit=10,
                language="en-US"
            )
            
            results = adapter.search_assets(query)
            
            assert len(results) > 0
            assert results[0].asset_type == AssetType.CRYPTO
            assert "Bitcoin" in results[0].names["en-US"]

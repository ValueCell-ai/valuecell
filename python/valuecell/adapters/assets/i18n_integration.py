"""Integration with ValueCell i18n system for asset localization.

This module provides integration with the existing i18n infrastructure to support
localized asset names, descriptions, and other text content.
"""

import logging
from typing import Dict, List, Optional

from ...server.api.i18n_api import get_i18n_service, t, get_i18n_config
from ...server.config.i18n import I18nConfig
from .types import Asset, AssetSearchResult, AssetType, MarketStatus
from .manager import AdapterManager

logger = logging.getLogger(__name__)


class AssetI18nService:
    """Service for handling asset internationalization."""

    def __init__(self, adapter_manager: AdapterManager):
        """Initialize asset i18n service.

        Args:
            adapter_manager: Asset adapter manager instance
        """
        self.adapter_manager = adapter_manager
        self.i18n_service = get_i18n_service()

        # Cache for translated asset names
        self._name_cache: Dict[str, Dict[str, str]] = {}  # ticker -> language -> name

        # Known translations for common assets
        self._predefined_translations = self._load_predefined_translations()

        logger.info("Asset i18n service initialized")

    def _load_predefined_translations(self) -> Dict[str, Dict[str, str]]:
        """Load predefined translations for common assets.

        Returns:
            Dictionary mapping tickers to language-name mappings
        """
        return {
            # US Tech Stocks
            "NASDAQ:AAPL": {
                "en-US": "Apple Inc.",
                "en-GB": "Apple Inc.",
                "zh-Hans": "苹果公司",
                "zh-Hant": "蘋果公司",
            },
            "NASDAQ:MSFT": {
                "en-US": "Microsoft Corporation",
                "en-GB": "Microsoft Corporation",
                "zh-Hans": "微软公司",
                "zh-Hant": "微軟公司",
            },
            "NASDAQ:GOOGL": {
                "en-US": "Alphabet Inc.",
                "en-GB": "Alphabet Inc.",
                "zh-Hans": "谷歌",
                "zh-Hant": "谷歌",
            },
            "NASDAQ:AMZN": {
                "en-US": "Amazon.com Inc.",
                "en-GB": "Amazon.com Inc.",
                "zh-Hans": "亚马逊",
                "zh-Hant": "亞馬遜",
            },
            "NASDAQ:TSLA": {
                "en-US": "Tesla Inc.",
                "en-GB": "Tesla Inc.",
                "zh-Hans": "特斯拉",
                "zh-Hant": "特斯拉",
            },
            "NASDAQ:META": {
                "en-US": "Meta Platforms Inc.",
                "en-GB": "Meta Platforms Inc.",
                "zh-Hans": "Meta平台",
                "zh-Hant": "Meta平台",
            },
            "NASDAQ:NVDA": {
                "en-US": "NVIDIA Corporation",
                "en-GB": "NVIDIA Corporation",
                "zh-Hans": "英伟达",
                "zh-Hant": "輝達",
            },
            "NYSE:JPM": {
                "en-US": "JPMorgan Chase & Co",
                "en-GB": "JPMorgan Chase & Co",
                "zh-Hans": "摩根大通",
                "zh-Hant": "摩根大通",
            },
            "NYSE:JNJ": {
                "en-US": "Johnson & Johnson",
                "en-GB": "Johnson & Johnson",
                "zh-Hans": "强生公司",
                "zh-Hant": "強生公司",
            },
            # Chinese Stocks
            "SSE:600519": {
                "en-US": "Kweichow Moutai Co Ltd",
                "zh-Hans": "贵州茅台",
                "zh-Hant": "貴州茅台",
            },
            "SZSE:000858": {
                "en-US": "Wuliangye Yibin Co Ltd",
                "zh-Hans": "五粮液",
                "zh-Hant": "五糧液",
            },
            "SSE:600036": {
                "en-US": "China Merchants Bank Co Ltd",
                "zh-Hans": "招商银行",
                "zh-Hant": "招商銀行",
            },
            "SZSE:000001": {
                "en-US": "Ping An Bank Co Ltd",
                "zh-Hans": "平安银行",
                "zh-Hant": "平安銀行",
            },
            "HKEX:00700": {
                "en-US": "Tencent Holdings Ltd",
                "zh-Hans": "腾讯控股",
                "zh-Hant": "騰訊控股",
            },
            "HKEX:09988": {
                "en-US": "Alibaba Group Holding Ltd",
                "zh-Hans": "阿里巴巴集团",
                "zh-Hant": "阿里巴巴集團",
            },
            # Cryptocurrencies
            "CRYPTO:BTC": {
                "en-US": "Bitcoin",
                "zh-Hans": "比特币",
                "zh-Hant": "比特幣",
            },
            "CRYPTO:ETH": {
                "en-US": "Ethereum",
                "zh-Hans": "以太坊",
                "zh-Hant": "以太坊",
            },
            "CRYPTO:USDT": {
                "en-US": "Tether",
                "zh-Hans": "泰达币",
                "zh-Hant": "泰達幣",
            },
            "CRYPTO:BNB": {
                "en-US": "Binance Coin",
                "zh-Hans": "币安币",
                "zh-Hant": "幣安幣",
            },
        }

    def get_localized_asset_name(
        self, ticker: str, language: Optional[str] = None
    ) -> str:
        """Get localized name for an asset.

        Args:
            ticker: Asset ticker in internal format
            language: Target language code (uses current i18n config if None)

        Returns:
            Localized asset name or ticker if no translation available
        """
        if language is None:
            config = get_i18n_config()
            language = config.language

        # Check cache first
        if ticker in self._name_cache and language in self._name_cache[ticker]:
            return self._name_cache[ticker][language]

        # Check predefined translations
        if ticker in self._predefined_translations:
            translations = self._predefined_translations[ticker]
            if language in translations:
                # Cache the result
                if ticker not in self._name_cache:
                    self._name_cache[ticker] = {}
                self._name_cache[ticker][language] = translations[language]
                return translations[language]

        # Try to get from asset data
        try:
            asset = self.adapter_manager.get_asset_info(ticker)
            if asset:
                name = asset.get_localized_name(language)
                if name:
                    # Cache the result
                    if ticker not in self._name_cache:
                        self._name_cache[ticker] = {}
                    self._name_cache[ticker][language] = name
                    return name
        except Exception as e:
            logger.warning(f"Could not fetch asset info for {ticker}: {e}")

        # Fallback to ticker
        return ticker

    def localize_asset(self, asset: Asset, language: Optional[str] = None) -> Asset:
        """Add localized names to an asset object.

        Args:
            asset: Asset to localize
            language: Target language (uses current i18n config if None)

        Returns:
            Asset with localized names added
        """
        if language is None:
            config = get_i18n_config()
            language = config.language

        # Check if we have predefined translations
        if asset.ticker in self._predefined_translations:
            translations = self._predefined_translations[asset.ticker]
            for lang, name in translations.items():
                asset.set_localized_name(lang, name)

        return asset

    def localize_search_results(
        self, results: List[AssetSearchResult], language: Optional[str] = None
    ) -> List[AssetSearchResult]:
        """Add localized names to search results.

        Args:
            results: Search results to localize
            language: Target language (uses current i18n config if None)

        Returns:
            Search results with localized names
        """
        if language is None:
            config = get_i18n_config()
            language = config.language

        for result in results:
            localized_name = self.get_localized_asset_name(result.ticker, language)
            if localized_name != result.ticker:
                result.names[language] = localized_name

        return results

    def get_asset_type_display_name(
        self, asset_type: AssetType, language: Optional[str] = None
    ) -> str:
        """Get localized display name for asset type.

        Args:
            asset_type: Asset type
            language: Target language (uses current i18n config if None)

        Returns:
            Localized asset type name
        """
        if language is None:
            config = get_i18n_config()
            language = config.language

        # Use i18n service to translate asset type
        key = f"assets.types.{asset_type.value}"
        return t(key, default=asset_type.value.replace("_", " ").title())

    def get_market_status_display_name(
        self, status: MarketStatus, language: Optional[str] = None
    ) -> str:
        """Get localized display name for market status.

        Args:
            status: Market status
            language: Target language (uses current i18n config if None)

        Returns:
            Localized market status name
        """
        if language is None:
            config = get_i18n_config()
            language = config.language

        # Use i18n service to translate market status
        key = f"assets.market_status.{status.value}"
        return t(key, default=status.value.replace("_", " ").title())

    def format_currency_amount(
        self, amount: float, currency: str, language: Optional[str] = None
    ) -> str:
        """Format currency amount according to locale.

        Args:
            amount: Amount to format
            currency: Currency code
            language: Target language (uses current i18n config if None)

        Returns:
            Formatted currency string
        """
        if language is None:
            config = get_i18n_config()
        else:
            config = I18nConfig(language=language)

        # Use the existing i18n currency formatting
        if currency == "USD":
            return f"${config.format_number(amount, 2)}"
        elif currency == "CNY":
            if language and language.startswith("zh"):
                return f"¥{config.format_number(amount, 2)}"
            else:
                return f"CN¥{config.format_number(amount, 2)}"
        elif currency == "HKD":
            return f"HK${config.format_number(amount, 2)}"
        elif currency == "JPY":
            return f"¥{config.format_number(amount, 0)}"
        elif currency == "EUR":
            return f"€{config.format_number(amount, 2)}"
        elif currency == "GBP":
            return f"£{config.format_number(amount, 2)}"
        else:
            return f"{currency} {config.format_number(amount, 2)}"

    def format_percentage_change(
        self, change_percent: float, language: Optional[str] = None
    ) -> str:
        """Format percentage change with appropriate styling.

        Args:
            change_percent: Percentage change value
            language: Target language (uses current i18n config if None)

        Returns:
            Formatted percentage string
        """
        if language is None:
            config = get_i18n_config()
        else:
            config = I18nConfig(language=language)

        # Format with + or - sign
        formatted_percent = config.format_number(abs(change_percent), 2)

        if change_percent > 0:
            return f"+{formatted_percent}%"
        elif change_percent < 0:
            return f"-{formatted_percent}%"
        else:
            return f"{formatted_percent}%"

    def format_market_cap(
        self, market_cap: float, currency: str = "USD", language: Optional[str] = None
    ) -> str:
        """Format market capitalization with appropriate units.

        Args:
            market_cap: Market capitalization value
            currency: Currency code
            language: Target language (uses current i18n config if None)

        Returns:
            Formatted market cap string
        """
        if language is None:
            config = get_i18n_config()
        else:
            config = I18nConfig(language=language)

        # Determine appropriate unit
        if market_cap >= 1e12:  # Trillion
            value = market_cap / 1e12
            unit = t("units.trillion", default="T")
        elif market_cap >= 1e9:  # Billion
            value = market_cap / 1e9
            unit = t("units.billion", default="B")
        elif market_cap >= 1e6:  # Million
            value = market_cap / 1e6
            unit = t("units.million", default="M")
        elif market_cap >= 1e3:  # Thousand
            value = market_cap / 1e3
            unit = t("units.thousand", default="K")
        else:
            value = market_cap
            unit = ""

        formatted_value = config.format_number(value, 1 if value >= 10 else 2)

        # Format with currency
        if currency == "USD":
            return f"${formatted_value}{unit}"
        elif currency == "CNY":
            if language and language.startswith("zh"):
                return f"¥{formatted_value}{unit}"
            else:
                return f"CN¥{formatted_value}{unit}"
        else:
            return f"{currency} {formatted_value}{unit}"

    def add_asset_translation(self, ticker: str, language: str, name: str) -> None:
        """Add a custom translation for an asset.

        Args:
            ticker: Asset ticker in internal format
            language: Language code
            name: Localized asset name
        """
        if ticker not in self._predefined_translations:
            self._predefined_translations[ticker] = {}

        self._predefined_translations[ticker][language] = name

        # Update cache
        if ticker not in self._name_cache:
            self._name_cache[ticker] = {}
        self._name_cache[ticker][language] = name

        logger.info(f"Added translation for {ticker} in {language}: {name}")

    def clear_cache(self) -> None:
        """Clear the translation cache."""
        self._name_cache.clear()
        logger.info("Asset translation cache cleared")

    def get_available_languages_for_asset(self, ticker: str) -> List[str]:
        """Get list of available languages for an asset.

        Args:
            ticker: Asset ticker in internal format

        Returns:
            List of available language codes
        """
        languages = set()

        # Check predefined translations
        if ticker in self._predefined_translations:
            languages.update(self._predefined_translations[ticker].keys())

        # Check asset data
        try:
            asset = self.adapter_manager.get_asset_info(ticker)
            if asset:
                languages.update(asset.names.get_available_languages())
        except Exception as e:
            logger.warning(f"Could not fetch asset info for {ticker}: {e}")

        return list(languages)


# Global instance
_asset_i18n_service: Optional[AssetI18nService] = None


def get_asset_i18n_service() -> AssetI18nService:
    """Get global asset i18n service instance."""
    global _asset_i18n_service
    if _asset_i18n_service is None:
        from .manager import get_adapter_manager

        _asset_i18n_service = AssetI18nService(get_adapter_manager())
    return _asset_i18n_service


def reset_asset_i18n_service() -> None:
    """Reset global asset i18n service instance (mainly for testing)."""
    global _asset_i18n_service
    _asset_i18n_service = None

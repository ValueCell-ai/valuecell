"""I18n service for ValueCell Server."""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from pathlib import Path

from ...config.logging import get_logger
from ...config.settings import get_settings

logger = get_logger(__name__)


class I18nService:
    """Service for handling internationalization."""
    
    def __init__(self, db: Session):
        """Initialize i18n service."""
        self.db = db
        self.settings = get_settings()
        self._translations = {}
        self._load_translations()
    
    def _load_translations(self) -> None:
        """Load translation files."""
        try:
            # Define supported languages
            self.supported_languages = {
                "en-US": {"name": "English (US)", "native_name": "English"},
                "zh-Hans": {"name": "Chinese (Simplified)", "native_name": "简体中文"},
                "zh-Hant": {"name": "Chinese (Traditional)", "native_name": "繁體中文"},
                "ja-JP": {"name": "Japanese", "native_name": "日本語"},
                "ko-KR": {"name": "Korean", "native_name": "한국어"},
            }
            
            # Define supported timezones
            self.supported_timezones = [
                "UTC",
                "America/New_York",
                "America/Los_Angeles",
                "Europe/London",
                "Europe/Paris",
                "Asia/Shanghai",
                "Asia/Tokyo",
                "Asia/Seoul",
                "Australia/Sydney",
            ]
            
            # Load basic translations (in production, these would come from files)
            self._translations = {
                "en-US": {
                    "welcome": "Welcome to ValueCell",
                    "error.not_found": "Resource not found",
                    "error.internal": "Internal server error",
                    "success.created": "Resource created successfully",
                    "success.updated": "Resource updated successfully",
                    "success.deleted": "Resource deleted successfully",
                },
                "zh-Hans": {
                    "welcome": "欢迎使用ValueCell",
                    "error.not_found": "资源未找到",
                    "error.internal": "内部服务器错误",
                    "success.created": "资源创建成功",
                    "success.updated": "资源更新成功",
                    "success.deleted": "资源删除成功",
                },
                "zh-Hant": {
                    "welcome": "歡迎使用ValueCell",
                    "error.not_found": "資源未找到",
                    "error.internal": "內部伺服器錯誤",
                    "success.created": "資源創建成功",
                    "success.updated": "資源更新成功",
                    "success.deleted": "資源刪除成功",
                },
            }
            
            logger.info("Translations loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading translations: {e}")
            # Fallback to minimal English translations
            self._translations = {
                "en-US": {
                    "welcome": "Welcome to ValueCell",
                    "error.not_found": "Resource not found",
                    "error.internal": "Internal server error",
                }
            }
    
    async def get_supported_languages(self) -> Dict[str, Any]:
        """Get list of supported languages."""
        return {
            "languages": self.supported_languages,
            "default": self.settings.DEFAULT_LANGUAGE
        }
    
    async def get_supported_timezones(self) -> Dict[str, Any]:
        """Get list of supported timezones."""
        return {
            "timezones": self.supported_timezones,
            "default": self.settings.DEFAULT_TIMEZONE
        }
    
    async def get_user_config(self, user_id: Optional[str]) -> Dict[str, Any]:
        """Get i18n configuration for user."""
        # In a real implementation, this would fetch from database
        # For now, return default configuration
        return {
            "language": self.settings.DEFAULT_LANGUAGE,
            "timezone": self.settings.DEFAULT_TIMEZONE,
            "date_format": "YYYY-MM-DD",
            "time_format": "HH:mm:ss",
            "currency": "USD",
            "number_format": {
                "decimal_separator": ".",
                "thousands_separator": ",",
                "decimal_places": 2
            }
        }
    
    async def set_user_language(self, user_id: Optional[str], language: str) -> Dict[str, Any]:
        """Set user language preference."""
        if language not in self.supported_languages:
            raise ValueError(f"Unsupported language: {language}")
        
        # In a real implementation, this would save to database
        logger.info(f"Setting language to {language} for user {user_id}")
        
        return {
            "language": language,
            "message": f"Language set to {language}"
        }
    
    async def set_user_timezone(self, user_id: Optional[str], timezone: str) -> Dict[str, Any]:
        """Set user timezone preference."""
        if timezone not in self.supported_timezones:
            raise ValueError(f"Unsupported timezone: {timezone}")
        
        # In a real implementation, this would save to database
        logger.info(f"Setting timezone to {timezone} for user {user_id}")
        
        return {
            "timezone": timezone,
            "message": f"Timezone set to {timezone}"
        }
    
    async def detect_language(self, accept_language: str) -> Dict[str, Any]:
        """Detect language from Accept-Language header."""
        # Simple language detection logic
        # In production, use a proper language detection library
        
        languages = accept_language.lower().split(",")
        detected_language = self.settings.DEFAULT_LANGUAGE
        
        for lang in languages:
            lang = lang.strip().split(";")[0]  # Remove quality values
            if lang in self.supported_languages:
                detected_language = lang
                break
            # Check for language family matches
            elif lang.startswith("zh"):
                detected_language = "zh-Hans"
                break
            elif lang.startswith("en"):
                detected_language = "en-US"
                break
        
        return {
            "detected_language": detected_language,
            "confidence": 0.8,  # Mock confidence score
            "supported": detected_language in self.supported_languages
        }
    
    async def translate(self, key: str, language: str, variables: Optional[Dict[str, Any]] = None) -> str:
        """Translate a key to target language."""
        if language not in self.supported_languages:
            language = self.settings.DEFAULT_LANGUAGE
        
        translations = self._translations.get(language, self._translations.get(self.settings.DEFAULT_LANGUAGE, {}))
        translation = translations.get(key, key)
        
        # Simple variable substitution
        if variables:
            for var_key, var_value in variables.items():
                translation = translation.replace(f"{{{var_key}}}", str(var_value))
        
        return translation
    
    async def format_datetime(self, datetime_str: str, format_type: str, user_id: Optional[str] = None) -> str:
        """Format datetime according to user preferences."""
        try:
            # Parse datetime string
            dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
            
            # Get user config (in real implementation, from database)
            config = await self.get_user_config(user_id)
            
            # Format based on type
            if format_type == "date":
                return dt.strftime("%Y-%m-%d")
            elif format_type == "time":
                return dt.strftime("%H:%M:%S")
            elif format_type == "datetime":
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                return dt.isoformat()
                
        except Exception as e:
            logger.error(f"Error formatting datetime: {e}")
            return datetime_str
    
    async def format_number(self, number: float, decimal_places: Optional[int] = None, user_id: Optional[str] = None) -> str:
        """Format number according to user preferences."""
        try:
            config = await self.get_user_config(user_id)
            number_format = config.get("number_format", {})
            
            if decimal_places is None:
                decimal_places = number_format.get("decimal_places", 2)
            
            # Format number
            formatted = f"{number:,.{decimal_places}f}"
            
            # Apply user preferences
            decimal_sep = number_format.get("decimal_separator", ".")
            thousands_sep = number_format.get("thousands_separator", ",")
            
            if decimal_sep != ".":
                formatted = formatted.replace(".", "__DECIMAL__")
            if thousands_sep != ",":
                formatted = formatted.replace(",", thousands_sep)
            if decimal_sep != ".":
                formatted = formatted.replace("__DECIMAL__", decimal_sep)
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error formatting number: {e}")
            return str(number)
    
    async def format_currency(self, amount: float, decimal_places: Optional[int] = None, user_id: Optional[str] = None) -> str:
        """Format currency according to user preferences."""
        try:
            config = await self.get_user_config(user_id)
            currency = config.get("currency", "USD")
            
            # Format as number first
            formatted_number = await self.format_number(amount, decimal_places, user_id)
            
            # Add currency symbol
            currency_symbols = {
                "USD": "$",
                "EUR": "€",
                "GBP": "£",
                "JPY": "¥",
                "CNY": "¥",
                "KRW": "₩"
            }
            
            symbol = currency_symbols.get(currency, currency)
            return f"{symbol}{formatted_number}"
            
        except Exception as e:
            logger.error(f"Error formatting currency: {e}")
            return str(amount)
    
    async def get_user_settings(self, user_id: str) -> Dict[str, Any]:
        """Get user i18n settings."""
        # In real implementation, fetch from database
        return await self.get_user_config(user_id)
    
    async def update_user_settings(self, user_id: str, language: Optional[str] = None, timezone: Optional[str] = None) -> Dict[str, Any]:
        """Update user i18n settings."""
        settings = {}
        
        if language:
            if language not in self.supported_languages:
                raise ValueError(f"Unsupported language: {language}")
            settings["language"] = language
        
        if timezone:
            if timezone not in self.supported_timezones:
                raise ValueError(f"Unsupported timezone: {timezone}")
            settings["timezone"] = timezone
        
        # In real implementation, save to database
        logger.info(f"Updated settings for user {user_id}: {settings}")
        
        # Return updated config
        config = await self.get_user_config(user_id)
        config.update(settings)
        return config
    
    async def get_agent_context(self, user_id: Optional[str], session_id: Optional[str]) -> Dict[str, Any]:
        """Get i18n context for agent execution."""
        config = await self.get_user_config(user_id)
        
        return {
            "user_id": user_id,
            "session_id": session_id,
            "language": config["language"],
            "timezone": config["timezone"],
            "locale_info": {
                "date_format": config["date_format"],
                "time_format": config["time_format"],
                "currency": config["currency"],
                "number_format": config["number_format"]
            },
            "translations": self._translations.get(config["language"], {})
        }
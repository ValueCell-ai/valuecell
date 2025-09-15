"""I18n schemas for ValueCell Server."""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator


class I18nConfigResponse(BaseModel):
    """I18n configuration response."""

    language: str
    timezone: str
    date_format: str
    time_format: str
    datetime_format: str
    currency_symbol: str
    number_format: Dict[str, str]
    is_rtl: bool


class SupportedLanguage(BaseModel):
    """Supported language schema."""

    code: str
    name: str
    is_current: bool


class SupportedLanguagesResponse(BaseModel):
    """Supported languages response."""

    languages: List[SupportedLanguage]
    current: str


class TimezoneInfo(BaseModel):
    """Timezone information schema."""

    value: str
    label: str
    is_current: bool


class TimezonesResponse(BaseModel):
    """Timezones response."""

    timezones: List[TimezoneInfo]
    current: str


class LanguageRequest(BaseModel):
    """Language setting request."""

    language: str = Field(..., description="Language code to set")

    @validator("language")
    def validate_language(cls, v):
        """Validate language code."""
        # TODO: Add proper validation logic
        return v


class TimezoneRequest(BaseModel):
    """Timezone setting request."""

    timezone: str = Field(..., description="Timezone to set")


class LanguageDetectionRequest(BaseModel):
    """Language detection request."""

    accept_language: str = Field(..., description="Accept-Language header value")


class TranslationRequest(BaseModel):
    """Translation request."""

    key: str = Field(..., description="Translation key")
    language: Optional[str] = Field(None, description="Target language")
    variables: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Variables for string formatting"
    )


class DateTimeFormatRequest(BaseModel):
    """DateTime format request."""

    datetime: str = Field(..., description="ISO datetime string")
    format_type: str = Field(
        "datetime", description="Format type: date, time, or datetime"
    )


class NumberFormatRequest(BaseModel):
    """Number format request."""

    number: float = Field(..., description="Number to format")
    decimal_places: int = Field(2, description="Number of decimal places")


class CurrencyFormatRequest(BaseModel):
    """Currency format request."""

    amount: float = Field(..., description="Amount to format")
    decimal_places: int = Field(2, description="Number of decimal places")


class UserI18nSettings(BaseModel):
    """User i18n settings."""

    user_id: Optional[str] = None
    language: str = "en-US"
    timezone: str = "UTC"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @validator("language")
    def validate_language(cls, v):
        """Validate language code."""
        # TODO: Add proper validation logic
        return v


class UserI18nSettingsRequest(BaseModel):
    """User i18n settings update request."""

    language: Optional[str] = None
    timezone: Optional[str] = None

    @validator("language")
    def validate_language(cls, v):
        """Validate language code."""
        if v is not None:
            # TODO: Add proper validation logic
            pass
        return v


class AgentI18nContext(BaseModel):
    """Agent i18n context."""

    language: str
    timezone: str
    currency_symbol: str
    date_format: str
    time_format: str
    number_format: Dict[str, str]
    user_id: Optional[str] = None
    session_id: Optional[str] = None
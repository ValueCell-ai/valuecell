"""I18n related API schemas for ValueCell application."""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator

from ...core.constants import SUPPORTED_LANGUAGE_CODES


# I18n related data models
class I18nConfigData(BaseModel):
    """I18n configuration data model."""

    language: str = Field(..., description="Current language")
    timezone: str = Field(..., description="Current timezone")
    date_format: str = Field(..., description="Date format")
    time_format: str = Field(..., description="Time format")
    datetime_format: str = Field(..., description="DateTime format")
    currency_symbol: str = Field(..., description="Currency symbol")
    number_format: Dict[str, str] = Field(..., description="Number format")
    is_rtl: bool = Field(..., description="Whether text is right-to-left")


class SupportedLanguage(BaseModel):
    """Supported language schema."""

    code: str = Field(..., description="Language code")
    name: str = Field(..., description="Language name")
    is_current: bool = Field(..., description="Whether this is the current language")


class SupportedLanguagesData(BaseModel):
    """Supported languages data."""

    languages: List[SupportedLanguage] = Field(
        ..., description="List of supported languages"
    )
    current: str = Field(..., description="Current language code")


class TimezoneInfo(BaseModel):
    """Timezone information schema."""

    value: str = Field(..., description="Timezone value")
    label: str = Field(..., description="Timezone display name")
    is_current: bool = Field(..., description="Whether this is the current timezone")


class TimezonesData(BaseModel):
    """Timezones data."""

    timezones: List[TimezoneInfo] = Field(..., description="List of timezones")
    current: str = Field(..., description="Current timezone")


# API request models
class LanguageRequest(BaseModel):
    """Language change request."""

    language: str = Field(..., description="Language code to set")

    @validator("language")
    def validate_language(cls, v):
        if v not in SUPPORTED_LANGUAGE_CODES:
            raise ValueError(f"Language {v} is not supported")
        return v


class TimezoneRequest(BaseModel):
    """Timezone change request."""

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
    """DateTime formatting request."""

    datetime: str = Field(..., description="ISO datetime string")
    format_type: str = Field(
        "datetime", description="Format type: date, time, or datetime"
    )


class NumberFormatRequest(BaseModel):
    """Number formatting request."""

    number: float = Field(..., description="Number to format")
    decimal_places: int = Field(2, description="Number of decimal places")


class CurrencyFormatRequest(BaseModel):
    """Currency formatting request."""

    amount: float = Field(..., description="Amount to format")
    decimal_places: int = Field(2, description="Number of decimal places")


class UserI18nSettingsData(BaseModel):
    """User i18n settings data."""

    user_id: Optional[str] = Field(None, description="User ID")
    language: str = Field(default="en-US", description="User language")
    timezone: str = Field(default="UTC", description="User timezone")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Update timestamp")

    @validator("language")
    def validate_language(cls, v):
        if v not in SUPPORTED_LANGUAGE_CODES:
            raise ValueError(f"Language {v} is not supported")
        return v


class UserI18nSettingsRequest(BaseModel):
    """User i18n settings update request."""

    language: Optional[str] = Field(None, description="Language to update")
    timezone: Optional[str] = Field(None, description="Timezone to update")

    @validator("language")
    def validate_language(cls, v):
        if v and v not in SUPPORTED_LANGUAGE_CODES:
            raise ValueError(f"Language {v} is not supported")
        return v


class AgentI18nContextData(BaseModel):
    """Agent i18n context data for inter-agent communication."""

    language: str = Field(..., description="Language")
    timezone: str = Field(..., description="Timezone")
    currency_symbol: str = Field(..., description="Currency symbol")
    date_format: str = Field(..., description="Date format")
    time_format: str = Field(..., description="Time format")
    number_format: Dict[str, str] = Field(..., description="Number format")
    user_id: Optional[str] = Field(None, description="User ID")
    session_id: Optional[str] = Field(None, description="Session ID")


class LanguageDetectionData(BaseModel):
    """Language detection result data."""

    detected_language: str = Field(..., description="Detected language")
    language_name: str = Field(..., description="Language name")
    is_supported: bool = Field(..., description="Whether the language is supported")


class TranslationData(BaseModel):
    """Translation result data."""

    key: str = Field(..., description="Translation key")
    translated_text: str = Field(..., description="Translated text")
    language: str = Field(..., description="Target language")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Variables")


class DateTimeFormatData(BaseModel):
    """DateTime formatting result data."""

    original: str = Field(..., description="Original datetime")
    formatted: str = Field(..., description="Formatted datetime")
    format_type: str = Field(..., description="Format type")
    language: str = Field(..., description="Language")
    timezone: str = Field(..., description="Timezone")


class NumberFormatData(BaseModel):
    """Number formatting result data."""

    original: float = Field(..., description="Original number")
    formatted: str = Field(..., description="Formatted number")
    decimal_places: int = Field(..., description="Number of decimal places")
    language: str = Field(..., description="Language")


class CurrencyFormatData(BaseModel):
    """Currency formatting result data."""

    original: float = Field(..., description="Original amount")
    formatted: str = Field(..., description="Formatted amount")
    decimal_places: int = Field(..., description="Number of decimal places")
    language: str = Field(..., description="Language")
    currency_symbol: str = Field(..., description="Currency symbol")

"""API schemas for ValueCell application."""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator

from ..core.constants import SUPPORTED_LANGUAGE_CODES


class BaseResponse(BaseModel):
    """Base response schema."""

    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ErrorResponse(BaseResponse):
    """Error response schema."""

    success: bool = False
    error: str
    data: Optional[Dict[str, Any]] = None


class SuccessResponse(BaseResponse):
    """Success response schema."""

    success: bool = True
    data: Dict[str, Any]


# I18n related schemas
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


class UserI18nSettings(BaseModel):
    """User i18n settings schema."""

    user_id: Optional[str] = None
    language: str = "en-US"
    timezone: str = "UTC"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @validator("language")
    def validate_language(cls, v):
        if v not in SUPPORTED_LANGUAGE_CODES:
            raise ValueError(f"Language {v} is not supported")
        return v


class UserI18nSettingsRequest(BaseModel):
    """User i18n settings update request."""

    language: Optional[str] = None
    timezone: Optional[str] = None

    @validator("language")
    def validate_language(cls, v):
        if v and v not in SUPPORTED_LANGUAGE_CODES:
            raise ValueError(f"Language {v} is not supported")
        return v


class AgentI18nContext(BaseModel):
    """Agent i18n context schema for inter-agent communication."""

    language: str
    timezone: str
    currency_symbol: str
    date_format: str
    time_format: str
    number_format: Dict[str, str]
    user_id: Optional[str] = None
    session_id: Optional[str] = None

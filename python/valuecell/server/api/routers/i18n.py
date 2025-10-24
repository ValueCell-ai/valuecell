"""RESTful i18n API router module."""

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException

from ....config.constants import LANGUAGE_TIMEZONE_MAPPING, SUPPORTED_LANGUAGES
from ....utils.i18n_utils import (
    detect_browser_language,
    get_common_timezones,
    get_timezone_display_name,
    validate_language_code,
    validate_timezone,
)
from ...services.i18n_service import get_i18n_service
from ..exceptions import (
    APIException,
    InternalServerException,
)
from ..schemas import (  # Data models
    CurrencyFormatData,
    CurrencyFormatRequest,
    DateTimeFormatData,
    DateTimeFormatRequest,
    I18nConfigData,
    LanguageDetectionData,
    LanguageDetectionRequest,
    LanguageRequest,
    NumberFormatData,
    NumberFormatRequest,
    StatusCode,
    SuccessResponse,
    SupportedLanguagesData,
    TimezoneRequest,
    TimezonesData,
    TranslationData,
    TranslationRequest,
    UserI18nSettingsData,
    UserI18nSettingsRequest,
)


def create_i18n_router() -> APIRouter:
    """Create RESTful style i18n router.

    API path design:
    - GET /i18n/config - Get i18n configuration
    - GET /i18n/languages - Get supported languages list
    - PUT /i18n/language - Set language
    - GET /i18n/timezones - Get supported timezones list
    - PUT /i18n/timezone - Set timezone
    - POST /i18n/language/detect - Detect language
    - POST /i18n/translate - Translate text
    - POST /i18n/format/datetime - Format datetime
    - POST /i18n/format/number - Format number
    - POST /i18n/format/currency - Format currency
    - GET /i18n/users/{user_id}/settings - Get user i18n settings
    - PUT /i18n/users/{user_id}/settings - Update user i18n settings
    - GET /i18n/agents/context - Get Agent i18n context

    Returns:
        APIRouter: Configured i18n router
    """
    router = APIRouter(prefix="/i18n", tags=["i18n"])

    # Get services
    i18n_service = get_i18n_service()

    # User context storage (in production, use Redis or database)
    _user_contexts: Dict[str, Dict[str, Any]] = {}

    def _get_user_context(user_id: Optional[str]) -> Dict[str, Any]:
        """Get user context and apply to i18n service."""
        if user_id and user_id in _user_contexts:
            user_context = _user_contexts[user_id]
            i18n_service.set_language(user_context.get("language", "en-US"))
            i18n_service.set_timezone(user_context.get("timezone", "UTC"))
            return user_context
        return {"language": "en-US", "timezone": "UTC"}

    # Configuration endpoints
    @router.get(
        "/config",
        response_model=SuccessResponse[I18nConfigData],
        summary="Get i18n configuration",
        description="Get current internationalization configuration information",
    )
    async def get_config(
        user_id: Optional[str] = Header(None, alias="X-User-ID"),
        session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    ) -> SuccessResponse[I18nConfigData]:
        """Get current i18n configuration."""
        _get_user_context(user_id)

        config_dict = i18n_service.to_dict()
        config_data = I18nConfigData(**config_dict)

        return SuccessResponse.create(
            data=config_data, msg="I18n configuration retrieved successfully"
        )

    @router.get(
        "/languages",
        response_model=SuccessResponse[SupportedLanguagesData],
        summary="Get supported languages",
        description="Get list of all languages supported by the system",
    )
    async def get_supported_languages() -> SuccessResponse[SupportedLanguagesData]:
        """Get supported languages."""
        from ..schemas import SupportedLanguage

        languages = [
            SupportedLanguage(
                code=code,
                name=name,
                is_current=code == i18n_service.get_current_language(),
            )
            for code, name in SUPPORTED_LANGUAGES
        ]

        languages_data = SupportedLanguagesData(
            languages=languages, current=i18n_service.get_current_language()
        )

        return SuccessResponse.create(
            data=languages_data, msg="Supported languages retrieved successfully"
        )

    @router.get(
        "/timezones",
        response_model=SuccessResponse[TimezonesData],
        summary="Get supported timezones",
        description="Get list of all timezones supported by the system",
    )
    async def get_timezones() -> SuccessResponse:
        """Get available timezones."""
        common_timezones = get_common_timezones()
        timezone_list = [
            {
                "value": tz,
                "label": get_timezone_display_name(tz),
                "is_current": tz == i18n_service.get_current_timezone(),
            }
            for tz in common_timezones
        ]

        # Add language-specific timezones if not in common list
        for lang_tz in LANGUAGE_TIMEZONE_MAPPING.values():
            if lang_tz not in common_timezones:
                timezone_list.append(
                    {
                        "value": lang_tz,
                        "label": get_timezone_display_name(lang_tz),
                        "is_current": lang_tz == i18n_service.get_current_timezone(),
                    }
                )

        # Sort by label
        timezone_list.sort(key=lambda x: x["label"])

        return SuccessResponse(
            message="Timezones retrieved successfully",
            data={
                "timezones": timezone_list,
                "current": i18n_service.get_current_timezone(),
            },
        )

    # Language and timezone management
    @router.put(
        "/language",
        response_model=SuccessResponse[UserI18nSettingsData],
        summary="Set language",
        description="Set user's preferred language",
    )
    async def set_language(
        request: LanguageRequest,
        user_id: Optional[str] = Header(None, alias="X-User-ID"),
    ) -> SuccessResponse[UserI18nSettingsData]:
        """Set current language."""
        if not validate_language_code(request.language):
            raise APIException(
                code=StatusCode.BAD_REQUEST,
                message=f"Language '{request.language}' is not supported",
            )

        success = i18n_service.set_language(request.language)
        if not success:
            raise InternalServerException("Failed to set language")

        # Save user context
        if user_id:
            if user_id not in _user_contexts:
                _user_contexts[user_id] = {}
            _user_contexts[user_id]["language"] = request.language
            _user_contexts[user_id]["timezone"] = i18n_service.get_current_timezone()

        settings_data = UserI18nSettingsData(
            user_id=user_id,
            language=request.language,
            timezone=i18n_service.get_current_timezone(),
            updated_at=datetime.now(),
        )

        return SuccessResponse.create(
            data=settings_data, msg="Language setting successful"
        )

    @router.put(
        "/timezone",
        response_model=SuccessResponse[dict],
        summary="Set timezone",
        description="Set user's preferred timezone",
    )
    async def set_timezone(
        request: TimezoneRequest,
        user_id: Optional[str] = Header(None, alias="X-User-ID"),
    ) -> SuccessResponse:
        """Set current timezone."""
        if not validate_timezone(request.timezone):
            raise HTTPException(
                status_code=400, detail=f"Timezone '{request.timezone}' is not valid"
            )

        success = i18n_service.set_timezone(request.timezone)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to set timezone")

        # Save user context
        if user_id:
            if user_id not in _user_contexts:
                _user_contexts[user_id] = {}
            _user_contexts[user_id]["timezone"] = request.timezone

        return SuccessResponse(
            message="Timezone updated successfully",
            data={
                "timezone": request.timezone,
                "display_name": get_timezone_display_name(request.timezone),
            },
        )

    @router.post(
        "/detect-language",
        response_model=SuccessResponse[LanguageDetectionData],
        summary="Detect language",
        description="Detect user's preferred language based on Accept-Language header",
    )
    async def detect_language(
        request: LanguageDetectionRequest,
    ) -> SuccessResponse[LanguageDetectionData]:
        """Detect language from Accept-Language header."""
        detected_language = detect_browser_language(request.accept_language)

        language_name = next(
            (name for code, name in SUPPORTED_LANGUAGES if code == detected_language),
            detected_language,
        )

        detection_data = LanguageDetectionData(
            detected_language=detected_language,
            language_name=language_name,
            is_supported=detected_language in [code for code, _ in SUPPORTED_LANGUAGES],
        )

        return SuccessResponse.create(
            data=detection_data, msg="Language detection successful"
        )

    # Translation and formatting services
    @router.post(
        "/translate",
        response_model=SuccessResponse[TranslationData],
        summary="Translate text",
        description="Get translated text based on specified key and language",
    )
    async def translate(
        request: TranslationRequest,
    ) -> SuccessResponse[TranslationData]:
        """Translate a key."""
        try:
            translated_text = i18n_service.translate(
                request.key, request.language, **request.variables
            )

            translation_data = TranslationData(
                key=request.key,
                translated_text=translated_text,
                language=request.language or i18n_service.get_current_language(),
                variables=request.variables or {},
            )

            return SuccessResponse.create(
                data=translation_data, msg="Translation retrieved successfully"
            )
        except Exception as e:
            raise InternalServerException(
                f"Failed to translate key '{request.key}': {str(e)}"
            )

    @router.post(
        "/format/datetime",
        response_model=SuccessResponse[DateTimeFormatData],
        summary="Format datetime",
        description="Format datetime according to user's localization settings",
    )
    async def format_datetime(request: DateTimeFormatRequest) -> SuccessResponse:
        """Format datetime."""
        try:
            # Parse ISO datetime string
            dt = datetime.fromisoformat(request.datetime.replace("Z", "+00:00"))
            formatted_dt = i18n_service.format_datetime(dt, request.format_type)

            return SuccessResponse(
                message="Datetime formatted successfully",
                data={
                    "original": request.datetime,
                    "formatted": formatted_dt,
                    "format_type": request.format_type,
                    "language": i18n_service.get_current_language(),
                    "timezone": i18n_service.get_current_timezone(),
                },
            )
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to format datetime: {str(e)}"
            )

    @router.post(
        "/format/number",
        response_model=SuccessResponse[NumberFormatData],
        summary="Format number",
        description="Format number according to user's localization settings",
    )
    async def format_number(request: NumberFormatRequest) -> SuccessResponse:
        """Format number."""
        try:
            formatted_number = i18n_service.format_number(
                request.number, request.decimal_places
            )

            return SuccessResponse(
                message="Number formatted successfully",
                data={
                    "original": request.number,
                    "formatted": formatted_number,
                    "decimal_places": request.decimal_places,
                    "language": i18n_service.get_current_language(),
                },
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to format number: {str(e)}"
            )

    @router.post(
        "/format/currency",
        response_model=SuccessResponse[CurrencyFormatData],
        summary="Format currency",
        description="Format currency amount according to user's localization settings",
    )
    async def format_currency(request: CurrencyFormatRequest) -> SuccessResponse:
        """Format currency."""
        try:
            formatted_currency = i18n_service.format_currency(
                request.amount, request.decimal_places
            )

            return SuccessResponse(
                message="Currency formatted successfully",
                data={
                    "original": request.amount,
                    "formatted": formatted_currency,
                    "decimal_places": request.decimal_places,
                    "language": i18n_service.get_current_language(),
                    "currency_symbol": i18n_service._i18n_config.get_currency_symbol(),
                },
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to format currency: {str(e)}"
            )

    # User settings
    @router.get(
        "/user/settings",
        response_model=SuccessResponse[UserI18nSettingsData],
        summary="Get user i18n settings",
        description="Get internationalization settings for specified user",
    )
    async def get_user_settings(
        user_id: str = Header(..., alias="X-User-ID"),
    ) -> SuccessResponse:
        """Get user's i18n settings."""
        user_context = _user_contexts.get(
            user_id, {"language": "en-US", "timezone": "UTC"}
        )

        return SuccessResponse(
            message="User i18n settings retrieved successfully",
            data={
                "user_id": user_id,
                "language": user_context.get("language", "en-US"),
                "timezone": user_context.get("timezone", "UTC"),
            },
        )

    @router.put(
        "/user/settings",
        response_model=SuccessResponse[UserI18nSettingsData],
        summary="Update user i18n settings",
        description="Update internationalization settings for specified user",
    )
    async def update_user_settings(
        request: UserI18nSettingsRequest,
        user_id: str = Header(..., alias="X-User-ID"),
    ) -> SuccessResponse:
        """Update user's i18n settings."""
        if user_id not in _user_contexts:
            _user_contexts[user_id] = {}

        user_context = _user_contexts[user_id]

        if request.language:
            if not validate_language_code(request.language):
                raise HTTPException(
                    status_code=400,
                    detail=f"Language '{request.language}' is not supported",
                )
            user_context["language"] = request.language
            i18n_service.set_language(request.language)

        if request.timezone:
            if not validate_timezone(request.timezone):
                raise HTTPException(
                    status_code=400,
                    detail=f"Timezone '{request.timezone}' is not valid",
                )
            user_context["timezone"] = request.timezone
            i18n_service.set_timezone(request.timezone)

        return SuccessResponse(
            message="User i18n settings updated successfully",
            data={
                "user_id": user_id,
                "language": user_context.get("language"),
                "timezone": user_context.get("timezone"),
            },
        )

    return router


def get_i18n_router() -> APIRouter:
    """Get i18n router instance (backward compatible).

    Returns:
        APIRouter: Configured i18n router
    """
    return create_i18n_router()


# Export the router functions
__all__ = ["create_i18n_router", "get_i18n_router"]

"""Standalone i18n API module for ValueCell."""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Header
from datetime import datetime

from .schemas import (
    SuccessResponse,
    LanguageRequest,
    TimezoneRequest,
    LanguageDetectionRequest,
    TranslationRequest,
    DateTimeFormatRequest,
    NumberFormatRequest,
    CurrencyFormatRequest,
    UserI18nSettingsRequest,
    AgentI18nContext,
)
from ..services.i18n_service import get_i18n_service
from ..config.settings import get_settings
from ..core.constants import SUPPORTED_LANGUAGES, LANGUAGE_TIMEZONE_MAPPING
from ..utils.i18n_utils import (
    detect_browser_language,
    get_common_timezones,
    get_timezone_display_name,
    validate_language_code,
    validate_timezone,
)


class I18nAPI:
    """Standalone i18n API class."""

    def __init__(self):
        """Initialize i18n API."""
        self.i18n_service = get_i18n_service()
        self.settings = get_settings()

        # User context storage (in production, use Redis or database)
        self._user_contexts: Dict[str, Dict[str, Any]] = {}

        # Create router
        self.router = self._create_router()

    def _create_router(self) -> APIRouter:
        """Create FastAPI router for i18n endpoints."""
        router = APIRouter(prefix="/i18n", tags=["i18n"])

        # Configuration endpoints
        router.add_api_route("/config", self.get_config, methods=["GET"])
        router.add_api_route(
            "/languages", self.get_supported_languages, methods=["GET"]
        )
        router.add_api_route("/timezones", self.get_timezones, methods=["GET"])

        # Language and timezone management
        router.add_api_route("/language", self.set_language, methods=["POST"])
        router.add_api_route("/timezone", self.set_timezone, methods=["POST"])
        router.add_api_route("/detect-language", self.detect_language, methods=["POST"])

        # Translation and formatting services
        router.add_api_route("/translate", self.translate, methods=["POST"])
        router.add_api_route("/format/datetime", self.format_datetime, methods=["POST"])
        router.add_api_route("/format/number", self.format_number, methods=["POST"])
        router.add_api_route("/format/currency", self.format_currency, methods=["POST"])

        # User settings
        router.add_api_route("/user/settings", self.get_user_settings, methods=["GET"])
        router.add_api_route(
            "/user/settings", self.update_user_settings, methods=["POST"]
        )

        # Agent context
        router.add_api_route("/agent/context", self.get_agent_context, methods=["GET"])

        return router

    def _get_user_context(self, user_id: Optional[str]) -> Dict[str, Any]:
        """Get user context and apply to i18n service."""
        if user_id and user_id in self._user_contexts:
            user_context = self._user_contexts[user_id]
            self.i18n_service.set_language(user_context.get("language", "en-US"))
            self.i18n_service.set_timezone(user_context.get("timezone", "UTC"))
            return user_context
        return {"language": "en-US", "timezone": "UTC"}

    async def get_config(
        self,
        user_id: Optional[str] = Header(None, alias="X-User-ID"),
        session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    ) -> SuccessResponse:
        """Get current i18n configuration."""
        self._get_user_context(user_id)

        return SuccessResponse(
            message="I18n configuration retrieved successfully",
            data=self.i18n_service.to_dict(),
        )

    async def get_supported_languages(self) -> SuccessResponse:
        """Get supported languages."""
        languages = [
            {
                "code": code,
                "name": name,
                "is_current": code == self.i18n_service.get_current_language(),
            }
            for code, name in SUPPORTED_LANGUAGES
        ]

        return SuccessResponse(
            message="Supported languages retrieved successfully",
            data={
                "languages": languages,
                "current": self.i18n_service.get_current_language(),
            },
        )

    async def set_language(
        self,
        request: LanguageRequest,
        user_id: Optional[str] = Header(None, alias="X-User-ID"),
    ) -> SuccessResponse:
        """Set current language."""
        if not validate_language_code(request.language):
            raise HTTPException(
                status_code=400,
                detail=f"Language '{request.language}' is not supported",
            )

        success = self.i18n_service.set_language(request.language)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to set language")

        # Save user context
        if user_id:
            if user_id not in self._user_contexts:
                self._user_contexts[user_id] = {}
            self._user_contexts[user_id]["language"] = request.language
            self._user_contexts[user_id]["timezone"] = (
                self.i18n_service.get_current_timezone()
            )

        return SuccessResponse(
            message="Language updated successfully",
            data={
                "language": request.language,
                "timezone": self.i18n_service.get_current_timezone(),
            },
        )

    async def get_timezones(self) -> SuccessResponse:
        """Get available timezones."""
        common_timezones = get_common_timezones()
        timezone_list = [
            {
                "value": tz,
                "label": get_timezone_display_name(tz),
                "is_current": tz == self.i18n_service.get_current_timezone(),
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
                        "is_current": lang_tz
                        == self.i18n_service.get_current_timezone(),
                    }
                )

        # Sort by label
        timezone_list.sort(key=lambda x: x["label"])

        return SuccessResponse(
            message="Timezones retrieved successfully",
            data={
                "timezones": timezone_list,
                "current": self.i18n_service.get_current_timezone(),
            },
        )

    async def set_timezone(
        self,
        request: TimezoneRequest,
        user_id: Optional[str] = Header(None, alias="X-User-ID"),
    ) -> SuccessResponse:
        """Set current timezone."""
        if not validate_timezone(request.timezone):
            raise HTTPException(
                status_code=400, detail=f"Timezone '{request.timezone}' is not valid"
            )

        success = self.i18n_service.set_timezone(request.timezone)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to set timezone")

        # Save user context
        if user_id:
            if user_id not in self._user_contexts:
                self._user_contexts[user_id] = {}
            self._user_contexts[user_id]["timezone"] = request.timezone

        return SuccessResponse(
            message="Timezone updated successfully",
            data={
                "timezone": request.timezone,
                "display_name": get_timezone_display_name(request.timezone),
            },
        )

    async def detect_language(
        self, request: LanguageDetectionRequest
    ) -> SuccessResponse:
        """Detect language from Accept-Language header."""
        detected_language = detect_browser_language(request.accept_language)

        return SuccessResponse(
            message="Language detected successfully",
            data={
                "detected_language": detected_language,
                "language_name": next(
                    (
                        name
                        for code, name in SUPPORTED_LANGUAGES
                        if code == detected_language
                    ),
                    detected_language,
                ),
                "is_supported": detected_language
                in [code for code, _ in SUPPORTED_LANGUAGES],
            },
        )

    async def translate(self, request: TranslationRequest) -> SuccessResponse:
        """Translate a key."""
        try:
            translated_text = self.i18n_service.translate(
                request.key, request.language, **request.variables
            )

            return SuccessResponse(
                message="Translation retrieved successfully",
                data={
                    "key": request.key,
                    "translated_text": translated_text,
                    "language": request.language
                    or self.i18n_service.get_current_language(),
                    "variables": request.variables,
                },
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to translate key '{request.key}': {str(e)}",
            )

    async def format_datetime(self, request: DateTimeFormatRequest) -> SuccessResponse:
        """Format datetime."""
        try:
            # Parse ISO datetime string
            dt = datetime.fromisoformat(request.datetime.replace("Z", "+00:00"))
            formatted_dt = self.i18n_service.format_datetime(dt, request.format_type)

            return SuccessResponse(
                message="Datetime formatted successfully",
                data={
                    "original": request.datetime,
                    "formatted": formatted_dt,
                    "format_type": request.format_type,
                    "language": self.i18n_service.get_current_language(),
                    "timezone": self.i18n_service.get_current_timezone(),
                },
            )
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to format datetime: {str(e)}"
            )

    async def format_number(self, request: NumberFormatRequest) -> SuccessResponse:
        """Format number."""
        try:
            formatted_number = self.i18n_service.format_number(
                request.number, request.decimal_places
            )

            return SuccessResponse(
                message="Number formatted successfully",
                data={
                    "original": request.number,
                    "formatted": formatted_number,
                    "decimal_places": request.decimal_places,
                    "language": self.i18n_service.get_current_language(),
                },
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to format number: {str(e)}"
            )

    async def format_currency(self, request: CurrencyFormatRequest) -> SuccessResponse:
        """Format currency."""
        try:
            formatted_currency = self.i18n_service.format_currency(
                request.amount, request.decimal_places
            )

            return SuccessResponse(
                message="Currency formatted successfully",
                data={
                    "original": request.amount,
                    "formatted": formatted_currency,
                    "decimal_places": request.decimal_places,
                    "language": self.i18n_service.get_current_language(),
                    "currency_symbol": self.i18n_service._i18n_config.get_currency_symbol(),
                },
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to format currency: {str(e)}"
            )

    async def get_user_settings(
        self, user_id: str = Header(..., alias="X-User-ID")
    ) -> SuccessResponse:
        """Get user's i18n settings."""
        user_context = self._user_contexts.get(
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

    async def update_user_settings(
        self,
        request: UserI18nSettingsRequest,
        user_id: str = Header(..., alias="X-User-ID"),
    ) -> SuccessResponse:
        """Update user's i18n settings."""
        if user_id not in self._user_contexts:
            self._user_contexts[user_id] = {}

        user_context = self._user_contexts[user_id]

        if request.language:
            if not validate_language_code(request.language):
                raise HTTPException(
                    status_code=400,
                    detail=f"Language '{request.language}' is not supported",
                )
            user_context["language"] = request.language
            self.i18n_service.set_language(request.language)

        if request.timezone:
            if not validate_timezone(request.timezone):
                raise HTTPException(
                    status_code=400,
                    detail=f"Timezone '{request.timezone}' is not valid",
                )
            user_context["timezone"] = request.timezone
            self.i18n_service.set_timezone(request.timezone)

        return SuccessResponse(
            message="User i18n settings updated successfully",
            data={
                "user_id": user_id,
                "language": user_context.get("language"),
                "timezone": user_context.get("timezone"),
            },
        )

    async def get_agent_context(
        self,
        user_id: Optional[str] = Header(None, alias="X-User-ID"),
        session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    ) -> SuccessResponse:
        """Get i18n context for agent communication."""
        # Load user-specific settings
        self._get_user_context(user_id)

        context = AgentI18nContext(
            language=self.i18n_service.get_current_language(),
            timezone=self.i18n_service.get_current_timezone(),
            currency_symbol=self.i18n_service._i18n_config.get_currency_symbol(),
            date_format=self.i18n_service._i18n_config.get_date_format(),
            time_format=self.i18n_service._i18n_config.get_time_format(),
            number_format=self.i18n_service._i18n_config.get_number_format(),
            user_id=user_id,
            session_id=session_id,
        )

        return SuccessResponse(
            message="Agent i18n context retrieved successfully", data=context.dict()
        )

    def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get user context for agents."""
        return self._user_contexts.get(
            user_id, {"language": "en-US", "timezone": "UTC"}
        )

    def set_user_context(self, user_id: str, context: Dict[str, Any]):
        """Set user context for agents."""
        if user_id not in self._user_contexts:
            self._user_contexts[user_id] = {}
        self._user_contexts[user_id].update(context)


# Global i18n API instance
_i18n_api: Optional[I18nAPI] = None


def get_i18n_api() -> I18nAPI:
    """Get global i18n API instance."""
    global _i18n_api
    if _i18n_api is None:
        _i18n_api = I18nAPI()
    return _i18n_api


def create_i18n_router() -> APIRouter:
    """Create i18n router for inclusion in main app."""
    return get_i18n_api().router

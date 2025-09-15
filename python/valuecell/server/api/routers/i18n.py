"""I18n router for ValueCell Server."""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Header, Depends
from datetime import datetime
from sqlalchemy.orm import Session

from ..schemas.common import SuccessResponse
from ..schemas.i18n import (
    LanguageRequest,
    TimezoneRequest,
    LanguageDetectionRequest,
    TranslationRequest,
    DateTimeFormatRequest,
    NumberFormatRequest,
    CurrencyFormatRequest,
    UserI18nSettingsRequest,
    AgentI18nContext,
    I18nConfigResponse,
    SupportedLanguagesResponse,
    TimezonesResponse,
)
from ...config.database import get_db
from ...services.i18n.i18n_service import I18nService
from ...config.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/i18n", tags=["i18n"])


# Dependency to get i18n service
def get_i18n_service(db: Session = Depends(get_db)) -> I18nService:
    """Get i18n service instance."""
    return I18nService(db)


@router.get("/config", response_model=SuccessResponse)
async def get_config(
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    i18n_service: I18nService = Depends(get_i18n_service),
) -> SuccessResponse:
    """Get i18n configuration for user."""
    try:
        config = await i18n_service.get_user_config(user_id)
        return SuccessResponse(
            message="I18n configuration retrieved successfully",
            data=config
        )
    except Exception as e:
        logger.error(f"Error getting i18n config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/languages", response_model=SuccessResponse)
async def get_supported_languages(
    i18n_service: I18nService = Depends(get_i18n_service),
) -> SuccessResponse:
    """Get supported languages."""
    try:
        languages = await i18n_service.get_supported_languages()
        return SuccessResponse(
            message="Supported languages retrieved successfully",
            data=languages
        )
    except Exception as e:
        logger.error(f"Error getting supported languages: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/language", response_model=SuccessResponse)
async def set_language(
    request: LanguageRequest,
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    i18n_service: I18nService = Depends(get_i18n_service),
) -> SuccessResponse:
    """Set user language preference."""
    try:
        result = await i18n_service.set_user_language(user_id, request.language)
        return SuccessResponse(
            message=f"Language set to {request.language}",
            data=result
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error setting language: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/timezones", response_model=SuccessResponse)
async def get_timezones(
    i18n_service: I18nService = Depends(get_i18n_service),
) -> SuccessResponse:
    """Get supported timezones."""
    try:
        timezones = await i18n_service.get_supported_timezones()
        return SuccessResponse(
            message="Supported timezones retrieved successfully",
            data=timezones
        )
    except Exception as e:
        logger.error(f"Error getting timezones: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/timezone", response_model=SuccessResponse)
async def set_timezone(
    request: TimezoneRequest,
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    i18n_service: I18nService = Depends(get_i18n_service),
) -> SuccessResponse:
    """Set user timezone preference."""
    try:
        result = await i18n_service.set_user_timezone(user_id, request.timezone)
        return SuccessResponse(
            message=f"Timezone set to {request.timezone}",
            data=result
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error setting timezone: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/detect-language", response_model=SuccessResponse)
async def detect_language(
    request: LanguageDetectionRequest,
    i18n_service: I18nService = Depends(get_i18n_service),
) -> SuccessResponse:
    """Detect language from Accept-Language header."""
    try:
        detected = await i18n_service.detect_language(request.accept_language)
        return SuccessResponse(
            message="Language detected successfully",
            data=detected
        )
    except Exception as e:
        logger.error(f"Error detecting language: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/translate", response_model=SuccessResponse)
async def translate(
    request: TranslationRequest,
    i18n_service: I18nService = Depends(get_i18n_service),
) -> SuccessResponse:
    """Translate a key to target language."""
    try:
        translation = await i18n_service.translate(
            key=request.key,
            language=request.language,
            variables=request.variables
        )
        return SuccessResponse(
            message="Translation retrieved successfully",
            data={"translation": translation}
        )
    except Exception as e:
        logger.error(f"Error translating: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/format/datetime", response_model=SuccessResponse)
async def format_datetime(
    request: DateTimeFormatRequest,
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    i18n_service: I18nService = Depends(get_i18n_service),
) -> SuccessResponse:
    """Format datetime according to user preferences."""
    try:
        formatted = await i18n_service.format_datetime(
            datetime_str=request.datetime,
            format_type=request.format_type,
            user_id=user_id
        )
        return SuccessResponse(
            message="DateTime formatted successfully",
            data={"formatted": formatted}
        )
    except Exception as e:
        logger.error(f"Error formatting datetime: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/format/number", response_model=SuccessResponse)
async def format_number(
    request: NumberFormatRequest,
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    i18n_service: I18nService = Depends(get_i18n_service),
) -> SuccessResponse:
    """Format number according to user preferences."""
    try:
        formatted = await i18n_service.format_number(
            number=request.number,
            decimal_places=request.decimal_places,
            user_id=user_id
        )
        return SuccessResponse(
            message="Number formatted successfully",
            data={"formatted": formatted}
        )
    except Exception as e:
        logger.error(f"Error formatting number: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/format/currency", response_model=SuccessResponse)
async def format_currency(
    request: CurrencyFormatRequest,
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    i18n_service: I18nService = Depends(get_i18n_service),
) -> SuccessResponse:
    """Format currency according to user preferences."""
    try:
        formatted = await i18n_service.format_currency(
            amount=request.amount,
            decimal_places=request.decimal_places,
            user_id=user_id
        )
        return SuccessResponse(
            message="Currency formatted successfully",
            data={"formatted": formatted}
        )
    except Exception as e:
        logger.error(f"Error formatting currency: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/user/settings", response_model=SuccessResponse)
async def get_user_settings(
    user_id: str = Header(..., alias="X-User-ID"),
    i18n_service: I18nService = Depends(get_i18n_service),
) -> SuccessResponse:
    """Get user i18n settings."""
    try:
        settings = await i18n_service.get_user_settings(user_id)
        return SuccessResponse(
            message="User settings retrieved successfully",
            data=settings
        )
    except Exception as e:
        logger.error(f"Error getting user settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/user/settings", response_model=SuccessResponse)
async def update_user_settings(
    request: UserI18nSettingsRequest,
    user_id: str = Header(..., alias="X-User-ID"),
    i18n_service: I18nService = Depends(get_i18n_service),
) -> SuccessResponse:
    """Update user i18n settings."""
    try:
        settings = await i18n_service.update_user_settings(
            user_id=user_id,
            language=request.language,
            timezone=request.timezone
        )
        return SuccessResponse(
            message="User settings updated successfully",
            data=settings
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating user settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/agent/context", response_model=SuccessResponse)
async def get_agent_context(
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    i18n_service: I18nService = Depends(get_i18n_service),
) -> SuccessResponse:
    """Get i18n context for agent execution."""
    try:
        context = await i18n_service.get_agent_context(user_id, session_id)
        return SuccessResponse(
            message="Agent context retrieved successfully",
            data=context
        )
    except Exception as e:
        logger.error(f"Error getting agent context: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
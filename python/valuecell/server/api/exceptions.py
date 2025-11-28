"""API exception handling module."""

from typing import Any, Dict

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .schemas import ErrorResponse, StatusCode


class APIException(Exception):
    """Custom API exception base class."""

    def __init__(self, code: StatusCode, message: str, details: Dict[str, Any] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


class UnauthorizedException(APIException):
    """Unauthorized exception."""

    def __init__(self, message: str = "Unauthorized access"):
        super().__init__(StatusCode.UNAUTHORIZED, message)


class NotFoundException(APIException):
    """Resource not found exception."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(StatusCode.NOT_FOUND, message)


class ForbiddenException(APIException):
    """Forbidden access exception."""

    def __init__(self, message: str = "Forbidden access"):
        super().__init__(StatusCode.FORBIDDEN, message)


class InternalServerException(APIException):
    """Internal server error exception."""

    def __init__(self, message: str = "Internal server error"):
        super().__init__(StatusCode.INTERNAL_ERROR, message)


async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """API exception handler."""
    return JSONResponse(
        status_code=200,  # HTTP status code is always 200, error info is in response body
        content=ErrorResponse.create(code=exc.code, msg=exc.message).dict(),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """HTTP exception handler."""
    # Map HTTP status codes to our status codes
    status_code_mapping = {
        400: StatusCode.BAD_REQUEST,
        401: StatusCode.UNAUTHORIZED,
        403: StatusCode.FORBIDDEN,
        404: StatusCode.NOT_FOUND,
        500: StatusCode.INTERNAL_ERROR,
    }

    api_code = status_code_mapping.get(exc.status_code, StatusCode.INTERNAL_ERROR)
    return JSONResponse(
        status_code=200,
        content=ErrorResponse.create(code=api_code, msg=str(exc.detail)).dict(),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Request validation exception handler."""
    # Extract validation error information
    error_details = []
    for error in exc.errors():
        error_details.append(
            {
                "field": ".".join(str(x) for x in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
        )

    return JSONResponse(
        status_code=200,
        content=ErrorResponse.create(
            code=StatusCode.BAD_REQUEST,
            msg=(
                "Request parameter validation failed: "
                + "; ".join([f"{e['field']}: {e['message']}" for e in error_details])
            ),
        ).dict(),
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """General exception handler."""
    return JSONResponse(
        status_code=200,
        content=ErrorResponse.create(
            code=StatusCode.INTERNAL_ERROR,
            msg="Internal server error, please try again later",
        ).dict(),
    )

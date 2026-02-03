import logging
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class DockerSocketError(Exception):
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


async def exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled exception: %s path=%s method=%s",
        exc,
        request.url.path,
        request.method,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal error occurred. Please try again later.",
            "type": "internal_error",
        },
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    logger.warning(
        "HTTP exception: status=%s detail=%s path=%s method=%s",
        exc.status_code,
        exc.detail,
        request.url.path,
        request.method,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "type": "http_error",
        },
    )


async def request_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.warning(
        "Request validation error: %s path=%s method=%s",
        exc.errors(),
        request.url.path,
        request.method,
    )
    return JSONResponse(
        status_code=422,  # Unprocessable Entity/Content (avoids Starlette deprecation warning)
        content={
            "detail": exc.errors(),
            "type": "validation_error",
        },
    )

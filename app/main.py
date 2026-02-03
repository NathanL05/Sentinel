"""FastAPI main application entry point"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

from app import __version__
from app.exceptions import (
    exception_handler,
    http_exception_handler,
    request_validation_exception_handler,
)
from app.logging_config import configure_logging
from app.middleware import RequestLoggingMiddleware
from app.routers.metrics import router


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    configure_logging()
    yield


app = FastAPI(title="Sentinel", version=__version__, lifespan=lifespan)
app.add_exception_handler(Exception, exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
app.add_middleware(RequestLoggingMiddleware)
app.include_router(router)


@app.get("/")
async def read_root() -> dict[str, str]:
    return {"message": "Welcome to Sentinel", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/health")
async def health_check() -> dict[str, str | datetime]:
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": __version__,
    }


if __name__ == "__main__":
    import uvicorn

    from app.config import get_settings

    s = get_settings()
    uvicorn.run(
        "app.main:app",
        host=s.api_host,
        port=s.api_port,
        log_level=s.log_level.lower(),
    )

import logging
import time
from typing import Any
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)


async def log_request_response(scope: Scope, receive: Receive, send: Send, app: ASGIApp) -> None:
    if scope["type"] != "http":
        await app(scope, receive, send)
        return

    method = scope.get("method", "?")
    path = scope.get("path", "?")
    start = time.perf_counter()

    status_code = 500

    async def send_wrapper(message: dict[str, Any]) -> None:
        nonlocal status_code
        if message.get("type") == "http.response.start":
            status_code = message.get("status", 500)
        await send(message)

    await app(scope, receive, send_wrapper)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info("%s %s %s %.3fms", method, path, status_code, duration_ms)


class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await log_request_response(scope, receive, send, self.app)

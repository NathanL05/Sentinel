from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import BaseModel
from starlette.exceptions import HTTPException

from app.exceptions import (
    exception_handler,
    http_exception_handler,
    request_validation_exception_handler,
)

# Minimal app to test handlers in isolation (name avoids pytest collecting it as a test)
_exception_test_app = FastAPI()
_exception_test_app.add_exception_handler(Exception, exception_handler)
_exception_test_app.add_exception_handler(HTTPException, http_exception_handler)
_exception_test_app.add_exception_handler(RequestValidationError, request_validation_exception_handler)


@_exception_test_app.get("/raise-exception")
async def _raise_exception() -> None:
    raise RuntimeError("internal failure")


@_exception_test_app.get("/raise-404")
def _raise_404() -> None:
    raise HTTPException(status_code=404, detail="Resource not found")


class _RequestBody(BaseModel):
    value: int


@_exception_test_app.post("/validate")
def _validate(body: _RequestBody) -> dict:
    return {"value": body.value}


def test_unhandled_exception_returns_500() -> None:
    client = TestClient(_exception_test_app, raise_server_exceptions=False)
    response = client.get("/raise-exception")
    assert response.status_code == 500
    data = response.json()
    assert data["detail"] == "An internal error occurred. Please try again later."
    assert data["type"] == "internal_error"


def test_http_exception_returns_correct_status_and_detail() -> None:
    client = TestClient(_exception_test_app)
    response = client.get("/raise-404")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Resource not found"
    assert data["type"] == "http_error"


def test_validation_error_returns_422() -> None:
    client = TestClient(_exception_test_app)
    response = client.post("/validate", json={})
    assert response.status_code == 422
    data = response.json()
    assert data["type"] == "validation_error"
    assert "detail" in data
    assert isinstance(data["detail"], list)
    assert len(data["detail"]) > 0

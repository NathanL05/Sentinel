import logging

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_request_logging_middleware_logs_request(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="app.middleware")
    response = client.get("/health")
    assert response.status_code == 200
    assert any("GET" in rec.message and "/health" in rec.message and "200" in rec.message for rec in caplog.records)

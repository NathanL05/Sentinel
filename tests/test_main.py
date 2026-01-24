from datetime import datetime
import time
from fastapi.testclient import TestClient

from app import __version__

STATUS_CODE_OK = 200
TIMESTAMP_TOLERANCE_SECONDS = 60
HEALTH_RESPONSE_TIME = 0.1


class TestRootEndpoint:
    def test_root_endpoint_returns_welcome_message(self, client: TestClient) -> None:
        response = client.get("/")

        assert response.status_code == STATUS_CODE_OK
        data = response.json()
        assert "message" in data
        assert data["message"] == "Welcome to Sentinel"
        assert "timestamp" in data

        timestamp = data["timestamp"]
        datetime.fromisoformat(timestamp)

    def test_root_endpoint_has_correct_content_type(self, client: TestClient) -> None:
        response = client.get("/")
        assert response.headers["content-type"] == "application/json"


class TestHealthEndpoint:
    def test_health_endpoint_returns_healthy_status(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == STATUS_CODE_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data

    def test_health_endpoint_includes_version(self, client: TestClient) -> None:
        response = client.get("/health")
        data = response.json()

        assert data["version"] == __version__
        assert data["version"] == "1.0.0"

    def test_health_endpoint_timestamp_is_valid_iso(self, client: TestClient) -> None:
        response = client.get("/health")
        data = response.json()

        timestamp_str = data["timestamp"]
        parsed_timestamp = datetime.fromisoformat(timestamp_str)

        now = datetime.now(parsed_timestamp.tzinfo)
        time_diff = abs((now - parsed_timestamp).total_seconds())
        assert time_diff < TIMESTAMP_TOLERANCE_SECONDS, "Timestamp should be recent"

    def test_health_endpoint_is_fast(self, client: TestClient) -> None:
        start_time = time.time()
        response = client.get("/health")
        elapsed_time = time.time() - start_time

        assert response.status_code == STATUS_CODE_OK
        assert elapsed_time < HEALTH_RESPONSE_TIME, "Health endpoint should be fast"

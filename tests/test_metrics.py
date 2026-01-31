from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

SUCCESS_RESPONSE = 200
ERROR_RESPONSE = 500
NOT_FOUND_RESPONSE = 404


@pytest.fixture
def mock_metrics_docker():
    with patch("app.routers.metrics.docker_client") as m:
        yield m


class TestListContainers:
    def test_returns_container_list(self, client: TestClient, mock_metrics_docker: MagicMock) -> None:
        mock_metrics_docker.list_running_containers.return_value = [
            {"id": "1234567890", "name": "test_container", "image": "test_image", "status": "running"},
        ]
        response = client.get("/api/v1/containers")
        assert response.status_code == SUCCESS_RESPONSE
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "1234567890"
        assert data[0]["name"] == "test_container"
        assert data[0]["image"] == "test_image"
        assert data[0]["status"] == "running"

    def test_docker_returns_error(self, client: TestClient, mock_metrics_docker: MagicMock) -> None:
        mock_metrics_docker.list_running_containers.side_effect = Exception("No such container")
        response = client.get("/api/v1/containers")

        assert response.status_code == ERROR_RESPONSE
        assert response.json()["detail"] == "No such container"


class TestContainerStats:
    def test_returns_stats(self, client: TestClient, mock_metrics_docker: MagicMock) -> None:
        mock_metrics_docker.get_container_stats.return_value = {
            "container_id": "abc123",
            "cpu_percent": 12.5,
            "memory_usage_bytes": 1000000,
            "memory_limit_bytes": 2000000,
            "memory_percent": 50.0,
            "network_rx_bytes": 100,
            "network_tx_bytes": 200,
        }
        response = client.get("/api/v1/containers/abc123/stats")
        assert response.status_code == SUCCESS_RESPONSE
        data = response.json()
        assert data["container_id"] == "abc123"
        assert data["cpu_percent"] == 12.5
        assert data["memory_usage_bytes"] == 1000000
        assert data["memory_limit_bytes"] == 2000000
        assert data["memory_percent"] == 50.0
        assert data["network_rx_bytes"] == 100
        assert data["network_tx_bytes"] == 200

    def test_container_not_found(self, client: TestClient, mock_metrics_docker: MagicMock) -> None:
        mock_metrics_docker.get_container_stats.side_effect = Exception("Container not found")
        invalid_container_id = "invalid123"
        response = client.get(f"/api/v1/containers/{invalid_container_id}/stats")
        assert response.status_code == NOT_FOUND_RESPONSE

    def test_tail_query_respected(self, client: TestClient, mock_metrics_docker: MagicMock) -> None:
        mock_container = MagicMock()
        mock_container.logs.return_value = b"log"
        mock_metrics_docker.client.containers.get.return_value = mock_container

        client.get("/api/v1/containers/1234567890/logs?tail=50")
        mock_container.logs.assert_called_once_with(tail=50, follow=False)


class TestPrometheusMetrics:
    def test_prometheus_format(self, client: TestClient, mock_metrics_docker: MagicMock) -> None:
        mock_metrics_docker.list_running_containers.return_value = [
            {"id": "abc123", "name": "web", "image": "nginx", "status": "running"},
        ]
        mock_metrics_docker.get_container_stats.return_value = {
            "container_id": "abc123",
            "cpu_percent": 10.0,
            "memory_usage_bytes": 1000,
            "memory_limit_bytes": 2000,
            "memory_percent": 50.0,
            "network_rx_bytes": 100,
            "network_tx_bytes": 200,
        }

        response = client.get("/api/v1/metrics")
        assert response.status_code == 200
        text = response.text
        assert "sentinel_container_count 1" in text
        assert "sentinel_container_cpu_percent" in text
        assert "sentinel_container_memory_bytes" in text
        assert "sentinel_container_network_bytes" in text

    def test_docker_error_returns_500(self, client: TestClient, mock_metrics_docker: MagicMock) -> None:
        mock_metrics_docker.list_running_containers.side_effect = Exception("Docker unavailable")
        response = client.get("/api/v1/metrics")
        assert response.status_code == 500

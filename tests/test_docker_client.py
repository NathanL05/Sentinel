from unittest.mock import MagicMock
import pytest
from docker.errors import APIError, DockerException, NotFound
from app.docker_client import DockerClient

EXPECTED_CPU_PERCENT = 20.0
EXPECTED_MEMORY_PERCENT_75 = 75.0
EXPECTED_CPU_PERCENT_0 = 0.0
CPU_USAGE_DELTA = 1000000
SYSTEM_CPU_USAGE = 2000000
MEMORY_USAGE_75MB = 75000000
MEMORY_LIMIT = 100000000
NETWORK_RX_BYTES_ETH0 = 1000
NETWORK_TX_BYTES_ETH0 = 2000
NETWORK_RX_BYTES_ETH1 = 3000
NETWORK_TX_BYTES_ETH1 = 4000


class TestDockerClientInitialization:
    def test_init_when_docker_available(self, mock_docker_setup: MagicMock, docker_client: DockerClient) -> None:
        mock_client = mock_docker_setup
        mock_client.ping.return_value = True

        assert docker_client.client == mock_client
        mock_client.ping.assert_called_once()

    def test_init_raises_exception_when_docker_unavailable(self, mock_from_env: MagicMock) -> None:
        mock_from_env.side_effect = DockerException("Cannot connect to Docker")
        with pytest.raises(DockerException, match="Error initializing Docker client"):
            DockerClient()

    def test_init_raises_exception_when_ping_fails(self, mock_from_env: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.ping.side_effect = DockerException("Ping failed")
        mock_from_env.return_value = mock_client

        with pytest.raises(DockerException, match="Error initializing Docker client"):
            DockerClient()


class TestListRunningContainers:
    def test_containers_returns_formatted_list(self, mock_docker_setup: MagicMock, docker_client: DockerClient) -> None:
        mock_client = mock_docker_setup

        mock_container1 = MagicMock()
        mock_container1.id = "abcdef1234567890"
        mock_container1.name = "test_container1"
        mock_container1.image.tags = ["test-image:latest"]
        mock_container1.status = "running"

        mock_container2 = MagicMock()
        mock_container2.id = "xyz123789456abc"
        mock_container2.name = "test_container2"
        mock_container2.image.tags = ["test-image:v2"]
        mock_container2.status = "running"

        mock_client.containers.list.return_value = [mock_container1, mock_container2]

        result = docker_client.list_running_containers()

        expected_length = len(mock_client.containers.list.return_value)
        assert len(result) == expected_length
        assert result[0]["id"] == "abcdef1234567890"[:12]
        assert result[0]["name"] == "test_container1"
        assert result[0]["image"] == "test-image:latest"
        assert result[0]["status"] == "running"
        assert result[1]["id"] == "xyz123789456abc"[:12]
        assert result[1]["name"] == "test_container2"
        assert result[1]["image"] == "test-image:v2"
        assert result[1]["status"] == "running"

    def test_containers_without_tags(self, mock_docker_setup: MagicMock, docker_client: DockerClient) -> None:
        mock_client = mock_docker_setup

        mock_container = MagicMock()
        mock_container.id = "test123"
        mock_container.name = "untagged_container"
        mock_container.image.tags = []
        mock_container.status = "running"

        mock_client.containers.list.return_value = [mock_container]

        result = docker_client.list_running_containers()

        assert len(result) == 1
        assert result[0]["image"] == "unknown"

    def test_containers_handles_docker_error(self, mock_docker_setup: MagicMock, docker_client: DockerClient) -> None:
        mock_client = mock_docker_setup
        mock_client.containers.list.side_effect = DockerException("Docker API error")

        with pytest.raises(DockerException, match="Error listing running containers"):
            docker_client.list_running_containers()


class TestGetContainerStats:
    def test_container_calculates_cpu_percent(self, mock_docker_setup: MagicMock, docker_client: DockerClient) -> None:
        mock_client = mock_docker_setup
        mock_container = MagicMock()

        mock_container.stats.return_value = {
            "cpu_stats": {
                "cpu_usage": {"total_usage": 11000000},
                "system_cpu_usage": 20000000,
                "online_cpus": 2,
            },
            "precpu_stats": {
                "cpu_usage": {"total_usage": 10000000},
                "system_cpu_usage": 10000000,
            },
            "memory_stats": {
                "usage": 50000000,
                "limit": 100000000,
            },
            "networks": {
                "eth0": {"rx_bytes": 1000, "tx_bytes": 2000},
            },
        }
        mock_client.containers.get.return_value = mock_container

        result = docker_client.get_container_stats("test-container-id")

        assert result["cpu_percent"] == EXPECTED_CPU_PERCENT
        assert result["container_id"] == "test-container-id"

    def test_container_calculates_memory_percent(self, mock_docker_setup: MagicMock, docker_client: DockerClient) -> None:
        mock_client = mock_docker_setup
        mock_container = MagicMock()

        mock_container.stats.return_value = {
            "cpu_stats": {
                "cpu_usage": {"total_usage": 10000000},
                "system_cpu_usage": 10000000,
                "online_cpus": 1,
            },
            "precpu_stats": {
                "cpu_usage": {"total_usage": 10000000},
                "system_cpu_usage": 10000000,
            },
            "memory_stats": {
                "usage": 75000000,
                "limit": 100000000,
            },
            "networks": {},
        }

        mock_client.containers.get.return_value = mock_container

        result = docker_client.get_container_stats("test-id")

        assert result["memory_percent"] == EXPECTED_MEMORY_PERCENT_75
        assert result["memory_usage_bytes"] == MEMORY_USAGE_75MB
        assert result["memory_limit_bytes"] == MEMORY_LIMIT

    def test_container_handles_system_delta(self, mock_docker_setup: MagicMock, docker_client: DockerClient) -> None:
        mock_client = mock_docker_setup
        mock_container = MagicMock()

        mock_container.stats.return_value = {
            "cpu_stats": {
                "cpu_usage": {"total_usage": 10000000},
                "system_cpu_usage": 10000000,
                "online_cpus": 1,
            },
            "precpu_stats": {
                "cpu_usage": {"total_usage": 10000000},
                "system_cpu_usage": 10000000,
            },
            "memory_stats": {"usage": 0, "limit": 0},
            "networks": {},
        }

        mock_client.containers.get.return_value = mock_container

        result = docker_client.get_container_stats("test-id")

        assert result["cpu_percent"] == EXPECTED_CPU_PERCENT_0

    def test_container_handles_container_not_found(self, mock_docker_setup: MagicMock, docker_client: DockerClient) -> None:
        mock_client = mock_docker_setup
        mock_client.containers.get.side_effect = NotFound("Container not found")

        with pytest.raises(DockerException, match="Container not found"):
            docker_client.get_container_stats("non-existent-id")

    def test_container_stats_sums_network_bytes(self, mock_docker_setup: MagicMock, docker_client: DockerClient) -> None:
        mock_client = mock_docker_setup
        mock_container = MagicMock()

        mock_container.stats.return_value = {
            "cpu_stats": {
                "cpu_usage": {"total_usage": 10000000},
                "system_cpu_usage": 10000000,
                "online_cpus": 1,
            },
            "precpu_stats": {
                "cpu_usage": {"total_usage": 10000000},
                "system_cpu_usage": 10000000,
            },
            "memory_stats": {"usage": 0, "limit": 0},
            "networks": {
                "eth0": {"rx_bytes": NETWORK_RX_BYTES_ETH0, "tx_bytes": NETWORK_TX_BYTES_ETH0},
                "eth1": {"rx_bytes": NETWORK_RX_BYTES_ETH1, "tx_bytes": NETWORK_TX_BYTES_ETH1},
            },
        }

        mock_client.containers.get.return_value = mock_container

        result = docker_client.get_container_stats("test-id")

        assert result["network_rx_bytes"] == NETWORK_RX_BYTES_ETH0 + NETWORK_RX_BYTES_ETH1
        assert result["network_tx_bytes"] == NETWORK_TX_BYTES_ETH0 + NETWORK_TX_BYTES_ETH1

    def test_container_stats_handles_error(self, mock_docker_setup: MagicMock, docker_client: DockerClient) -> None:
        mock_client = mock_docker_setup
        mock_client.containers.get.side_effect = APIError("Docker API error")

        with pytest.raises(DockerException, match="Error getting container stats"):
            docker_client.get_container_stats("test-id")


class TestGetContainerMetadata:
    def test_container_returns_correct_data(self, mock_docker_setup: MagicMock, docker_client: DockerClient) -> None:
        mock_client = mock_docker_setup
        mock_container = MagicMock()
        mock_container.name = "my-container"
        mock_container.image.tags = ["my-image:v1.0"]
        mock_container.status = "running"
        mock_container.attrs = {"Created": "2024-01-01T00:00:00Z"}
        mock_container.ports = {"80/tcp": [{"HostPort": "8080"}]}

        mock_client.containers.get.return_value = mock_container

        result = docker_client.get_container_metadata("test-id")

        assert result["name"] == "my-container"
        assert result["image"] == "my-image:v1.0"
        assert result["status"] == "running"
        assert result["created"] == "2024-01-01T00:00:00Z"
        assert result["ports"] == {"80/tcp": [{"HostPort": "8080"}]}

    def test_container_handles_no_tags(self, mock_docker_setup: MagicMock, docker_client: DockerClient) -> None:
        mock_client = mock_docker_setup
        mock_container = MagicMock()
        mock_container.name = "untagged-container"
        mock_container.image.tags = []
        mock_container.status = "running"
        mock_container.attrs = {"Created": "2024-01-01T00:00:00Z"}
        mock_container.ports = {}

        mock_client.containers.get.return_value = mock_container

        result = docker_client.get_container_metadata("test-id")

        assert result["image"] == "unknown"

    def test_container_handles_not_found(self, mock_docker_setup: MagicMock, docker_client: DockerClient) -> None:
        mock_client = mock_docker_setup
        mock_client.containers.get.side_effect = NotFound("Container not found")

        with pytest.raises(DockerException, match="Container test-id not found"):
            docker_client.get_container_metadata("test-id")

    def test_container_handles_docker_error(self, mock_docker_setup: MagicMock, docker_client: DockerClient) -> None:
        mock_client = mock_docker_setup
        mock_client.containers.get.side_effect = APIError("Docker API error")

        with pytest.raises(DockerException, match="Error getting container metadata"):
            docker_client.get_container_metadata("test-id")

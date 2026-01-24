import pytest
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import MagicMock, patch
from app.docker_client import DockerClient


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def mock_from_env() -> MagicMock:
    with patch("app.docker_client.docker.from_env") as m:
        yield m


@pytest.fixture()
def mock_docker_setup() -> MagicMock:
    with patch("app.docker_client.docker.from_env") as mock_from_env:
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        yield mock_client
        mock_from_env.assert_called_once()


@pytest.fixture()
def docker_client(mock_docker_setup: MagicMock) -> DockerClient:
    docker_client = DockerClient()
    docker_client.client = mock_docker_setup
    return docker_client

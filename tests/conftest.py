from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Patch Docker before app.main loads (metrics router creates DockerClient at import time)
import app.docker_client

_mock_docker = MagicMock()
_mock_docker.ping.return_value = None
_mock_docker.containers = MagicMock()
patch("app.docker_client.docker.DockerClient", return_value=_mock_docker).start()
patch("app.docker_client.docker.from_env", return_value=_mock_docker).start()

from app.docker_client import DockerClient  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def mock_from_env() -> MagicMock:
    with patch("app.docker_client.docker.from_env") as m:
        yield m


@pytest.fixture
def mock_docker_setup() -> MagicMock:
    with patch("app.docker_client.docker.from_env") as mock_from_env:
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        yield mock_client
        mock_from_env.assert_called_once()


@pytest.fixture
def docker_client(mock_docker_setup: MagicMock) -> DockerClient:
    client = DockerClient()
    client.client = mock_docker_setup
    return client

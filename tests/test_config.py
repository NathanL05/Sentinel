import os

import pytest

from app.config import Settings, get_settings


class TestConfig:
    def test_settings_defaults_when_env_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        get_settings.cache_clear()
        for key in ("DOCKER_SOCKET_PATH", "API_HOST", "API_PORT", "LOG_LEVEL"):
            monkeypatch.delitem(os.environ, key, raising=False)
        settings = get_settings()
        assert settings is not None
        assert settings.docker_socket_path == "/var/run/docker.sock"
        assert settings.api_host == "0.0.0.0"
        assert settings.api_port == 8000
        assert settings.log_level == "INFO"

    def test_settings_override_via_kwargs(self) -> None:
        settings = Settings(api_port=9999, log_level="DEBUG")
        assert settings.api_port == 9999
        assert settings.log_level == "DEBUG"
        assert settings.docker_socket_path == "/var/run/docker.sock"

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    docker_socket_path: str = Field(
        default="/var/run/docker.sock",
        description="The path to the Docker socket",
    )

    api_host: str = Field(
        default="0.0.0.0",
        description="The host to bind the API to",
    )
    api_port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="The port to bind the API to",
    )

    log_level: LogLevel = Field(
        default="INFO",
        description="The log level",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

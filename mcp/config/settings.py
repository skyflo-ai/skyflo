"""MCP server configuration."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    APP_NAME: str = "Skyflo MCP Server"
    APP_VERSION: str = "0.0.0-dev"
    APP_DESCRIPTION: str = "MCP Server for Skyflo"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    MAX_RETRY_ATTEMPTS: int = 3
    RETRY_BASE_DELAY: int = 60
    RETRY_MAX_DELAY: int = 300
    RETRY_EXPONENTIAL_BASE: float = 2.0

    ENGINE_INTERNAL_URL: str = Field(default="http://127.0.0.1:8000")
    INTERNAL_API_KEY: str = Field()


settings = Settings()  # type: ignore[call-arg]  # populated from environment by pydantic-settings

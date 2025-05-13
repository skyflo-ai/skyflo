"""Configuration settings for the API service."""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """API service configuration settings.

    These settings can be configured using environment variables.
    """

    # Application Settings
    APP_NAME: str
    APP_VERSION: str
    APP_DESCRIPTION: str
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"

    # Server Settings
    LOG_LEVEL: str = "INFO"

    # Database Settings - using postgres:// format for Tortoise ORM
    POSTGRES_DATABASE_URL: str = Field(default="postgres://postgres:postgres@localhost:5432/skyflo")

    # Redis Settings for real-time features
    REDIS_URL: str = "redis://localhost:6379/0"

    # Rate Limiting
    RATE_LIMITING_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 100

    # JWT Settings
    JWT_SECRET: str = "CHANGE_ME_IN_PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # One week in minutes
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # MCP Server Settings
    MCP_SERVER_URL: str = "http://127.0.0.1:8081"

    # Workflow Settings
    WORKFLOW_EXECUTION_TIMEOUT: int = 300

    LLM_MODEL: Optional[str] = Field(default="openai/gpt-4o", env="LLM_MODEL") # Format: provider/model_name
    LLM_HOST: Optional[str] = Field(default=None, env="LLM_HOST") # Generic host for any provider

    MANAGER_OPENAI_TEMPERATURE: float = 0.2
    OPENAI_PLANNER_TEMPERATURE: float = 0.3
    OPENAI_EXECUTOR_TEMPERATURE: float = 0.0
    OPENAI_VERIFIER_TEMPERATURE: float = 0.2
    MODEL_NAME: str = "gpt-4o"
    AGENT_TYPE: str = "assistant"
    TEMPERATURE: float = 0.2

    class Config:
        """Pydantic settings configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Allow extra fields from env vars

    def __init__(self, **kwargs):
        """Initialize settings and ensure POSTGRES_DATABASE_URL is in the right format."""
        super().__init__(**kwargs)

        # Convert SQLAlchemy URL format to Tortoise ORM format if needed
        if self.POSTGRES_DATABASE_URL and "postgresql+" in self.POSTGRES_DATABASE_URL:
            self.POSTGRES_DATABASE_URL = self.POSTGRES_DATABASE_URL.replace("postgresql+psycopg://", "postgres://")


# Global settings instance to be imported by other modules
settings = Settings()


def get_settings() -> Settings:
    """Return the settings instance."""
    return settings

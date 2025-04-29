"""Configuration settings for the API service."""

from typing import Dict
import os
import re
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


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

    # Logging Settings
    LOG_LEVEL: str = "INFO"

    # AI Agent Settings
    OPENAI_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o"
    MANAGER_OPENAI_TEMPERATURE: float = 0.2
    OPENAI_PLANNER_TEMPERATURE: float = 0.3
    OPENAI_EXECUTOR_TEMPERATURE: float = 0.0
    OPENAI_VERIFIER_TEMPERATURE: float = 0.2
    MODEL_NAME: str = "gpt-4o"
    AGENT_TYPE: str = "assistant"
    TEMPERATURE: float = 0.2

    # Generic storage for LLM provider API keys - populated dynamically
    llm_api_keys: Dict[str, str] = {}

    class Config:
        """Pydantic settings configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Allow extra fields from env vars

    @model_validator(mode="after")
    def load_llm_api_keys(self):
        """Load all LLM provider API keys from environment variables."""
        api_key_pattern = re.compile(r"^(.+)_API_KEY$")

        # Scan environment for *_API_KEY variables
        for env_var, value in os.environ.items():
            match = api_key_pattern.match(env_var)
            if match and value:  # Only store non-empty keys
                provider = match.group(1).lower()
                self.llm_api_keys[provider] = value

        return self

    def __init__(self, **kwargs):
        """Initialize settings and ensure POSTGRES_DATABASE_URL is in the right format."""
        super().__init__(**kwargs)

        # Convert SQLAlchemy URL format to Tortoise ORM format if needed
        if self.POSTGRES_DATABASE_URL and "postgresql+" in self.POSTGRES_DATABASE_URL:
            self.POSTGRES_DATABASE_URL = self.POSTGRES_DATABASE_URL.replace(
                "postgresql+psycopg://", "postgres://"
            )

    def get_api_key_for_provider(self, provider: str) -> str:
        """Get API key for a specific provider.

        Args:
            provider: Provider name (e.g., 'openai', 'groq')

        Returns:
            API key for the provider if found

        Raises:
            ValueError: If no API key is found for the provider
        """
        provider = provider.lower()

        # Special case for OpenAI since it's explicitly defined
        if provider == "openai":
            return self.OPENAI_API_KEY

        # Check in our dynamic dictionary
        api_key = self.llm_api_keys.get(provider)
        if not api_key:
            raise ValueError(f"No API key found for provider '{provider}'")

        return api_key


# Global settings instance to be imported by other modules
settings = Settings()


def get_settings() -> Settings:
    """Return the settings instance."""
    return settings

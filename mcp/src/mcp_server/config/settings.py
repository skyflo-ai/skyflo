"""Configuration settings for Skyflo.ai MCP Server."""

from typing import List
from pydantic import validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """MCP Server configuration settings.
    
    These settings can be configured using environment variables.
    """
    
    # Application Configuration
    APP_NAME: str
    APP_VERSION: str
    APP_DESCRIPTION: str
    DEBUG: bool = False
    
    # Server Settings
    LOG_LEVEL: str = "INFO"
    
    # Retry Configuration
    MAX_RETRY_ATTEMPTS: int = 3
    RETRY_BASE_DELAY: float = 60  # Base delay in seconds
    RETRY_MAX_DELAY: float = 60 * 5  # Maximum delay in seconds
    RETRY_EXPONENTIAL_BASE: float = 2.0  # Base for exponential backoff
    
    class Config:
        """Pydantic settings configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance to be imported by other modules
settings = Settings()


def get_settings() -> Settings:
    """Return the settings instance."""
    return settings


# Legacy function to support existing code
def get_config() -> Settings:
    """Legacy function that returns the settings instance."""
    return settings

import logging
from typing import Literal, Optional

from pydantic import Field, conint
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    APP_NAME: str
    APP_VERSION: str
    APP_DESCRIPTION: str

    # FIX 1: Proper ENV field for Pydantic
    ENV: Optional[str] = Field(default="development")

    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"

    LOG_LEVEL: str = "INFO"

    POSTGRES_DATABASE_URL: str = Field(default="postgres://postgres:postgres@localhost:5432/skyflo")

    CHECKPOINTER_DATABASE_URL: Optional[str] = Field(default=None)
    ENABLE_POSTGRES_CHECKPOINTER: bool = Field(default=True)

    REDIS_URL: str = "redis://localhost:6379/0"

    RATE_LIMITING_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 100

    JWT_SECRET: str = "CHANGE_ME_IN_PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    MCP_SERVER_URL: str = "http://127.0.0.1:8888/mcp"

    INTEGRATIONS_SECRET_NAMESPACE: Optional[str] = Field(default="default")

    MAX_AUTO_CONTINUE_TURNS: int = 2

    LLM_MODEL: Optional[str] = Field(default="openai/gpt-4o", env="LLM_MODEL")
    LLM_HOST: Optional[str] = Field(default=None, env="LLM_HOST")
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")

    LLM_MAX_ITERATIONS: int = 25
    LLM_MAX_TOKENS: Optional[conint(ge=1)] = Field(default=None, env="LLM_MAX_TOKENS")

    LLM_REASONING_EFFORT: Optional[Literal["low", "medium", "high", "default"]] = Field(
        default=None, env="LLM_REASONING_EFFORT"
    )

    LLM_THINKING_BUDGET_TOKENS: Optional[conint(ge=0)] = Field(
        default=None, env="LLM_THINKING_BUDGET_TOKENS"
    )

    AGENT_TYPE: str = "assistant"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        DEFAULT_SECRET = "CHANGE_ME_IN_PRODUCTION"

        env = (self.ENV or "").strip().lower()

        # FIX 2: ENV whitelist validation
        allowed_envs = {"development", "staging", "test", "production"}

        if env not in allowed_envs:
            raise ValueError("ENV must be one of 'development', 'staging', 'test', or 'production'")

        if self.JWT_SECRET == DEFAULT_SECRET:
            if env == "production":
                raise ValueError(
                    "Cannot start application in production with default JWT_SECRET. "
                    "Set a secure JWT_SECRET environment variable."
                )
            else:
                logger.warning(
                    "Using insecure default JWT_SECRET. "
                    "This is allowed in development but must be changed before production."
                )

        if self.POSTGRES_DATABASE_URL and "postgresql+" in self.POSTGRES_DATABASE_URL:
            self.POSTGRES_DATABASE_URL = self.POSTGRES_DATABASE_URL.replace(
                "postgresql+psycopg://", "postgres://"
            )

        if not self.CHECKPOINTER_DATABASE_URL:
            self.CHECKPOINTER_DATABASE_URL = self._get_checkpointer_url()

    def _get_checkpointer_url(self) -> str:
        url = self.POSTGRES_DATABASE_URL

        if "sslmode=" not in url:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}sslmode=disable"

        return url


settings = Settings()


def get_settings() -> Settings:
    return settings

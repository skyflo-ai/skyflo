from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    APP_NAME: str
    APP_VERSION: str
    APP_DESCRIPTION: str
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
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # One week in minutes
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    MCP_SERVER_URL: str = "http://127.0.0.1:8888"

    MAX_AUTO_CONTINUE_TURNS: int = 2

    LLM_MODEL: Optional[str] = Field(default="openai/gpt-4o", env="LLM_MODEL")
    LLM_HOST: Optional[str] = Field(default=None, env="LLM_HOST")
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    LLM_MAX_ITERATIONS: int = 25

    LLM_TEMPERATURE: float = 0.2
    MODEL_NAME: str = "gpt-4o"
    AGENT_TYPE: str = "assistant"
    TEMPERATURE: float = 0.2

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

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

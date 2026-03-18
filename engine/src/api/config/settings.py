import logging
from typing import Any, Literal, Optional

from litellm import get_model_info
from pydantic import Field, conint
from pydantic_settings import BaseSettings


logger = logging.getLogger(__name__)


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

    def validate_llm_model(self) -> Optional[dict[str, Any]]:
        model_name = self.LLM_MODEL
        if not model_name:
            return None

        try:
            model_info = get_model_info(model=model_name)
        except Exception as e:
            logger.warning(
                "Could not validate LLM_MODEL '%s' against LiteLLM registry: %s. "
                "Startup will continue for possible self-hosted/custom models. "
                "See https://models.litellm.ai/ for registry-backed models.",
                model_name,
                e,
            )
            return None

        missing_capabilities: list[str] = []
        if not model_info.get("supports_function_calling", False):
            missing_capabilities.append("supports_function_calling")
        if not model_info.get("supports_response_schema", False):
            missing_capabilities.append("supports_response_schema")

        if missing_capabilities:
            missing_str = ", ".join(missing_capabilities)
            raise ValueError(
                f"Incompatible LLM_MODEL '{model_name}': missing required capability/capabilities: "
                f"{missing_str}. Skyflo Engine requires tool/function calling and structured "
                f"outputs support. Choose a compatible model at https://models.litellm.ai/."
            )

        return model_info


settings = Settings()


def get_settings() -> Settings:
    return settings

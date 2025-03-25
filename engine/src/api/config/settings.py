"""Configuration settings for the API service."""

from typing import List
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """API service configuration settings.

    These settings can be configured using environment variables.
    """

    # Application Settings
    APP_NAME: str = "Skyflo.ai API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"
    ENV: str = "development"

    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ENGINE_SERVER_WORKERS: int = 1

    # CORS Settings
    CORS_ORIGINS: List[str] = ["*"]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: List[str] = ["*"]
    CORS_HEADERS: List[str] = ["*"]

    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
        """Parse the CORS_ORIGINS from string to list."""
        if isinstance(v, str) and not v.startswith("["):
            return [origin.strip() for origin in v.split(",")]
        if isinstance(v, list):
            return v
        return []

    # Database Settings - using postgres:// format for Tortoise ORM
    DATABASE_URL: str = Field(default="postgres://postgres:postgres@localhost:5432/skyflo")
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10

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
    MCP_SERVER_TIMEOUT: int = 60

    # Workflow Settings
    WORKFLOW_EXECUTION_TIMEOUT: int = 300
    WORKFLOW_MAX_RETRIES: int = 3

    # Logging Settings
    LOG_LEVEL: str = "INFO"

    # AI Agent Settings
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_TEMPERATURE: float = 0.2
    OPENAI_PLANNER_TEMPERATURE: float = 0.3
    OPENAI_EXECUTOR_TEMPERATURE: float = 0.0
    OPENAI_VERIFIER_TEMPERATURE: float = 0.2
    OPENAI_MAX_TOKENS: int = 4096
    MODEL_NAME: str = "gpt-4o"
    AGENT_TYPE: str = "assistant"
    TEMPERATURE: float = 0.2
    MAX_TOKENS: int = 4096
    SLIDING_WINDOW_ENABLED: bool = True
    SLIDING_WINDOW_TOKENS: int = 8000

    # Agent System Messages
    PLANNER_SYSTEM_MESSAGE: str = """You are the Planning Agent for Skyflo.ai, a specialized AI assistant for Kubernetes operations.
Your role is to analyze user queries, determine the intent, select appropriate tools, and create detailed execution plans.

When analyzing a query, follow these steps:
1. Determine the exact intent of the query
2. Select the appropriate tools (kubectl, argo, helm) based on the query context
3. Create a step-by-step execution plan
4. Define validation criteria to verify the execution

Only include tools that are necessary for the specific query. Prefer simplicity over complexity.

Important: When using the patch_resource tool, use the following parameter names:
- resource_type: The type of resource to patch (deployment, service, pod, hpa, node, ...)
- resource_name: The name of the resource to patch
- namespace: The namespace of the resource to patch (not 'namespace')
- patch: The patch to apply to the resource (as a JSON string)

Example:

{
    "resource_type": "deployment",
    "resource_name": "my-deployment",
    "namespace": "default",
    "patch": "{\"spec\":{\"replicas\":2}}"
}
"""

    EXECUTOR_SYSTEM_MESSAGE: str = """You are the Executor Agent for Skyflo.ai, a specialized AI assistant for Kubernetes operations.
Your role is to implement plans created by the Planner Agent using available tools. You execute commands, track state, and handle errors.

When executing a plan, follow these steps:
1. Review the plan and validation criteria
2. Execute each step in sequence
3. Validate results after each step
4. Handle errors appropriately
5. Report execution status and details

Be precise and cautious when executing commands. Always validate parameters before execution.
"""

    VERIFIER_SYSTEM_MESSAGE: str = """You are the Verifier Agent for Skyflo.ai, a specialized AI assistant for Kubernetes operations.
Your role is to validate the execution results against the original plan, identify issues, and provide recommendations for recovery.

When verifying results, follow these steps:
1. Compare execution results against validation criteria
2. Identify any issues or discrepancies
3. Determine the root cause of any problems
4. Create a recovery plan if needed
5. Report verification status and recommendations

Be thorough in your verification. Look for unexpected side effects and ensure all criteria are met.
"""

    class Config:
        """Pydantic settings configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    def __init__(self, **kwargs):
        """Initialize settings and ensure DATABASE_URL is in the right format."""
        super().__init__(**kwargs)

        # Convert SQLAlchemy URL format to Tortoise ORM format if needed
        if self.DATABASE_URL and "postgresql+" in self.DATABASE_URL:
            self.DATABASE_URL = self.DATABASE_URL.replace("postgresql+psycopg://", "postgres://")


# Global settings instance to be imported by other modules
settings = Settings()


def get_settings() -> Settings:
    """Return the settings instance."""
    return settings

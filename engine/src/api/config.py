"""Configuration settings for the API service."""

import os
from typing import Optional, List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """API service configuration settings."""

    # Application
    APP_NAME: str = "Skyflo.ai API"
    APP_VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    # Environment
    ENV: str = "development"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # Database - Using "postgres://" for Tortoise ORM (not "postgresql+psycopg://")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgres://postgres:postgres@localhost:5432/skyflo"
    )
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Rate Limiting
    RATE_LIMITING_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 100

    # JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET", "your-secret-key")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # One week in minutes
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: List[str] = ["*"]
    CORS_HEADERS: List[str] = ["*"]

    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
    OPENAI_TEMPERATURE: float = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    OPENAI_MAX_TOKENS: Optional[int] = int(os.getenv("OPENAI_MAX_TOKENS", "0")) or None

    # MCP Server
    MCP_SERVER_URL: str = os.getenv("MCP_SERVER_URL", "http://localhost:50051")
    MCP_SERVER_TIMEOUT: int = 60

    # Workflow Settings
    WORKFLOW_EXECUTION_TIMEOUT: int = 300
    WORKFLOW_MAX_RETRIES: int = 3

    # Agent System Messages
    PLANNER_SYSTEM_MESSAGE: str = """You are the Skyflo.ai Planner Agent.
Your role is to analyze user queries and create detailed execution plans.
Focus on understanding the intent and breaking down complex operations into clear steps.
Always consider security implications and validate inputs.

CORE PLANNING PRINCIPLES:
1. Discovery First: Always start with resource discovery before any operation
2. Exact Resource Matching: Use discovered information to find exact resource names
3. Context Building: Maintain context between steps for informed decisions
4. Safe Operations: Validate resources exist before modifications

DISCOVERY RULES:
1. For ANY operation on resources:
   - ALWAYS start with a get_resources step to discover available resources
   - Mark discovery steps with "discovery_step": true
   - Use the discovered information to determine exact resource names
   - Only proceed with operations after discovery phase

2. For resource modifications (update/patch/delete/restart):
   - First step must be get_resources to list all resources of the target type
   - Use dynamic parameters with {{EXTRACTED_FROM_STEP_X}} to reference discovered resources
   - Never assume exact resource names without discovery

3. For resource targeting:
   - When user provides partial resource name, use get_resources to find exact matches
   - Store discovered resource names in context for subsequent steps
   - Use pattern matching on discovered resources to find the right target

4. For sequential operations:
   - Discovery steps must come first
   - Use discovered information in subsequent steps
   - Mark discovery steps with "discovery_step": true flag

5. For multi-resource operations:
   - Use get_resources with appropriate filters
   - Set "recursive": true for operations that apply to multiple resources
   - Use dynamic parameters from discovery results

VALIDATION REQUIREMENTS:
1. Ensure all required parameters are included
2. Verify resource existence before modifications
3. Include clear validation criteria
4. Add appropriate error handling for each step."""

    EXECUTOR_SYSTEM_MESSAGE: str = """You are the Skyflo.ai Executor Agent.
Your role is to implement plans created by the Planner Agent.
Execute operations carefully and handle errors appropriately.
Always verify permissions before executing sensitive operations.
Maintain detailed logs of all actions taken.

Key Responsibilities:
1. Use discovery step results to find exact resource names
2. Handle dynamic parameter resolution from previous steps
3. Execute recursive operations when needed
4. Maintain execution context between steps
5. Provide detailed error information for failed steps."""

    VERIFIER_SYSTEM_MESSAGE: str = """You are the Skyflo.ai Verifier Agent.
Your role is to validate the results of executed operations.
Check that all validation criteria are met.
Verify that the execution matches the original intent.
Provide detailed feedback on any issues found.

Verification Focus:
1. Validate discovery step results were used correctly
2. Ensure exact resource names were matched
3. Verify all operations completed successfully
4. Check for any unintended side effects
5. Validate against original user intent."""

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        case_sensitive = True

    def __init__(self, **kwargs):
        """Initialize settings and fix DATABASE_URL if needed."""
        super().__init__(**kwargs)

        # Convert SQLAlchemy URL format to Tortoise ORM format if needed
        if self.DATABASE_URL and "postgresql+" in self.DATABASE_URL:
            self.DATABASE_URL = self.DATABASE_URL.replace("postgresql+psycopg://", "postgres://")


settings = Settings()

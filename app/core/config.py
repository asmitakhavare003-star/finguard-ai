"""Application configuration loaded from environment variables / `.env`.

Uses Pydantic Settings so values are typed and validated at startup. Sensitive
credentials use ``SecretStr`` so accidental ``print``/``repr``/log calls do not
expose raw API keys.
"""

from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated runtime settings for FinGuard AI.

    Values are read from process environment variables, falling back to the
    project-root ``.env`` file. Required secrets fail fast if missing.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Application ---
    PROJECT_NAME: str = "FinGuard AI"
    ENVIRONMENT: str = "development"

    # --- OpenAI ---
    # SecretStr masks the value in logs/repr (shows as '**********') so keys
    # are less likely to leak when settings objects are logged during debugging.
    # Use `.get_secret_value()` only at the call site that needs the raw key.
    OPENAI_API_KEY: SecretStr

    # --- Qdrant ---
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[SecretStr] = None

    # --- LangSmith / LangChain tracing ---
    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGCHAIN_API_KEY: Optional[SecretStr] = Field(
        default=None,
        description=(
            "Optional LangSmith API key. Stored as SecretStr for the same "
            "reason as OPENAI_API_KEY: avoid leaking credentials via logs."
        ),
    )
    LANGCHAIN_PROJECT: str = "finguard-ai"


# Single shared instance imported by the rest of the app.
settings = Settings()

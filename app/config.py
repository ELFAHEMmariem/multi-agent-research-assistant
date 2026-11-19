
from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    groq_api_key: SecretStr
    groq_model: str = "openai/gpt-oss-20b"

    tavily_api_key: SecretStr | None = None

    redis_url: str = "redis://localhost:6379"

    max_subquestions: int = Field(default=3, ge=1, le=10)
    max_searches_per_question: int = Field(default=2, ge=1)
    max_total_tokens: int = Field(default=15000, gt=0)
    max_revisions: int = Field(default=1, ge=0)
    max_run_seconds: int = Field(default=240, gt=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()

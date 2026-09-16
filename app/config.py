from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    groq_api_key: str
    tavily_api_key: str
    redis_url: str = "redis://localhost:6379/0"

    max_sub_questions: int = 5
    max_searches_per_sq: int = 4
    max_total_tokens: int = 50_000
    wall_clock_seconds: int = 240
    max_results_per_domain: int = 2

    groq_model: str = "openai/gpt-oss-20b"
    groq_model_fast: str = "openai/gpt-oss-20b"

    class Config:
        env_file = ".env"


settings = Settings()
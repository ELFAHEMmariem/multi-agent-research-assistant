
from langchain_groq import ChatGroq

from app.config import get_settings


def get_llm() -> ChatGroq:
    settings = get_settings()

    return ChatGroq(
        model=settings.groq_model,
        api_key=settings.groq_api_key.get_secret_value(),
        temperature=0,
        max_tokens=1024,
        timeout=30,
        max_retries=1,
    )

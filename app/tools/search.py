
from tavily import TavilyClient

from app.config import get_settings


def web_search(query: str) -> list[dict]:
    settings = get_settings()

    if settings.tavily_api_key is None:
        raise ValueError("TAVILY_API_KEY is missing")

    client = TavilyClient(
        api_key=settings.tavily_api_key.get_secret_value()
    )

    response = client.search(
        query=query,
        search_depth="basic",
        max_results=3,
    )

    return response.get("results", [])

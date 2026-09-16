"""Tavily search wrapper — raises typed errors the researcher agent catches."""
from tavily import TavilyClient
from app.config import settings

_client = TavilyClient(api_key=settings.tavily_api_key)


class RateLimitError(Exception):
    pass


async def tavily_search(query: str, max_results: int = 5) -> list[dict]:
    try:
        response = _client.search(query=query, max_results=max_results)
    except Exception as e:
        if "rate" in str(e).lower() or "429" in str(e):
            raise RateLimitError(str(e)) from e
        raise
    return response.get("results", [])


from tavily import TavilyClient

from app.config import get_settings


class ResearchToolError(Exception):
    def __init__(self, status: str, message: str):
        super().__init__(message)
        self.status = status


def create_tavily_client() -> TavilyClient:
    settings = get_settings()

    if settings.tavily_api_key is None:
        raise ResearchToolError(
            "error",
            "TAVILY_API_KEY is missing"
        )

    return TavilyClient(
        api_key=settings.tavily_api_key.get_secret_value()
    )


def web_search(query: str) -> list[dict]:
    client = create_tavily_client()

    response = client.search(
        query=query,
        search_depth="basic",
        max_results=5,
    )

    return response.get("results", [])

def classify_tool_error(exc: Exception) -> str:
    status_code = getattr(
        exc,
        "status_code",
        None,
    )

    response = getattr(exc, "response", None)

    if status_code is None and response is not None:
        status_code = getattr(
            response,
            "status_code",
            None,
        )

    if status_code == 429:
        return "rate_limited"

    if isinstance(exc, TimeoutError):
        return "timeout"

    name = type(exc).__name__.lower()

    if "timeout" in name:
        return "timeout"

    if "ratelimit" in name:
        return "rate_limited"

    return "error"


from tavily import TavilyClient

from app.tools.search import create_tavily_client


def extract_pages(
    urls: list[str],
    client: TavilyClient | None = None,
) -> dict:
    if not urls:
        return {
            "results": [],
            "failed_results": [],
        }

    if client is None:
        client = create_tavily_client()

    response = client.extract(
        urls=urls,
        extract_depth="basic",
    )

    return {
        "results": response.get("results", []),
        "failed_results": response.get(
            "failed_results", []
        ),
    }


def get_useful_content(
    page: dict,
    max_chars: int = 6000,
) -> str:
    content = page.get("raw_content") or ""

    content = " ".join(content.split())

    if not content:
        return ""

    return content[:max_chars]

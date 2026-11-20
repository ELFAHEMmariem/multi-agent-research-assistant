
from app.tools.extract import (
    extract_pages,
    get_useful_content,
)


class FakeTavilyClient:
    def extract(self, urls, extract_depth):
        return {
            "results": [
                {
                    "url": urls[0],
                    "raw_content": (
                        "This is a simulated web article."
                    ),
                }
            ],
            "failed_results": [],
        }


def test_extract_page():
    result = extract_pages(
        ["https://example.org/article"],
        client=FakeTavilyClient(),
    )

    assert len(result["results"]) == 1
    assert result["failed_results"] == []


def test_clean_content():
    page = {
        "raw_content": "AI   security\n requires controls."
    }

    content = get_useful_content(page)

    assert content == "AI security requires controls."

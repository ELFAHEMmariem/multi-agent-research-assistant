
from app.tools.dedup import (
    deduplicate_results,
    normalize_url,
)


def test_normalize_tracking_url():
    url = (
        "https://EXAMPLE.com/article/"
        "?utm_source=google"
    )

    assert normalize_url(url) == (
        "https://example.com/article"
    )


def test_remove_duplicate_urls():
    results = [
        {"url": "https://example.com/article"},
        {"url": "https://example.com/article/"},
        {"url": "https://other.org/report"},
    ]

    unique = deduplicate_results(results)

    assert len(unique) == 2


def test_domain_limit():
    results = [
        {"url": f"https://example.com/article-{i}"}
        for i in range(4)
    ]

    unique = deduplicate_results(
        results,
        max_per_domain=2,
    )

    assert len(unique) == 2

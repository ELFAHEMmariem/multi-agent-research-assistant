from app.tools.dedup import dedupe_by_domain


def test_caps_results_per_domain():
    results = [
        {"url": "https://example.com/a"},
        {"url": "https://example.com/b"},
        {"url": "https://example.com/c"},  # 3rd from same domain, should be dropped
        {"url": "https://other.com/x"},
    ]
    out = dedupe_by_domain(results, cap=2)
    assert len(out) == 3
    urls = {r["url"] for r in out}
    assert "https://example.com/c" not in urls


def test_removes_exact_duplicate_urls():
    results = [{"url": "https://a.com/1"}, {"url": "https://a.com/1"}]
    out = dedupe_by_domain(results, cap=5)
    assert len(out) == 1

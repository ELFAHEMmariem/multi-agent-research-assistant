"""URL dedup + per-domain cap so one site can't dominate a report."""
from urllib.parse import urlparse


def dedupe_by_domain(results: list[dict], cap: int = 2) -> list[dict]:
    seen_urls: set[str] = set()
    domain_counts: dict[str, int] = {}
    out: list[dict] = []

    for r in results:
        url = r.get("url", "")
        if not url or url in seen_urls:
            continue
        domain = urlparse(url).netloc
        if domain_counts.get(domain, 0) >= cap:
            continue
        seen_urls.add(url)
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
        out.append(r)

    return out

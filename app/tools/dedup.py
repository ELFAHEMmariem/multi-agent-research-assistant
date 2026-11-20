
from urllib.parse import (
    parse_qsl,
    urlencode,
    urlsplit,
    urlunsplit,
)


TRACKING_PARAMS = {
    "fbclid",
    "gclid",
    "msclkid",
}


def normalize_url(url: str) -> str:
    parts = urlsplit(url)

    scheme = parts.scheme.lower()
    hostname = (parts.hostname or "").lower()

    if scheme not in {"http", "https"} or not hostname:
        raise ValueError(f"Invalid HTTP URL: {url}")

    netloc = hostname

    if parts.port is not None:
        default_port = (
            (scheme == "http" and parts.port == 80)
            or (scheme == "https" and parts.port == 443)
        )
        if not default_port:
            netloc = f"{hostname}:{parts.port}"

    path = parts.path.rstrip("/") or "/"

    query_params = [
        (key, value)
        for key, value in parse_qsl(
            parts.query,
            keep_blank_values=True,
        )
        if not key.lower().startswith("utm_")
        and key.lower() not in TRACKING_PARAMS
    ]

    query = urlencode(sorted(query_params))

    return urlunsplit(
        (scheme, netloc, path, query, "")
    )


def deduplicate_results(
    results: list[dict],
    max_per_domain: int = 2,
    max_total: int = 5,
) -> list[dict]:
    unique = []
    seen_urls = set()
    domain_counts = {}

    for result in results:
        url = result.get("url")

        if not url:
            continue

        try:
            normalized = normalize_url(url)
        except ValueError:
            continue

        if normalized in seen_urls:
            continue

        domain = urlsplit(normalized).hostname

        if domain_counts.get(domain, 0) >= max_per_domain:
            continue

        seen_urls.add(normalized)
        domain_counts[domain] = (
            domain_counts.get(domain, 0) + 1
        )

        unique.append({
            **result,
            "url": normalized,
        })

        if len(unique) >= max_total:
            break

    return unique

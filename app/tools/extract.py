"""Full-page fetch + extraction — never trust the search snippet, it's truncated."""
import asyncio
import httpx
import trafilatura


class PaywallError(Exception):
    pass


class FetchTimeoutError(Exception):
    pass


PAYWALL_MARKERS = ["subscribe to continue", "this content is for subscribers", "sign in to read"]


async def fetch_and_extract(url: str, timeout: float = 8.0) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (research-bot)"})
    except (httpx.TimeoutException, httpx.ConnectTimeout):
        raise FetchTimeoutError(url)
    except httpx.HTTPError:
        return None

    if resp.status_code != 200:
        return None

    html = resp.text
    lowered = html.lower()
    if any(marker in lowered for marker in PAYWALL_MARKERS):
        raise PaywallError(url)

    text = trafilatura.extract(html)
    return text

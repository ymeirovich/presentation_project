from typing import Any, Dict, Optional
import logging
import httpx
import asyncio

log = logging.getLogger("agent.ahttp")

_DEFAULT_TIMEOUT = 10.0  # seconds

# Create a module-level AsyncClient so connections are reused (performance).
# We set limits to avoid opening too many connections at once.
_client: httpx.AsyncClient | None = None


async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=_DEFAULT_TIMEOUT,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            follow_redirects=True,
        )
    return _client


async def aget_json(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Async GET that returns JSON. Raises httpx.HTTPStatusError on 4xx/5xx errors.
    """

    client = await get_client()
    try:
        resp = await client.get(url, params=params, headers=headers)
        resp.raise_for_status()  # raises for HTTP errors(4xx/5xx)
        return resp.json()
    except httpx.RequestError as e:
        # Network/timeout/DNS errors
        log.error("Network error requesting %s: %s", url, e)
        raise
    except httpx.HTTPStatusError as e:
        # HTTP error with access to response
        body = (e.response.text or "")[:300]
        log.error("HTTP %s for %s. Body starts: %r", e.response.status_code, url, body)

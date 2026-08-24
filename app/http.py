import asyncio

import httpx

from app.config import settings

client = httpx.AsyncClient(timeout=settings.request_timeout_seconds)


async def get_json(url: str, params: dict | None = None) -> dict:
    """GET a URL and return its JSON body, retrying transient network errors."""
    for attempt in range(settings.max_retries):
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except (httpx.TimeoutException, httpx.ConnectError):
            if attempt == settings.max_retries - 1:
                raise
            await asyncio.sleep(2**attempt)

    raise httpx.RequestError("request failed after retries")


async def close() -> None:
    await client.aclose()

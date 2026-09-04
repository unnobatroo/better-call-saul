import asyncio
from collections.abc import Mapping
from typing import TypeAlias

import httpx

from app.config import settings

QueryValue: TypeAlias = str | int | float
QueryParams = Mapping[str, QueryValue]

client = httpx.AsyncClient(timeout=settings.request_timeout_seconds)


async def get_json(url: str, params: QueryParams | None = None) -> dict[str, object]:
    """GET a URL and return its JSON body, retrying transient network errors."""
    for attempt in range(settings.max_retries):
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("upstream response must be a JSON object")
            return data
        except (httpx.TimeoutException, httpx.ConnectError):
            if attempt == settings.max_retries - 1:
                raise
            await asyncio.sleep(2**attempt)

    raise httpx.RequestError("request failed after retries")


async def close() -> None:
    await client.aclose()

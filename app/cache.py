import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import CacheEntry


async def get_cached(db: AsyncSession, key: str) -> dict | None:
    result = await db.execute(
        select(CacheEntry.response).where(
            CacheEntry.cache_key == key,
            CacheEntry.expires_at > time.time(),
        )
    )
    return result.scalar_one_or_none()


async def set_cached(
    db: AsyncSession, key: str, response: dict, ttl_seconds: int | None = None
) -> None:
    ttl = ttl_seconds if ttl_seconds is not None else settings.cache_ttl_seconds
    result = await db.execute(select(CacheEntry).where(CacheEntry.cache_key == key))
    entry = result.scalar_one_or_none()

    if entry:
        entry.response = response
        entry.expires_at = time.time() + ttl
    else:
        db.add(CacheEntry(cache_key=key, response=response, expires_at=time.time() + ttl))

    await db.commit()

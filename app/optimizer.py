import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import get_cached, set_cached
from app.circuit_breaker import CircuitBreaker
from app.providers import PROVIDERS
from app.router import rank_providers
from app.schemas import WeatherRequest, WeatherResponse
from app.stats import ProviderStats


class ProviderUnavailableError(Exception):
    """No provider can be reached right now (not configured / circuit open)."""


class UpstreamError(Exception):
    """Every provider errored while handling the request."""


class WeatherOptimizer:
    def __init__(self) -> None:
        self.providers = PROVIDERS
        self.breakers: dict[str, CircuitBreaker] = {
            provider.name: CircuitBreaker() for provider in self.providers
        }
        self.stats: dict[str, ProviderStats] = {
            provider.name: ProviderStats() for provider in self.providers
        }

    @staticmethod
    def _cache_key(request: WeatherRequest) -> str:
        return f"weather:{request.city}" if request.city else f"weather:{request.lat}:{request.lon}"

    async def get_weather(self, db: AsyncSession, request: WeatherRequest) -> WeatherResponse:
        key = self._cache_key(request)

        if (cached := await get_cached(db, key)) is not None:
            return WeatherResponse(**cached, cached=True)

        configured = [p for p in self.providers if p.is_configured]
        if not configured:
            raise ProviderUnavailableError("no weather providers are configured")

        transient_error: Exception | None = None
        shape_error: ValueError | None = None
        open_count = 0

        for provider in rank_providers(request.strategy, configured, self.stats):
            breaker = self.breakers[provider.name]
            if breaker.is_open():
                open_count += 1
                continue

            start = time.perf_counter()
            try:
                data = await provider.fetch(request.city, request.lat, request.lon)
            except ValueError as exc:
                shape_error = exc
                continue
            except Exception as exc:
                transient_error = exc
                breaker.record_failure()
                self.stats[provider.name].record_failure()
                continue

            latency_ms = (time.perf_counter() - start) * 1000
            breaker.record_success()
            self.stats[provider.name].record_success(latency_ms, provider.cost)

            await set_cached(db, key, data.model_dump(mode="json"), request.freshness_seconds)
            return WeatherResponse(**data.model_dump(), cached=False)

        if transient_error is not None:
            raise UpstreamError("all providers failed") from transient_error
        if open_count:
            raise ProviderUnavailableError("all providers are temporarily unavailable")
        if shape_error is not None:
            raise shape_error
        raise ProviderUnavailableError("no provider could handle this request")

    def stats_snapshot(self) -> dict:
        return {
            provider.name: {
                "configured": provider.is_configured,
                "cost": provider.cost,
                **self.stats[provider.name].as_dict(),
            }
            for provider in self.providers
        }


optimizer = WeatherOptimizer()

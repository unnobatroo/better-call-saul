import time

from sqlalchemy.ext.asyncio import AsyncSession
from typing_extensions import TypedDict

from app.cache import get_cached, set_cached
from app.circuit_breaker import CircuitBreaker
from app.providers import PROVIDERS, ProviderResponseError
from app.router import rank_providers
from app.schemas import WeatherPayload, WeatherRequest, WeatherResponse
from app.stats import ProviderStats


class ProviderUnavailableError(Exception):
    """No provider can be reached right now (not configured / circuit open)."""


class UpstreamError(Exception):
    """Every provider errored while handling the request."""


class ProviderMetrics(TypedDict):
    configured: bool
    cost: float
    successes: int
    failures: int
    success_rate: float | None
    avg_latency_ms: float | None
    total_cost: float


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

        last_transient_error: Exception | None = None
        last_shape_error: ValueError | None = None
        skipped_count = 0

        for provider in rank_providers(request.strategy, configured, self.stats):
            breaker = self.breakers[provider.name]
            if breaker.is_open():
                skipped_count += 1
                continue

            start = time.perf_counter()
            try:
                data = await provider.fetch(request.city, request.lat, request.lon)
            except ProviderResponseError as exc:
                last_transient_error = exc
                breaker.record_failure()
                self.stats[provider.name].record_failure()
                continue
            except ValueError as exc:
                last_shape_error = exc
                continue
            # Provider implementations are an extension boundary.
            except Exception as exc:
                last_transient_error = exc
                breaker.record_failure()
                self.stats[provider.name].record_failure()
                continue

            latency_ms = (time.perf_counter() - start) * 1000
            breaker.record_success()
            self.stats[provider.name].record_success(latency_ms, provider.cost)

            payload = WeatherPayload(data.model_dump(mode="json"))
            await set_cached(db, key, payload, request.freshness_seconds)
            return WeatherResponse.model_validate({**payload, "cached": False})

        if last_transient_error is not None:
            raise UpstreamError("all providers failed") from last_transient_error
        if skipped_count:
            raise ProviderUnavailableError("all providers are temporarily unavailable")
        if last_shape_error is not None:
            raise last_shape_error
        raise ProviderUnavailableError("no provider could handle this request")

    def stats_snapshot(self) -> dict[str, ProviderMetrics]:
        return {
            provider.name: {
                "configured": provider.is_configured,
                "cost": provider.cost,
                **self.stats[provider.name].as_dict(),
            }
            for provider in self.providers
        }


optimizer = WeatherOptimizer()

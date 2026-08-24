from operator import attrgetter

from app.providers.base import WeatherProvider
from app.stats import ProviderStats


def _latency(provider: WeatherProvider, stats: dict[str, ProviderStats]) -> float:
    measured = stats[provider.name].avg_latency_ms
    return measured if measured is not None else float(provider.estimated_latency_ms)


def _reliability(provider: WeatherProvider, stats: dict[str, ProviderStats]) -> float:
    measured = stats[provider.name].success_rate
    return measured if measured is not None else provider.default_reliability


def rank_providers(
    strategy: str | None,
    providers: list[WeatherProvider],
    stats: dict[str, ProviderStats],
) -> list[WeatherProvider]:
    """Order providers best-first; live metrics beat the static priors."""
    strategy = strategy or "reliable"

    if strategy == "cheap":
        return sorted(providers, key=attrgetter("cost"))
    if strategy == "fast":
        return sorted(providers, key=lambda p: _latency(p, stats))
    return sorted(providers, key=lambda p: _reliability(p, stats), reverse=True)

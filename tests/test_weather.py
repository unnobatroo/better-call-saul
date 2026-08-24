from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from app.circuit_breaker import CircuitBreaker
from app.config import settings
from app.optimizer import optimizer
from app.providers.base import WeatherProvider, WeatherReport
from app.stats import ProviderStats


class FakeProvider(WeatherProvider):
    name = "fake"
    cost = 0.01
    estimated_latency_ms = 100
    default_reliability = 1.0

    def __init__(self, data: WeatherReport) -> None:
        self._data = data

    async def fetch(self, city: str | None, lat: float | None, lon: float | None) -> WeatherReport:
        return self._data


class FailingProvider(WeatherProvider):
    name = "failing"

    async def fetch(self, city: str | None, lat: float | None, lon: float | None) -> WeatherReport:
        raise RuntimeError("boom")


@pytest.fixture
def fake_data() -> WeatherReport:
    return WeatherReport(
        temperature_c=22.5,
        humidity_percent=55.0,
        pressure_hpa=1013.0,
        wind_speed_ms=3.5,
        source="fake",
        timestamp=datetime.now(UTC),
    )


def _install_provider(monkeypatch, provider: WeatherProvider) -> None:
    monkeypatch.setattr(optimizer, "providers", [provider])
    monkeypatch.setattr(optimizer, "breakers", {provider.name: CircuitBreaker()})
    monkeypatch.setattr(optimizer, "stats", {provider.name: ProviderStats()})


@pytest.fixture
def fake_provider(monkeypatch, fake_data: WeatherReport) -> FakeProvider:
    provider = FakeProvider(fake_data)
    _install_provider(monkeypatch, provider)
    return provider


@pytest.mark.asyncio
async def test_weather_ok(client: AsyncClient, fake_provider: FakeProvider):
    response = await client.get("/weather?city=budapest")
    assert response.status_code == 200
    data = response.json()
    assert data["temperature_c"] == 22.5
    assert data["source"] == "fake"
    assert data["cached"] is False


@pytest.mark.asyncio
async def test_weather_cached(client: AsyncClient, fake_provider: FakeProvider):
    first = await client.get("/weather?city=budapest")
    assert first.json()["cached"] is False

    second = await client.get("/weather?city=budapest")
    assert second.status_code == 200
    assert second.json()["cached"] is True


@pytest.mark.asyncio
async def test_weather_city_normalized(client: AsyncClient, fake_provider: FakeProvider):
    await client.get("/weather?city=Budapest")
    second = await client.get("/weather?city=budapest")
    assert second.json()["cached"] is True


@pytest.mark.asyncio
async def test_weather_missing_location(client: AsyncClient):
    response = await client.get("/weather")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_weather_invalid_strategy(client: AsyncClient):
    response = await client.get("/weather?city=budapest&strategy=bogus")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_fallback_to_next_provider(
    client: AsyncClient, fake_data: WeatherReport, monkeypatch
):
    failing = FailingProvider()
    good = FakeProvider(fake_data)
    monkeypatch.setattr(optimizer, "providers", [failing, good])
    monkeypatch.setattr(optimizer, "breakers", {p.name: CircuitBreaker() for p in (failing, good)})
    monkeypatch.setattr(optimizer, "stats", {p.name: ProviderStats() for p in (failing, good)})

    response = await client.get("/weather?city=budapest")

    assert response.status_code == 200
    assert response.json()["source"] == "fake"


@pytest.mark.asyncio
async def test_upstream_failure_502(client: AsyncClient, monkeypatch):
    _install_provider(monkeypatch, FailingProvider())
    response = await client.get("/weather?city=budapest")
    assert response.status_code == 502


@pytest.mark.asyncio
async def test_circuit_breaker_opens(client: AsyncClient, monkeypatch):
    _install_provider(monkeypatch, FailingProvider())

    for _ in range(settings.circuit_failure_threshold):
        response = await client.get("/weather?city=budapest")
        assert response.status_code == 502

    response = await client.get("/weather?city=budapest")
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_metrics_endpoint(client: AsyncClient, fake_provider: FakeProvider):
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert "fake" in response.json()


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import overload

from app.config import settings
from app.http import get_json
from app.providers.base import ProviderResponseError, WeatherProvider, WeatherReport


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ProviderResponseError(f"OpenWeather response field '{field}' is malformed")
    return value


@overload
def _number(value: object, field: str, *, required: True) -> float: ...


@overload
def _number(value: object, field: str, *, required: bool = False) -> float | None: ...


def _number(value: object, field: str, *, required: bool = False) -> float | None:
    if value is None and not required:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProviderResponseError(f"OpenWeather response field '{field}' is malformed")
    return float(value)


class OpenWeatherProvider(WeatherProvider):
    name = "openweather"
    cost = 0.02
    estimated_latency_ms = 300
    default_reliability = 0.95

    def __init__(self) -> None:
        self.api_key = settings.openweather_api_key

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def fetch(self, city: str | None, lat: float | None, lon: float | None) -> WeatherReport:
        if not self.api_key:
            raise ValueError("OpenWeather is not configured")

        params = {"appid": self.api_key, "units": "metric"}
        if city:
            params["q"] = city
        else:
            params["lat"] = lat
            params["lon"] = lon

        data = await get_json("https://api.openweathermap.org/data/2.5/weather", params)
        main = _mapping(data.get("main", {}), "main")
        wind = _mapping(data.get("wind", {}), "wind")
        return WeatherReport(
            temperature_c=_number(main.get("temp"), "main.temp", required=True),
            humidity_percent=_number(main.get("humidity"), "main.humidity"),
            pressure_hpa=_number(main.get("pressure"), "main.pressure"),
            wind_speed_ms=_number(wind.get("speed"), "wind.speed"),
            source=self.name,
            timestamp=datetime.now(UTC),
        )

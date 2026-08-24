from datetime import UTC, datetime

from app.config import settings
from app.http import get_json
from app.providers.base import WeatherProvider, WeatherReport


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
        main = data.get("main", {})
        wind = data.get("wind", {})
        return WeatherReport(
            temperature_c=main.get("temp", 0.0),
            humidity_percent=main.get("humidity"),
            pressure_hpa=main.get("pressure"),
            wind_speed_ms=wind.get("speed"),
            source=self.name,
            timestamp=datetime.now(UTC),
        )

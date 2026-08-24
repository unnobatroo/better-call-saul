from app.providers.base import WeatherProvider, WeatherReport
from app.providers.nasa_power import NasaPowerProvider
from app.providers.openweather import OpenWeatherProvider

PROVIDERS: list[WeatherProvider] = [
    OpenWeatherProvider(),
    NasaPowerProvider(),
]

__all__ = [
    "WeatherReport",
    "WeatherProvider",
    "NasaPowerProvider",
    "OpenWeatherProvider",
    "PROVIDERS",
]

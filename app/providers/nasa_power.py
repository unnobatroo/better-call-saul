from collections.abc import Mapping
from datetime import UTC, datetime, timedelta

from app.http import get_json
from app.providers.base import ProviderResponseError, WeatherProvider, WeatherReport

_FILL_VALUE = -900.0
_LOOKBACK_DAYS = 7


def _latest_valid(values: Mapping[str, object]) -> float | None:
    """Most recent value that isn't NASA's -999 fill value."""
    for key in sorted(values, reverse=True):
        value = values[key]
        if value is not None and isinstance(value, (int, float)) and value > _FILL_VALUE:
            return value
    return None


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ProviderResponseError(f"NASA POWER response field '{field}' is malformed")
    return value


class NasaPowerProvider(WeatherProvider):
    name = "nasa_power"
    cost = 0.005
    estimated_latency_ms = 1200
    default_reliability = 0.85

    async def fetch(self, city: str | None, lat: float | None, lon: float | None) -> WeatherReport:
        if lat is None or lon is None:
            raise ValueError("NASA POWER needs 'lat' and 'lon'")

        now = datetime.now(UTC)
        data = await get_json(
            "https://power.larc.nasa.gov/api/temporal/daily/point",
            {
                "parameters": "T2M,RH2M,PS,WS10M",
                "community": "RE",
                "longitude": lon,
                "latitude": lat,
                # NASA daily data lags ~2 days, so look back a week.
                "start": (now - timedelta(days=_LOOKBACK_DAYS)).strftime("%Y%m%d"),
                "end": now.strftime("%Y%m%d"),
                "format": "JSON",
            },
        )

        properties = _mapping(data.get("properties", {}), "properties")
        params = _mapping(properties.get("parameter", {}), "properties.parameter")
        temperature = _latest_valid(_mapping(params.get("T2M", {}), "T2M"))
        if temperature is None:
            raise ValueError("no temperature data available for those coordinates")

        pressure_kpa = _latest_valid(_mapping(params.get("PS", {}), "PS"))
        return WeatherReport(
            temperature_c=temperature,
            humidity_percent=_latest_valid(_mapping(params.get("RH2M", {}), "RH2M")),
            pressure_hpa=pressure_kpa * 10 if pressure_kpa is not None else None,
            wind_speed_ms=_latest_valid(_mapping(params.get("WS10M", {}), "WS10M")),
            source=self.name,
            timestamp=now,
        )

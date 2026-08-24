from datetime import UTC, datetime, timedelta

from app.http import get_json
from app.providers.base import WeatherProvider, WeatherReport

_FILL_VALUE = -900.0
_LOOKBACK_DAYS = 7


def _latest_valid(values: dict[str, float]) -> float | None:
    """Most recent value that isn't NASA's -999 fill value."""
    for key in sorted(values, reverse=True):
        if (value := values[key]) is not None and value > _FILL_VALUE:
            return value
    return None


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

        params = data.get("properties", {}).get("parameter", {})
        temperature = _latest_valid(params.get("T2M", {}))
        if temperature is None:
            raise ValueError("no temperature data available for those coordinates")

        pressure_kpa = _latest_valid(params.get("PS", {}))
        return WeatherReport(
            temperature_c=temperature,
            humidity_percent=_latest_valid(params.get("RH2M", {})),
            pressure_hpa=pressure_kpa * 10 if pressure_kpa is not None else None,
            wind_speed_ms=_latest_valid(params.get("WS10M", {})),
            source=self.name,
            timestamp=now,
        )

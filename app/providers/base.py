from abc import ABC, abstractmethod
from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict


class WeatherReport(BaseModel):
    """The single format every provider is adapted to."""

    model_config = ConfigDict(frozen=True)

    temperature_c: float
    humidity_percent: float | None
    pressure_hpa: float | None
    wind_speed_ms: float | None
    source: str
    timestamp: datetime


class WeatherProvider(ABC):
    """Static cost + cold-start priors, later refined by live metrics."""

    name: ClassVar[str]
    cost: ClassVar[float] = 0.0
    estimated_latency_ms: ClassVar[int] = 0
    default_reliability: ClassVar[float] = 1.0

    @property
    def is_configured(self) -> bool:
        return True

    @abstractmethod
    async def fetch(self, city: str | None, lat: float | None, lon: float | None) -> WeatherReport:
        """Call the upstream API and return a normalized result."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Strategy = Literal["cheap", "fast", "reliable"]


class WeatherRequest(BaseModel):
    city: str | None = Field(None, min_length=1, max_length=100)
    lat: float | None = Field(None, ge=-90, le=90)
    lon: float | None = Field(None, ge=-180, le=180)
    strategy: Strategy | None = None
    freshness_seconds: int | None = Field(None, ge=0)

    @field_validator("city")
    @classmethod
    def _normalize_city(cls, value: str | None) -> str | None:
        return value.strip().lower() if value else value

    @model_validator(mode="after")
    def _require_location(self) -> "WeatherRequest":
        if self.city is None and (self.lat is None or self.lon is None):
            raise ValueError("Provide 'city' or both 'lat' and 'lon'")
        return self


class WeatherResponse(BaseModel):
    temperature_c: float
    humidity_percent: float | None = None
    pressure_hpa: float | None = None
    wind_speed_ms: float | None = None
    source: str
    cached: bool = False
    timestamp: datetime

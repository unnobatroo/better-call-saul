from sqlalchemy import JSON, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.schemas import WeatherPayload


class CacheEntry(Base):
    __tablename__ = "cache_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    cache_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    response: Mapped[WeatherPayload] = mapped_column(JSON)
    expires_at: Mapped[float] = mapped_column(Float)

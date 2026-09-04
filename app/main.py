from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, status

from app.database import Base, SessionDep, engine
from app.http import close as close_http
from app.optimizer import ProviderMetrics, ProviderUnavailableError, UpstreamError, optimizer
from app.schemas import HealthResponse, WeatherRequest, WeatherResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await close_http()
    await engine.dispose()


app = FastAPI(title="API Optimizer", version="0.4.0", lifespan=lifespan)


@app.get("/health")
async def health() -> HealthResponse:
    return {"status": "ok"}


@app.get("/metrics")
async def metrics() -> dict[str, ProviderMetrics]:
    return optimizer.stats_snapshot()


@app.get("/weather", response_model=WeatherResponse)
async def get_weather(
    db: SessionDep,
    request: Annotated[WeatherRequest, Query()],
) -> WeatherResponse:
    try:
        return await optimizer.get_weather(db, request)
    except ProviderUnavailableError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    except UpstreamError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc

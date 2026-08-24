import pytest

from app.providers.nasa_power import NasaPowerProvider


@pytest.mark.asyncio
async def test_nasa_skips_fill_values(monkeypatch):
    async def fake_get_json(url, params=None):
        return {
            "properties": {
                "parameter": {
                    "T2M": {"20260823": 26.5, "20260824": -999.0},
                    "RH2M": {"20260823": 60.0},
                    "PS": {"20260823": 99.5},
                    "WS10M": {"20260823": 3.2},
                }
            }
        }

    monkeypatch.setattr("app.providers.nasa_power.get_json", fake_get_json)

    result = await NasaPowerProvider().fetch(None, 47.49, 19.04)
    assert result.temperature_c == 26.5
    assert result.humidity_percent == 60.0
    assert result.pressure_hpa == 995.0
    assert result.wind_speed_ms == 3.2
    assert result.source == "nasa_power"


@pytest.mark.asyncio
async def test_nasa_all_fill_values_raises(monkeypatch):
    async def fake_get_json(url, params=None):
        return {"properties": {"parameter": {"T2M": {"20260823": -999.0, "20260824": -999.0}}}}

    monkeypatch.setattr("app.providers.nasa_power.get_json", fake_get_json)

    with pytest.raises(ValueError, match="no temperature data"):
        await NasaPowerProvider().fetch(None, 47.49, 19.04)

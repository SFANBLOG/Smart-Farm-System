"""气象：Open-Meteo 实时预报（未来 3 天），失败退化为季节性本地推演。带 10 分钟缓存。"""
from __future__ import annotations
import time
import random
from datetime import datetime, timedelta
import httpx
from app.config import settings

_cache: dict[str, tuple[float, list[dict]]] = {}


def _cache_get(key: str):
    item = _cache.get(key)
    if item and time.time() - item[0] < settings.WEATHER_CACHE_TTL:
        return item[1]
    return None


async def forecast(lat: float | None = None, lon: float | None = None, days: int = 3) -> list[dict]:
    lat = lat if lat is not None else settings.WEATHER_DEFAULT_LAT
    lon = lon if lon is not None else settings.WEATHER_DEFAULT_LON
    key = f"{round(lat,2)}:{round(lon,2)}:{days}"
    cached = _cache_get(key)
    if cached:
        return cached
    data = await _open_meteo(lat, lon, days)
    if data is None:
        data = _seasonal_local(lat, lon, days)
    _cache[key] = (time.time(), data)
    return data


async def _open_meteo(lat: float, lon: float, days: int) -> list[dict] | None:
    try:
        params = {
            "latitude": lat, "longitude": lon,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
            "forecast_days": days, "timezone": "auto",
        }
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(settings.WEATHER_API, params=params)
            r.raise_for_status()
            j = r.json()
        d = j["daily"]
        out = []
        for i, date in enumerate(d["time"]):
            out.append({
                "date": date, "source": "open-meteo",
                "temp_max": d["temperature_2m_max"][i], "temp_min": d["temperature_2m_min"][i],
                "rain": d["precipitation_sum"][i], "wind": d["wind_speed_10m_max"][i],
            })
        return out
    except Exception:
        return None


def _seasonal_local(lat: float, lon: float, days: int) -> list[dict]:
    """季节性 + 扰动本地推演：断网也能给出合理预报。"""
    now = datetime.now()
    month = now.month
    # 简化季节基准温度（北半球中纬度）
    base = 15 + 15 * _cos_seasonal(month)
    rnd = random.Random(int(now.strftime("%Y%m%d")) + int(lat * 10))
    out = []
    for i in range(days):
        day = (now + timedelta(days=i)).strftime("%Y-%m-%d")
        tmax = round(base + 4 + rnd.uniform(-3, 3), 1)
        tmin = round(tmax - 8 + rnd.uniform(-2, 2), 1)
        rain = round(max(0.0, rnd.gauss(3, 6)), 1)
        out.append({"date": day, "source": "local", "temp_max": tmax, "temp_min": tmin,
                    "rain": rain, "wind": round(rnd.uniform(1, 8), 1)})
    return out


def _cos_seasonal(month: int) -> float:
    import math
    return math.cos((month - 7) / 12.0 * 2 * math.pi)


async def next_24h_rain(lat: float | None = None, lon: float | None = None) -> float:
    fc = await forecast(lat, lon, days=2)
    return sum(d.get("rain", 0) or 0 for d in fc[:2])


async def has_heavy_rain(lat: float | None = None, lon: float | None = None, threshold: float = 15) -> bool:
    return await next_24h_rain(lat, lon) >= threshold

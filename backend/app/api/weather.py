"""气象模块：实时预报（Open-Meteo，失败退化本地推演）+ 历史记录。"""
from fastapi import APIRouter
from app.common.result import Result
from app.common.crud import to_page
from app.models import WeatherRecord, Field
from app.services import weather

router = APIRouter(prefix="/weather", tags=["气象"])


@router.get("/forecast", response_model=Result, summary="气象-未来预报")
async def forecast(field_id: int | None = None, days: int = 3):
    lat = lon = None
    if field_id:
        f = await Field.filter(id=field_id).first()
        if f:
            lat, lon = f.lat, f.lon
    data = await weather.forecast(lat, lon, days)
    return Result.ok(data)


@router.get("/history", response_model=Result, summary="气象-历史记录")
async def history(page: int = 1, size: int = 20):
    return Result.ok(await to_page(WeatherRecord, page, size, order="-id"))

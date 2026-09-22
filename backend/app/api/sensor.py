"""传感器模块：CRUD + 时序数据查询 + 批量上报 + 模拟数据 + 滑动窗口统计。"""
from fastapi import APIRouter, Query
from pydantic import BaseModel
from app.common.crud_router import build_crud_router
from app.common.crud import dump_one, to_page
from app.common.result import Result
from app.models import Sensor, SensorData
import random

router = build_crud_router(Sensor, "/sensor", "传感器")


class ReportItem(BaseModel):
    sensor_id: int
    value: float


@router.get("/{sensor_id}/data", response_model=Result, summary="传感器-时序数据")
async def sensor_data(sensor_id: int, limit: int = Query(100, ge=1, le=1000)):
    rows = await SensorData.filter(sensor_id=sensor_id).order_by("-ts").limit(limit)
    items = [{"id": r.id, "value": r.value, "ts": r.ts.isoformat(), "is_anomaly": r.is_anomaly}
             for r in reversed(rows)]
    return Result.ok(items)


@router.get("/{sensor_id}/stat", response_model=Result, summary="传感器-滑动窗口统计")
async def sensor_stat(sensor_id: int, window: int = Query(20, ge=2, le=500)):
    rows = await SensorData.filter(sensor_id=sensor_id).order_by("-ts").limit(window)
    vals = [r.value for r in rows]
    if not vals:
        return Result.ok({"count": 0})
    avg = sum(vals) / len(vals)
    trend = "stable"
    if len(vals) >= 4:
        recent, older = sum(vals[:3]) / 3, sum(vals[-3:]) / 3
        trend = "up" if recent > older * 1.03 else ("down" if recent < older * 0.97 else "stable")
    return Result.ok({"count": len(vals), "avg": round(avg, 2), "max": max(vals),
                      "min": min(vals), "trend": trend})


@router.post("/report", response_model=Result, summary="传感器-批量上报")
async def report(items: list[ReportItem]):
    objs = [SensorData(sensor_id=i.sensor_id, value=i.value) for i in items]
    await SensorData.bulk_create(objs)
    return Result.ok({"created": len(objs)})


@router.post("/simulate/{sensor_id}", response_model=Result, summary="传感器-生成模拟数据")
async def simulate(sensor_id: int, count: int = Query(10, ge=1, le=200)):
    sensor = await Sensor.filter(id=sensor_id).first()
    if not sensor:
        return Result.fail("传感器不存在", 404)
    rnd = random.Random()
    base = {"soil_moisture": 55, "temp": 25, "humidity": 65, "light": 30000, "ph": 6.8}.get(sensor.metric, 50)
    objs = [SensorData(sensor_id=sensor_id, value=round(base + rnd.uniform(-8, 8), 2))
            for _ in range(count)]
    await SensorData.bulk_create(objs)
    return Result.ok({"created": count})

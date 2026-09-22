"""大屏总览：核心指标、传感器曲线、预警看板、病虫害地图、影像墙、指令流、引擎与 LLM 健康。"""
from fastapi import APIRouter
from app.common.result import Result
from app.common.crud import dump_one
from app.models import (Field, Crop, Sensor, SensorData, Device, DeviceCommand, Alert,
                        Diagnosis, Media)
from app.agent import engine

router = APIRouter(prefix="/dashboard", tags=["大屏"])


@router.get("/overview", response_model=Result, summary="大屏-总览")
async def overview():
    fields = await Field.all()
    alerts_open = await Alert.filter(status="open").order_by("-id").limit(20)
    devices = await Device.all().limit(50)
    commands = await DeviceCommand.all().order_by("-id").limit(20)
    diagnoses = await Diagnosis.all().order_by("-id").limit(20)
    medias = await Media.all().order_by("-id").limit(12)
    crops = await Crop.all().limit(50)

    # 核心指标
    core = {
        "field_count": len(fields),
        "total_area": round(sum(f.area or 0 for f in fields), 1),
        "device_count": len(devices),
        "device_online": sum(1 for d in devices if d.online),
        "alert_open": len(alerts_open),
        "alert_urgent": sum(1 for a in alerts_open if a.level == "紧急"),
        "diagnosis_count": len(diagnoses),
    }

    # 传感器曲线（每类取最近点）
    sensor_rows = await Sensor.all().limit(30)
    curves = []
    for s in sensor_rows:
        d = await SensorData.filter(sensor_id=s.id).order_by("-ts").limit(20)
        curves.append({"sensor": s.name, "metric": s.metric, "unit": s.unit,
                       "points": [{"ts": x.ts.isoformat(), "value": x.value} for x in reversed(d)]})

    # 病虫害地图（按地块聚合）
    pest_map = {}
    for dg in diagnoses:
        key = dg.field_id or 0
        pest_map.setdefault(key, {"field_id": key, "count": 0, "severity": []})
        pest_map[key]["count"] += 1
        pest_map[key]["severity"].append(dg.severity)

    return Result.ok({
        "core": core,
        "alerts": [dump_one(a) for a in alerts_open],
        "commands": [{"id": c.id, "device_id": c.device_id, "action": c.action,
                      "passed": c.passed, "blocked_reason": c.blocked_reason,
                      "source": c.source, "created_at": c.created_at.isoformat()} for c in commands],
        "curves": curves,
        "pest_map": list(pest_map.values()),
        "media_wall": [{"id": m.id, "path": m.path, "kind": m.kind} for m in medias],
        "crops": [{"name": c.name, "stage": c.stage, "field_id": c.field_id} for c in crops],
        "engine": engine.routing_table(),
    })

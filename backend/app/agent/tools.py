"""Agent 工具层：一切动作都走这里（感知/查询/检索/视觉/控制/预警/配置读取）。
控制类工具内嵌安全校验，拦截即留痕。工具为纯异步函数，离线/在线模式共用。
（如已安装 langchain，可用 @tool 装饰这些函数供 LLM function-calling 使用。）"""
from __future__ import annotations
import uuid
from datetime import datetime, timedelta

from app.models import (Field, Crop, Sensor, SensorData, Device, DeviceCommand,
                        Alert, Diagnosis, WeatherRecord)
from app.services import weather, vision, device_guard
from app.rag import retriever


# ---------- 感知类 ----------
async def tool_perceive(field_id: int | None) -> dict:
    """多源数据清洗、异常过滤、气象融合，输出标准化"农场现状"。"""
    fld = await Field.filter(id=field_id).first() if field_id else await Field.first()
    if not fld:
        return {"ok": False, "reason": "无地块数据"}
    crop = await Crop.filter(field_id=fld.id).first()
    sensors = await Sensor.filter(field_id=fld.id)
    metrics = {}
    anomalies = []
    for s in sensors:
        d = await SensorData.filter(sensor_id=s.id).order_by("-ts").limit(20)
        if not d:
            continue
        vals = [x.value for x in d]
        avg = sum(vals) / len(vals)
        if _is_anomaly(s.metric, avg):
            anomalies.append({"metric": s.metric, "value": round(avg, 2), "unit": s.unit})
        metrics[s.metric] = {"avg": round(avg, 2), "max": round(max(vals), 2),
                             "min": round(min(vals), 2), "unit": s.unit,
                             "trend": _trend(vals)}
    fc = await weather.forecast(fld.lat, fld.lon, days=3)
    return {
        "ok": True, "field": {"id": fld.id, "name": fld.name, "area": fld.area,
                              "soil_type": fld.soil_type},
        "crop": {"name": crop.name, "stage": crop.stage, "variety": crop.variety} if crop else None,
        "metrics": metrics, "anomalies": anomalies,
        "weather": fc, "rain_24h": sum(d.get("rain", 0) or 0 for d in fc[:1]),
    }


def _is_anomaly(metric: str, v: float) -> bool:
    table = {"soil_moisture": (20, 90), "temp": (-5, 42), "humidity": (15, 98),
             "ph": (4.5, 9.0), "light": (0, 200000)}
    lo, hi = table.get(metric, (float("-inf"), float("inf")))
    return v < lo or v > hi


def _trend(vals: list[float]) -> str:
    if len(vals) < 3:
        return "stable"
    recent = sum(vals[:3]) / 3
    older = sum(vals[-3:]) / 3
    if recent > older * 1.05:
        return "up"
    if recent < older * 0.95:
        return "down"
    return "stable"


# ---------- 检索类 ----------
async def tool_retrieve(query: str, top_k: int | None = None) -> list[dict]:
    return await retriever.retrieve(query, top_k)


# ---------- 视觉类 ----------
async def tool_vision(path: str) -> dict:
    return vision.analyze_remote_or_local(path)


# ---------- 控制类（带安全护栏） ----------
async def tool_control(request_id: str, action: str, device_id: int | None,
                       params: dict | None = None, source: str = "agent") -> dict:
    """下发 IoT 指令，先过安全校验。拦截留痕。"""
    params = params or {}
    device = await Device.filter(id=device_id).first() if device_id else \
        await Device.filter(type=_action_to_device(action)).first()
    if not device:
        return {"ok": False, "blocked": True, "reason": "未找到目标设备"}
    passed, reason = await device_guard.safety_check(action, device, params)
    cmd = await DeviceCommand.create(
        request_id=request_id, device=device, action=action, params=params,
        source=source, passed=passed, blocked_reason=None if passed else reason,
        executed=passed,
    )
    if passed:
        device.status = "running"
        await device.save()
    return {"ok": passed, "blocked": not passed, "reason": reason,
            "command_id": cmd.id, "device": device.name, "action": action}


def _action_to_device(action: str) -> str:
    return {"irrigate": "pump", "spray": "sprayer", "ventilate": "fan"}.get(action, "valve")


# ---------- 预警类 ----------
async def tool_alert(request_id: str, field_id: int | None, type_: str, level: str,
                     title: str, detail: str) -> dict:
    """创建预警，同地块同类型未关闭的自动去重合并。"""
    exist = await Alert.filter(field_id=field_id, type=type_, status="open").first()
    if exist:
        exist.detail = detail
        exist.level = _higher_level(exist.level, level)
        await exist.save()
        return {"ok": True, "merged": True, "alert_id": exist.id, "level": exist.level}
    a = await Alert.create(request_id=request_id, field_id=field_id, type=type_,
                           level=level, title=title, detail=detail, status="open")
    return {"ok": True, "merged": False, "alert_id": a.id, "level": level}


def _higher_level(a: str, b: str) -> str:
    order = {"一般": 1, "重要": 2, "紧急": 3}
    return a if order.get(a, 0) >= order.get(b, 0) else b


# ---------- 配置读取类 ----------
async def tool_read_llm_config() -> dict:
    from app.models import LLMConfig
    from app.config import settings
    active = await LLMConfig.filter(is_active=True).first()
    return {
        "llm_enabled": bool(active) or settings.LLM_ENABLED,
        "provider": active.provider if active else "local",
        "model": active.model if active else "local-rule-engine",
        "engine": settings.ENGINE_MODE,
    }


def new_request_id() -> str:
    return uuid.uuid4().hex[:16]

"""设备控制安全护栏：每条 Agent 指令都要过校验，不通过则拦截并记录原因。"""
from __future__ import annotations
from app.models import Device, Sensor, SensorData, Field
from app.services import weather


async def latest_sensor_value(field_id: int | None, metric: str) -> float | None:
    if not field_id:
        return None
    sensor = await Sensor.filter(field_id=field_id, metric=metric).first()
    if not sensor:
        return None
    data = await SensorData.filter(sensor_id=sensor.id).order_by("-ts").first()
    return data.value if data else None


async def check_irrigation(device: Device, params: dict) -> tuple[bool, str]:
    """灌溉安全校验：土壤湿度上限 / 未来 24h 强降雨 / 水泵在线 / 水源充足。"""
    if not device.online:
        return False, "设备离线，无法下发灌溉指令"
    field_id = device.field_id
    moisture = await latest_sensor_value(field_id, "soil_moisture")
    if moisture is not None and moisture >= (params.get("moisture_upper", 75)):
        return False, f"土壤湿度已达 {moisture:.1f}%，超过上限，无需灌溉"
    fld = await Field.filter(id=field_id).first() if field_id else None
    lat = fld.lat if fld else None
    lon = fld.lon if fld else None
    if await weather.has_heavy_rain(lat, lon):
        rain = await weather.next_24h_rain(lat, lon)
        return False, f"未来 24h 预计强降雨 {rain:.1f}mm，暂缓灌溉"
    if params.get("water_level", 100) < 20:
        return False, "水源水位不足，禁止启动水泵"
    return True, "校验通过"


async def check_spray(device: Device, params: dict) -> tuple[bool, str]:
    """打药安全校验：设备在线 + 风力不过大（避免飘移）。"""
    if not device.online:
        return False, "施药设备离线"
    fld = await Field.filter(id=device.field_id).first() if device.field_id else None
    if fld:
        fc = await weather.forecast(fld.lat, fld.lon, days=1)
        if fc and (fc[0].get("wind") or 0) > 6:
            return False, f"风力 {fc[0].get('wind')}m/s 过大，存在药液飘移风险，暂缓施药"
    return True, "校验通过"


async def check_generic(device: Device, params: dict) -> tuple[bool, str]:
    if not device.online:
        return False, "设备离线"
    return True, "校验通过"


_CHECKERS = {
    "irrigate": check_irrigation,
    "spray": check_spray,
}


async def safety_check(action: str, device: Device, params: dict) -> tuple[bool, str]:
    checker = _CHECKERS.get(action, check_generic)
    return await checker(device, params)

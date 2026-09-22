"""地块模块：标准 CRUD + 关联作物/设备/传感器聚合查询。"""
from fastapi import APIRouter
from app.common.crud_router import build_crud_router
from app.common.result import Result
from app.common.crud import dump_one
from app.models import Field, Crop, Device, Sensor

router = build_crud_router(Field, "/field", "地块")


@router.get("/{field_id}/detail", response_model=Result, summary="地块-聚合详情")
async def field_detail(field_id: int):
    fld = await Field.filter(id=field_id).first()
    if not fld:
        return Result.fail("地块不存在", 404)
    crops = [dump_one(c) for c in await Crop.filter(field_id=field_id)]
    devices = [dump_one(d) for d in await Device.filter(field_id=field_id)]
    sensors = [dump_one(s) for s in await Sensor.filter(field_id=field_id)]
    return Result.ok({**dump_one(fld), "crops": crops, "devices": devices, "sensors": sensors})

"""设备模块：标准 CRUD + 手动下发指令（同样过安全护栏）+ 指令流水查询。"""
from fastapi import APIRouter
from pydantic import BaseModel
from app.common.crud_router import build_crud_router
from app.common.crud import dump_one, to_page
from app.common.result import Result
from app.models import Device, DeviceCommand
from app.agent import tools

router = build_crud_router(Device, "/device", "设备")


class CmdIn(BaseModel):
    device_id: int
    action: str
    params: dict | None = None


@router.post("/command", response_model=Result, summary="设备-手动下发指令")
async def send_command(body: CmdIn):
    rid = tools.new_request_id()
    res = await tools.tool_control(rid, body.action, body.device_id, body.params or {}, source="manual")
    return Result.ok(res, "已下发" if res.get("ok") else f"已拦截：{res.get('reason')}")


@router.get("/{device_id}/commands", response_model=Result, summary="设备-指令流水")
async def device_commands(device_id: int, page: int = 1, size: int = 20):
    qs = DeviceCommand.filter(device_id=device_id)
    data = await to_page(qs, page, size, order="-id")
    return Result.ok(data)

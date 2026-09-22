"""农事规划模块：CRUD + 发起规划（感知→规划→控制）+ 状态流转。"""
from fastapi import APIRouter
from pydantic import BaseModel
from app.common.crud_router import build_crud_router
from app.common.result import Result
from app.models import FarmTask
from app.agent import service

router = build_crud_router(FarmTask, "/task", "农事计划")


class PlanIn(BaseModel):
    field_id: int | None = None
    user_input: str = ""


@router.post("/run", response_model=Result, summary="农事-发起规划")
async def run_plan(body: PlanIn):
    state = await service.run_pipeline("plan", body.user_input, body.field_id)
    return Result.ok({"request_id": state.get("request_id"), "plan": state.get("plan", {}),
                      "control": state.get("control", {})}, "农事规划完成")


class StatusIn(BaseModel):
    status: str


@router.post("/{task_id}/status", response_model=Result, summary="农事-更新状态")
async def set_status(task_id: int, body: StatusIn):
    t = await FarmTask.filter(id=task_id).first()
    if not t:
        return Result.fail("任务不存在", 404)
    t.status = body.status
    await t.save()
    return Result.ok({"id": task_id, "status": body.status})

"""Agent 编排模块：跑任意任务类型 + 实时路由表 + 节点级日志审计（按 request_id 复盘）。"""
from fastapi import APIRouter
from pydantic import BaseModel
from app.common.result import Result
from app.common.crud import to_page
from app.models import AgentLog
from app.agent import engine, service

router = APIRouter(prefix="/agent", tags=["Agent编排"])


class RunIn(BaseModel):
    task_type: str = "chat"   # diagnose/growth/plan/control/alert/chat/full
    user_input: str = ""
    field_id: int | None = None
    media_paths: list[str] | None = None


@router.get("/engine", response_model=Result, summary="引擎-路由表与健康")
async def engine_info():
    return Result.ok(engine.routing_table())


@router.post("/run", response_model=Result, summary="引擎-执行任务链")
async def run(body: RunIn):
    if body.task_type not in engine.ROUTES:
        return Result.fail(f"未知任务类型：{body.task_type}", 400)
    state = await service.run_pipeline(body.task_type, body.user_input, body.field_id, body.media_paths)
    return Result.ok({
        "request_id": state.get("request_id"), "task_type": body.task_type,
        "status": state.get("status"), "need_confirm": state.get("need_confirm", False),
        "perception": state.get("perception", {}), "diagnosis": state.get("diagnosis", {}),
        "growth": state.get("growth", {}), "plan": state.get("plan", {}),
        "control": state.get("control", {}), "alert": state.get("alert", {}),
        "answer": state.get("answer", {}), "trace": state.get("trace", []),
    })


@router.get("/logs", response_model=Result, summary="审计-节点日志分页")
async def logs(page: int = 1, size: int = 20, request_id: str | None = None):
    qs = AgentLog.filter(request_id=request_id) if request_id else AgentLog.all()
    return Result.ok(await to_page(qs, page, size, order="-id"))


@router.get("/trace/{request_id}", response_model=Result, summary="审计-按 request_id 复盘")
async def trace(request_id: str):
    rows = await AgentLog.filter(request_id=request_id).order_by("id")
    return Result.ok([{"node": r.node, "phase": r.phase, "payload": r.payload,
                       "cost_ms": r.cost_ms, "status": r.status, "ts": r.ts.isoformat()}
                      for r in rows])

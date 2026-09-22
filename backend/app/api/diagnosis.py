"""诊断模块：CRUD + 发起诊断（跑流水线）+ Human-in-the-loop resume/reject。"""
from fastapi import APIRouter
from pydantic import BaseModel
from app.common.crud_router import build_crud_router
from app.common.crud import dump_one
from app.common.result import Result
from app.models import Diagnosis
from app.agent import service

router = build_crud_router(Diagnosis, "/diagnosis", "病虫害诊断")


class DiagnoseIn(BaseModel):
    field_id: int | None = None
    media_paths: list[str] | None = None
    user_input: str = ""


class ResumeIn(BaseModel):
    decision: str  # approve / reject


@router.post("/run", response_model=Result, summary="诊断-发起（感知→诊断→人工介入→规划→控制）")
async def run_diagnose(body: DiagnoseIn):
    state = await service.run_pipeline("diagnose", body.user_input, body.field_id, body.media_paths)
    diag = state.get("diagnosis", {})
    return Result.ok({
        "request_id": state.get("request_id"),
        "status": state.get("status"),
        "need_confirm": state.get("need_confirm", False),
        "diagnosis": diag,
        "plan": state.get("plan", {}),
        "control": state.get("control", {}),
    }, "诊断完成（等待人工确认）" if state.get("need_confirm") else "诊断完成")


@router.post("/{diagnosis_id}/resume", response_model=Result, summary="诊断-人工确认/驳回")
async def resume(diagnosis_id: int, body: ResumeIn):
    res = await service.resume_diagnosis(diagnosis_id, body.decision)
    if not res.get("ok"):
        return Result.fail(res.get("reason", "处理失败"), 400)
    return Result.ok(res, "已确认并执行" if body.decision == "approve" else "已驳回")

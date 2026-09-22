"""生长诊断模块：CRUD + 发起长势诊断（感知→长势→规划）+ 历史曲线。"""
from fastapi import APIRouter
from pydantic import BaseModel
from app.common.crud_router import build_crud_router
from app.common.crud import dump_one
from app.common.result import Result
from app.models import GrowthDiagnosis
from app.agent import service

router = build_crud_router(GrowthDiagnosis, "/growth", "作物生长诊断")


class GrowthIn(BaseModel):
    field_id: int | None = None
    user_input: str = ""


@router.post("/run", response_model=Result, summary="长势-发起诊断")
async def run_growth(body: GrowthIn):
    state = await service.run_pipeline("growth", body.user_input, body.field_id)
    return Result.ok({"request_id": state.get("request_id"), "growth": state.get("growth", {}),
                      "plan": state.get("plan", {})}, "长势诊断完成")


@router.get("/history/{field_id}", response_model=Result, summary="长势-历史曲线")
async def history(field_id: int):
    rows = await GrowthDiagnosis.filter(field_id=field_id).order_by("-id").limit(30)
    items = [{"id": r.id, "score": r.score, "green_index": r.green_index,
              "stage": r.stage, "created_at": r.created_at.isoformat()} for r in reversed(rows)]
    return Result.ok(items)

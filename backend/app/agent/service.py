"""Agent 业务服务：跑一次流水线并把结果落库（诊断/长势/计划/指令/预警），供 API 复用。"""
from __future__ import annotations
from datetime import datetime

from app.agent import engine, tools
from app.models import Diagnosis, GrowthDiagnosis, FarmTask, Alert, Crop, Field


def engine_status() -> dict:
    return engine.routing_table()


async def run_pipeline(task_type: str, user_input: str = "", field_id: int | None = None,
                       media_paths: list[str] | None = None) -> dict:
    rid = tools.new_request_id()
    state = {
        "request_id": rid, "task_type": task_type, "user_input": user_input,
        "field_id": field_id, "media_paths": media_paths or [], "trace": [],
    }
    state = await engine.run(state)
    await persist(state)
    return state


async def persist(state: dict) -> None:
    """把状态结果落库，形成可追溯记录。"""
    rid = state.get("request_id")
    field_id = (state.get("perception", {}).get("field") or {}).get("id") or state.get("field_id")

    diag = state.get("diagnosis")
    if diag and diag.get("disease"):
        await Diagnosis.create(
            request_id=rid, field_id=field_id, disease=diag["disease"],
            severity=diag.get("severity", "轻度"), confidence=diag.get("confidence", 0),
            pesticide=diag.get("pesticide"), dosage=diag.get("dosage"),
            safety_interval=diag.get("safety_interval"),
            withdrawal_period=diag.get("withdrawal_period"),
            suggestion=diag.get("text"), knowledge_refs=diag.get("refs"),
            need_confirm=diag.get("need_confirm", False),
            status="pending" if diag.get("need_confirm") else "done",
        )

    growth = state.get("growth")
    if growth and growth.get("score") is not None:
        crop = await Crop.filter(field_id=field_id).first() if field_id else None
        await GrowthDiagnosis.create(
            request_id=rid, field_id=field_id, crop_id=crop.id if crop else None,
            score=growth.get("score", 0), green_index=growth.get("green_index", 0),
            nutrient_issue=growth.get("nutrient_issue"), stage=growth.get("stage"),
            days_to_harvest=growth.get("days_to_harvest"),
            estimated_yield=growth.get("estimated_yield"), analysis=growth.get("analysis"),
        )

    plan = state.get("plan")
    if plan:
        for t in plan.get("tasks", []):
            await FarmTask.create(
                request_id=rid, field_id=field_id, type=t.get("type"),
                title=t.get("title"), detail=t.get("objective"),
                priority=t.get("priority", "normal"), objective=t.get("objective"),
                plan_start=_parse(t.get("when")), status="pending",
            )

    alert = state.get("alert")
    if alert:
        for r in alert.get("risks", []):
            pass  # tool_alert 已落库去重，无需重复创建


def _parse(s):
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


async def resume_diagnosis(diagnosis_id: int, decision: str) -> dict:
    """Human-in-the-loop：确认执行 / 驳回。"""
    d = await Diagnosis.filter(id=diagnosis_id).first()
    if not d:
        return {"ok": False, "reason": "诊断记录不存在"}
    if decision == "approve":
        d.confirmed = True
        d.status = "confirmed"
        await d.save()
        # 确认后继续执行规划与控制
        state = {"request_id": d.request_id or tools.new_request_id(), "task_type": "plan",
                 "field_id": d.field_id, "resume_decision": "approve", "trace": [],
                 "diagnosis": {"disease": d.disease, "severity": d.severity}}
        state = await engine.run(state)
        await persist(state)
        return {"ok": True, "status": "confirmed", "commands": state.get("control", {}).get("commands")}
    else:
        d.status = "rejected"
        await d.save()
        return {"ok": True, "status": "rejected"}

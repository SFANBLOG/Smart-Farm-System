"""预警模块：CRUD + 单地块研判 + 全农场并发巡检（SCAN_CONCURRENCY）+ 解除闭环。"""
import asyncio
from fastapi import APIRouter
from pydantic import BaseModel
from app.common.crud_router import build_crud_router
from app.common.result import Result
from app.config import settings
from app.models import Alert, Field
from app.agent import service

router = build_crud_router(Alert, "/alert", "预警")


class AlertIn(BaseModel):
    field_id: int | None = None


@router.post("/run", response_model=Result, summary="预警-单地块研判")
async def run_alert(body: AlertIn):
    state = await service.run_pipeline("alert", "", body.field_id)
    return Result.ok({"request_id": state.get("request_id"), "alert": state.get("alert", {})}, "研判完成")


@router.post("/scan", response_model=Result, summary="预警-全农场并发巡检")
async def scan_all():
    fields = await Field.all()
    sem = asyncio.Semaphore(settings.SCAN_CONCURRENCY)
    results = []

    async def one(f: Field):
        async with sem:
            st = await service.run_pipeline("alert", "", f.id)
            return {"field": f.name, "risks": st.get("alert", {}).get("risks", [])}

    results = await asyncio.gather(*[one(f) for f in fields])
    total = sum(len(r["risks"]) for r in results)
    return Result.ok({"fields": len(fields), "risks": total, "detail": results},
                     f"巡检完成，共 {total} 条风险")


@router.post("/{alert_id}/resolve", response_model=Result, summary="预警-解除闭环")
async def resolve(alert_id: int):
    from datetime import datetime
    a = await Alert.filter(id=alert_id).first()
    if not a:
        return Result.fail("预警不存在", 404)
    a.status = "closed"
    a.resolved_at = datetime.now()
    await a.save()
    return Result.ok({"id": alert_id, "status": "closed"})

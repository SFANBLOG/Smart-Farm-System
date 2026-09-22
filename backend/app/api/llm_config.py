"""大模型配置模块：CRUD + 启用/热切换 + 连通性测试。切换后即时生效。"""
import httpx
from fastapi import APIRouter
from pydantic import BaseModel
from app.common.crud_router import build_crud_router
from app.common.crud import dump_one
from app.common.result import Result
from app.models import LLMConfig

router = build_crud_router(LLMConfig, "/llm-config", "大模型配置")


@router.post("/{config_id}/activate", response_model=Result, summary="配置-启用(热切换)")
async def activate(config_id: int):
    cfg = await LLMConfig.filter(id=config_id).first()
    if not cfg:
        return Result.fail("配置不存在", 404)
    await LLMConfig.all().update(is_active=False)
    cfg.is_active = True
    await cfg.save()
    _apply_to_settings(cfg)
    return Result.ok(dump_one(cfg), f"已切换到 {cfg.name}")


def _apply_to_settings(cfg: LLMConfig):
    """把启用的配置热写入运行时 settings。"""
    from app.config import settings
    if cfg.provider == "local":
        settings.LLM_ENABLED = False
        return
    settings.LLM_ENABLED = True
    settings.LLM_BASE_URL = cfg.base_url or settings.LLM_BASE_URL
    settings.LLM_API_KEY = cfg.api_key or settings.LLM_API_KEY
    settings.LLM_MODEL = cfg.model
    settings.EMBEDDING_MODEL = cfg.embedding_model or settings.EMBEDDING_MODEL


@router.get("/{config_id}/test", response_model=Result, summary="配置-连通性测试")
async def test(config_id: int):
    cfg = await LLMConfig.filter(id=config_id).first()
    if not cfg:
        return Result.fail("配置不存在", 404)
    if cfg.provider == "local":
        return Result.ok({"mode": "local", "ok": True}, "本地规则内核就绪")
    if not cfg.api_key:
        return Result.fail("未配置 API Key", 400)
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                f"{(cfg.base_url or '').rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {cfg.api_key}"},
                json={"model": cfg.model, "messages": [{"role": "user", "content": "ping"}],
                      "max_tokens": 5},
            )
            ok = r.status_code == 200
            return Result.ok({"ok": ok, "status": r.status_code},
                             "连通正常" if ok else f"连通失败: {r.text[:100]}")
    except Exception as e:
        return Result.fail(f"请求异常: {e}", 500)

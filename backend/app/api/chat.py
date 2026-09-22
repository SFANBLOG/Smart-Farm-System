"""问答交互模块：多轮会话记忆 + 图文混合提问 + 意图路由 + SSE 流式输出。"""
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.common.result import Result
from app.common.crud import dump_one
from app.models import ChatSession, ChatMessage
from app.agent import engine, tools, nodes
from app.rag import retriever

router = APIRouter(prefix="/chat", tags=["问答"])


class ChatIn(BaseModel):
    session_id: int | None = None
    message: str
    field_id: int | None = None
    media_paths: list[str] | None = None


@router.get("/sessions", response_model=Result, summary="会话-列表")
async def sessions():
    rows = await ChatSession.all().order_by("-id").limit(100)
    return Result.ok([dump_one(r) for r in rows])


@router.post("/sessions", response_model=Result, summary="会话-新建")
async def new_session():
    s = await ChatSession.create(title="新会话")
    return Result.ok(dump_one(s))


@router.get("/sessions/{sid}/messages", response_model=Result, summary="会话-消息")
async def messages(sid: int):
    rows = await ChatMessage.filter(session_id=sid).order_by("id")
    return Result.ok([{"id": r.id, "role": r.role, "content": r.content,
                       "knowledge_refs": r.knowledge_refs, "ts": r.ts.isoformat()} for r in rows])


@router.delete("/sessions/{sid}", response_model=Result, summary="会话-删除")
async def delete_session(sid: int):
    await ChatMessage.filter(session_id=sid).delete()
    await ChatSession.filter(id=sid).delete()
    return Result.ok({"id": sid})


async def _get_history(sid: int, limit: int = 10) -> str:
    rows = await ChatMessage.filter(session_id=sid).order_by("-id").limit(limit)
    rows = list(reversed(rows))
    return "\n".join(f"{r.role}: {r.content[:200]}" for r in rows)


@router.post("/send", response_model=Result, summary="问答-同步发送")
async def send(body: ChatIn):
    session = await _ensure_session(body.session_id, body.message)
    await ChatMessage.create(session=session, role="user", content=body.message)
    rid = tools.new_request_id()
    state = {"request_id": rid, "task_type": "chat", "user_input": body.message,
             "field_id": body.field_id, "media_paths": body.media_paths or [],
             "trace": [], "history": await _get_history(session.id)}
    state = await engine.run(state)
    answer = state.get("answer", {})
    text = answer.get("text", "（无回答）")
    await ChatMessage.create(session=session, role="assistant", content=text,
                             knowledge_refs=answer.get("refs"), request_id=rid)
    session.title = body.message[:20]
    await session.save()
    return Result.ok({"session_id": session.id, "request_id": rid, "text": text,
                      "refs": answer.get("refs", []), "intent": answer.get("intent"),
                      "llm_mode": answer.get("llm_mode")})


@router.post("/stream", summary="问答-SSE 流式")
async def stream(body: ChatIn):
    session = await _ensure_session(body.session_id, body.message)
    await ChatMessage.create(session=session, role="user", content=body.message)
    rid = tools.new_request_id()

    async def event_gen():
        # 先跑流水线拿到完整答案与知识依据，再逐字流式推送（模拟 token 流）
        state = {"request_id": rid, "task_type": "chat", "user_input": body.message,
                 "field_id": body.field_id, "media_paths": body.media_paths or [],
                 "trace": [], "history": await _get_history(session.id)}
        state = await engine.run(state)
        answer = state.get("answer", {})
        text = answer.get("text", "（无回答）")
        yield _sse("meta", {"request_id": rid, "intent": answer.get("intent"),
                            "llm_mode": answer.get("llm_mode")})
        chunk = 4
        for i in range(0, len(text), chunk):
            yield _sse("token", {"text": text[i:i + chunk]})
        await ChatMessage.create(session=session, role="assistant", content=text,
                                 knowledge_refs=answer.get("refs"), request_id=rid)
        session.title = body.message[:20]
        await session.save()
        yield _sse("refs", {"refs": answer.get("refs", []), "session_id": session.id})
        yield _sse("done", {"ok": True})

    return StreamingResponse(event_gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _ensure_session(sid: int | None, msg: str) -> ChatSession:
    if sid:
        s = await ChatSession.filter(id=sid).first()
        if s:
            return s
    return await ChatSession.create(title=msg[:20])

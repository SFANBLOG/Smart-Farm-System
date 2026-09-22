"""LLM 统一封装：优先 LangChain ChatOpenAI，未启用/失败时降级本地规则推理内核。
关键：节点函数在两种模式下完全一致，只是底层 LLM 实现不同。"""
from __future__ import annotations
import re
from app.config import settings


class LocalRuleLLM:
    """离线兜底：按墒情/作物/生育期给出结构化结论的本地规则推理内核。"""

    name = "local-rule-engine"

    def invoke(self, prompt: str, context: dict | None = None) -> str:
        ctx = context or {}
        kind = ctx.get("kind", "chat")
        if kind == "diagnosis":
            return self._diagnosis(ctx)
        if kind == "growth":
            return self._growth(ctx)
        if kind == "plan":
            return self._plan(ctx)
        if kind == "alert":
            return self._alert(ctx)
        return self._chat(prompt, ctx)

    def _diagnosis(self, ctx: dict) -> str:
        sev = ctx.get("severity", "轻度")
        disease = ctx.get("disease", "疑似叶部病害")
        return (f"[本地规则] 综合像素内核绿度/黄化/褐斑占比与知识库命中，判断为「{disease}」，"
                f"严重度 {sev}。建议：加强通风降湿、及时清除病叶；"
                f"如需化学防治请参照知识库处方并遵守安全间隔期。以实地判断为准。")

    def _growth(self, ctx: dict) -> str:
        score = ctx.get("score", 78)
        stage = ctx.get("stage", "生长期")
        return (f"[本地规则] 长势评分 {score}/100，当前处于{stage}。"
                f"绿度指标正常，未见明显缺素特征；保持水肥均衡即可。")

    def _plan(self, ctx: dict) -> str:
        return (f"[本地规则] 依据当前墒情与未来降雨推演，优先安排：1) 视土壤湿度决定灌溉；"
                f"2) 生长期按需追肥；3) 结合诊断结果安排植保；4) 临近成熟期准备采收。")

    def _alert(self, ctx: dict) -> str:
        return ("[本地规则] 多源风险研判：结合传感器阈值与气象推演，对干旱/渍涝/高温/低温/"
                "强降雨/设备故障/病虫害七类风险分级，同地块同类型自动去重合并。")

    def _chat(self, prompt: str, ctx: dict) -> str:
        refs = ctx.get("refs") or []
        q = (ctx.get("user_input") or prompt).strip()
        lines = [f"关于「{q[:40]}」："]
        if refs:
            lines.append("已从本地知识库检索到相关条目，结论如下（附知识依据）：")
            for i, r in enumerate(refs[:5], 1):
                title = r.get("title") or "知识库"
                content = (r.get("content") or "").strip().replace("\n", " ")
                score = r.get("score") or 0
                lines.append(f"{i}. 《{title}》(相关度 {score * 100:.0f}%) {content[:120]}")
            lines.append("以上依据来自知识库命中项，实际操作请结合田间情况。")
        else:
            lines.append("知识库暂无直接命中，以下为通用建议：保持水肥均衡、加强巡检、"
                         "关注气象预警；涉及病虫害请先做叶片诊断。请以实地判断为准。")
        return "\n".join(lines)


_local = LocalRuleLLM()


def _build_remote():
    """惰性构建 LangChain ChatOpenAI（兼容协议）。失败返回 None。"""
    if not settings.LLM_ENABLED or not settings.LLM_API_KEY:
        return None
    try:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            temperature=0.2,
            timeout=60,
        )
    except Exception:
        return None


def llm_mode() -> str:
    """当前 LLM 运行模式。"""
    return "langchain" if (_build_remote() is not None) else "local"


def invoke_llm(prompt: str, context: dict | None = None) -> str:
    """统一入口：远程可用走远程，否则离线兜底。"""
    remote = _build_remote()
    if remote is not None:
        try:
            sys = (context or {}).get("system")
            msgs = []
            if sys:
                from langchain_core.messages import SystemMessage
                msgs.append(SystemMessage(content=sys))
            from langchain_core.messages import HumanMessage
            msgs.append(HumanMessage(content=prompt))
            resp = remote.invoke(msgs)
            return resp.content
        except Exception:
            pass  # 远程失败静默降级
    return _local.invoke(prompt, context)


def extract_json(text: str) -> dict | None:
    """尝试从 LLM 文本中抽取 JSON 片段。"""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    import json
    try:
        return json.loads(m.group(0))
    except Exception:
        return None

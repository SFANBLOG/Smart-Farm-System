"""编排引擎：按任务类型动态路由。
- langgraph 模式：StateGraph 条件路由 + 人工介入节点（需 langgraph 已安装）。
- offline 模式：等价串并行状态机，复用同一批节点函数。
路由表可通过 /agent/engine 实时查看。"""
from __future__ import annotations
from app.config import settings
from app.agent import nodes
from app.agent.state import FarmState

# 任务类型 → 节点序列（[human] 表示人工介入点）
ROUTES: dict[str, list[str]] = {
    "diagnose": ["n_perceive", "n_diagnosis", "human", "n_plan", "n_control"],
    "growth":   ["n_perceive", "n_growth", "n_plan"],
    "plan":     ["n_perceive", "n_plan", "n_control"],
    "control":  ["n_perceive", "n_control"],
    "alert":    ["n_perceive", "n_alert"],
    "chat":     ["n_perceive", "n_chat"],
    "full":     ["n_perceive", "n_diagnosis", "human", "n_growth", "n_plan", "n_control", "n_alert"],
}

NODE_FUNCS = {
    "n_perceive": nodes.n_perceive,
    "n_diagnosis": nodes.n_diagnosis,
    "n_growth": nodes.n_growth,
    "n_plan": nodes.n_plan,
    "n_control": nodes.n_control,
    "n_alert": nodes.n_alert,
    "n_chat": nodes.n_chat,
}


def routing_table() -> dict:
    return {"engine": active_engine(), "routes": ROUTES, "llm": _llm_status()}


def _llm_status() -> str:
    from app.agent.llm import llm_mode
    return llm_mode()


def active_engine() -> str:
    if settings.ENGINE_MODE == "langgraph":
        try:
            import langgraph  # noqa
            return "langgraph"
        except Exception:
            return "offline(langgraph 未安装，自动降级)"
    return "offline"


def _merge(state: dict, patch: dict) -> dict:
    """按 FarmState reducer 语义合并 patch 到 state。"""
    for k, v in (patch or {}).items():
        if k in ("perception", "diagnosis", "growth", "plan", "control", "alert", "answer"):
            state[k] = {**(state.get(k) or {}), **(v or {})}
        elif k in ("media_paths", "trace"):
            state[k] = list(state.get(k) or []) + list(v or [])
        else:
            state[k] = v
    return state


async def run_offline(state: dict, stop_at_human: bool = True) -> dict:
    """离线等价状态机：按路由顺序执行节点；遇 human 节点且未确认则挂起。"""
    task_type = state.get("task_type", "chat")
    seq = ROUTES.get(task_type, ROUTES["chat"])
    for node_name in seq:
        if node_name == "human":
            if state.get("need_confirm") and stop_at_human and not state.get("resume_decision"):
                state["paused_at"] = "human"
                state["status"] = "waiting_confirm"
                return state
            continue
        fn = NODE_FUNCS[node_name]
        patch = await fn(state)
        state = _merge(state, patch)
    state["status"] = "done"
    return state


# ---------- LangGraph 模式 ----------
def build_graph():
    """构建 StateGraph（条件路由）。仅在 langgraph 可用时调用。"""
    from langgraph.graph import StateGraph, END

    g = StateGraph(FarmState)
    for name, fn in NODE_FUNCS.items():
        g.add_node(name, fn)

    g.set_entry_point("n_perceive")

    def after_perceive(state: dict) -> str:
        tt = state.get("task_type", "chat")
        return {"diagnose": "n_diagnosis", "full": "n_diagnosis", "growth": "n_growth",
                "plan": "n_plan", "control": "n_control", "alert": "n_alert",
                "chat": "n_chat"}.get(tt, "n_chat")

    g.add_conditional_edges("n_perceive", after_perceive,
                            list(NODE_FUNCS.keys()))

    def after_diagnosis(state: dict) -> str:
        # Human-in-the-loop：重度需挂起（由 interrupt/checkpoint 处理，这里路由到 plan 或 END）
        if state.get("need_confirm") and not state.get("resume_decision"):
            return END
        return "n_growth" if state.get("task_type") == "full" else "n_plan"

    g.add_conditional_edges("n_diagnosis", after_diagnosis, ["n_growth", "n_plan", END])
    g.add_edge("n_growth", "n_plan")
    g.add_edge("n_plan", "n_control")

    def after_control(state: dict) -> str:
        return "n_alert" if state.get("task_type") == "full" else END

    g.add_conditional_edges("n_control", after_control, ["n_alert", END])
    g.add_edge("n_alert", END)
    g.add_edge("n_chat", END)
    return g.compile()


_graph = None


async def run_graph(state: dict) -> dict:
    global _graph
    if _graph is None:
        _graph = build_graph()
    result = await _graph.ainvoke(state)
    result["status"] = "waiting_confirm" if result.get("need_confirm") else "done"
    return result


async def run(state: dict) -> dict:
    """统一入口：按引擎模式选择执行方式。"""
    if active_engine() == "langgraph":
        try:
            return await run_graph(state)
        except Exception:
            pass  # 降级
    return await run_offline(state)

"""七个 Agent 节点函数。节点函数在 LangGraph 与离线状态机两种模式下完全一致。
每个节点：读 FarmState → 调用工具/LLM → 写回 FarmState 子键，并记 AgentLog。"""
from __future__ import annotations
import time
from datetime import datetime

from app.agent import tools
from app.agent.llm import invoke_llm, llm_mode
from app.rag import retriever
from app.models import AgentLog


async def _log(request_id: str, node: str, phase: str, payload: dict, cost: int = 0, status: str = "ok"):
    try:
        await AgentLog.create(request_id=request_id, node=node, phase=phase,
                              payload=payload, cost_ms=cost, status=status)
    except Exception:
        pass


# 1. 感知 Agent
async def n_perceive(state: dict) -> dict:
    t0 = time.time()
    rid = state.get("request_id")
    perception = await tools.tool_perceive(state.get("field_id"))
    out = {"perception": perception, "trace": [{"node": "perceive", "ok": perception.get("ok")}]}
    await _log(rid, "n_perceive", "end", {"ok": perception.get("ok")}, int((time.time() - t0) * 1000))
    return out


# 2. 病虫害诊断 Agent
async def n_diagnosis(state: dict) -> dict:
    t0 = time.time()
    rid = state.get("request_id")
    perception = state.get("perception", {})
    # 视觉分析（若有图片）
    pix = {}
    for p in state.get("media_paths", [])[:1]:
        pix = await tools.tool_vision(p)
    crop = (perception.get("crop") or {}).get("name", "作物")
    stage = (perception.get("crop") or {}).get("stage", "生长期")
    disease = _guess_disease(pix, perception, state.get("user_input", ""))
    severity = _guess_severity(pix, state.get("user_input", ""))
    # RAG 检索植保知识
    query = f"{crop} {disease} {stage} 防治 药剂 安全间隔期"
    refs = await retriever.retrieve(query)
    ctx = retriever.format_refs(refs)
    prompt = f"作物：{crop}，生育期：{stage}，疑似病害：{disease}，严重度：{severity}。\n像素分析：{pix}\n知识库：\n{ctx}\n请给出诊断结论与处方（药剂/用量/安全间隔期/休药期）。"
    text = invoke_llm(prompt, {"kind": "diagnosis", "disease": disease, "severity": severity,
                               "system": "你是资深植保专家，结论必须关联知识库命中项，未命中时明确提示以实地判断为准。"})
    prescription = _prescription(disease, severity, refs)
    need_confirm = severity == "重度"
    out = {"diagnosis": {"disease": disease, "severity": severity,
                         "confidence": round(0.6 + (pix.get("health_score", 80) / 100) * 0.3, 2),
                         "health_score": pix.get("health_score"),
                         "pixel": pix, "refs": refs, "text": text, **prescription,
                         "need_confirm": need_confirm, "llm_mode": llm_mode()},
           "need_confirm": need_confirm,
           "trace": [{"node": "diagnosis", "disease": disease, "severity": severity}]}
    await _log(rid, "n_diagnosis", "end", {"disease": disease, "severity": severity},
               int((time.time() - t0) * 1000))
    return out


def _guess_disease(pix: dict, perception: dict, user_input: str = "") -> str:
    t = user_input or ""
    if pix.get("brown_ratio", 0) > 0.12 or any(k in t for k in ["褐斑", "斑点", "黑斑", "枯斑"]):
        return "叶斑病（真菌性）"
    if pix.get("yellow_ratio", 0) > 0.15 or any(k in t for k in ["黄化", "发黄", "黄叶", "缺素"]):
        return "黄化/缺素或病毒病"
    if any(k in t for k in ["虫", "蚜", "螟", "蛾"]):
        return "虫害"
    if any(k in t for k in ["霉", "白粉", "锈"]):
        return "白粉/锈病"
    anomalies = perception.get("anomalies", [])
    if any(a["metric"] == "humidity" and a["value"] > 90 for a in anomalies):
        return "高湿诱发病害风险"
    return "未见明显病害"


def _guess_severity(pix: dict, user_input: str = "") -> str:
    t = user_input or ""
    if any(k in t for k in ["严重", "大面积", "枯死", "蔓延"]):
        return "重度"
    hs = pix.get("health_score")
    if hs is None:
        return "中度" if any(k in t for k in ["褐斑", "黄化", "虫", "病"]) else "轻度"
    if hs < 45:
        return "重度"
    if hs < 70:
        return "中度"
    return "轻度"


def _prescription(disease: str, severity: str, refs: list[dict]) -> dict:
    table = {
        "叶斑病（真菌性）": {"pesticide": "苯醚甲环唑", "dosage": "10%水分散粒剂 1500倍液",
                          "safety_interval": "7天", "withdrawal_period": "14天"},
        "黄化/缺素或病毒病": {"pesticide": "氨基酸叶面肥+防蚜", "dosage": "叶面喷施 800倍液",
                       "safety_interval": "3天", "withdrawal_period": "-"},
        "高湿诱发病害风险": {"pesticide": "预防为主(通风降湿)", "dosage": "-",
                      "safety_interval": "-", "withdrawal_period": "-"},
    }
    base = table.get(disease, {"pesticide": "以实地诊断为准", "dosage": "-",
                               "safety_interval": "-", "withdrawal_period": "-"})
    if severity == "重度":
        base = {**base, "note": "重度需人工确认后执行，建议复配并缩短间隔"}
    return base


# 3. 作物生长诊断 Agent
async def n_growth(state: dict) -> dict:
    t0 = time.time()
    rid = state.get("request_id")
    perception = state.get("perception", {})
    metrics = perception.get("metrics", {})
    crop = perception.get("crop") or {}
    score = _growth_score(metrics, crop)
    stage = crop.get("stage", "生长期")
    days = _days_to_harvest(stage)
    prompt = (f"作物 {crop.get('name')} 处于 {stage}，长势评分 {score}/100，"
              f"环境指标 {metrics}。请评估长势、缺素情况与产量预估。")
    text = invoke_llm(prompt, {"kind": "growth", "score": score, "stage": stage,
                               "system": "你是作物栽培专家。"})
    out = {"growth": {"score": score, "stage": stage, "green_index": _green_index(metrics),
                      "nutrient_issue": _nutrient_issue(metrics),
                      "days_to_harvest": days,
                      "estimated_yield": round((crop.get("target_yield") or 500) * score / 100, 1),
                      "analysis": text, "llm_mode": llm_mode()},
           "trace": [{"node": "growth", "score": score}]}
    await _log(rid, "n_growth", "end", {"score": score}, int((time.time() - t0) * 1000))
    return out


def _growth_score(metrics: dict, crop: dict) -> int:
    base = 75
    sm = metrics.get("soil_moisture", {}).get("avg")
    if sm is not None:
        base += 10 if 40 <= sm <= 75 else -10
    t = metrics.get("temp", {}).get("avg")
    if t is not None:
        base += 5 if 18 <= t <= 30 else -8
    return max(20, min(99, base))


def _green_index(metrics: dict) -> float:
    return round(0.6 + min(metrics.get("light", {}).get("avg", 5000), 20000) / 50000, 3)


def _nutrient_issue(metrics: dict) -> str | None:
    ph = metrics.get("ph", {}).get("avg")
    if ph is not None and (ph < 5.5 or ph > 7.8):
        return "pH 偏离，可能影响养分吸收"
    ec = metrics.get("ec", {}).get("avg")
    if ec is not None and ec < 0.8:
        return "EC 偏低，疑似缺肥"
    return None


def _days_to_harvest(stage: str) -> int:
    table = {"苗期": 75, "分蘖期": 60, "拔节期": 45, "抽穗期": 30, "灌浆期": 18,
             "成熟期": 5, "生长期": 40}
    return table.get(stage, 40)


# 4. 农事规划 Agent
async def n_plan(state: dict) -> dict:
    t0 = time.time()
    rid = state.get("request_id")
    perception = state.get("perception", {})
    growth = state.get("growth", {})
    diagnosis = state.get("diagnosis", {})
    tasks = _build_tasks(perception, growth, diagnosis)
    prompt = f"农场现状 {perception}，长势 {growth}，诊断 {diagnosis}。请给出灌溉/施肥/打药/除草/采收排期与多目标优化建议。"
    text = invoke_llm(prompt, {"kind": "plan", "system": "你是农事规划专家，兼顾节水/降本/增产。"})
    out = {"plan": {"tasks": tasks, "reasoning": text, "llm_mode": llm_mode()},
           "trace": [{"node": "plan", "task_count": len(tasks)}]}
    await _log(rid, "n_plan", "end", {"task_count": len(tasks)}, int((time.time() - t0) * 1000))
    return out


def _build_tasks(perception: dict, growth: dict, diagnosis: dict) -> list[dict]:
    tasks = []
    metrics = perception.get("metrics", {})
    rain = perception.get("rain_24h", 0)
    sm = metrics.get("soil_moisture", {}).get("avg")
    now = datetime.now()
    if (sm is not None and sm < 40) and rain < 5:
        tasks.append({"type": "irrigate", "title": "补水灌溉", "objective": "节水",
                      "priority": "high", "when": (now + timedelta_h(2)).isoformat()})
    if growth.get("nutrient_issue"):
        tasks.append({"type": "fertilize", "title": "追肥调理", "objective": "增产",
                      "priority": "normal", "when": (now + timedelta_h(6)).isoformat()})
    if diagnosis.get("severity") in ("中度", "重度"):
        tasks.append({"type": "spray", "title": f"植保施药（{diagnosis.get('disease')}）",
                      "objective": "降本", "priority": "high",
                      "when": (now + timedelta_h(4)).isoformat()})
    if growth.get("days_to_harvest", 99) <= 7:
        tasks.append({"type": "harvest", "title": "准备采收", "objective": "增产",
                      "priority": "high", "when": (now + timedelta_h(24)).isoformat()})
    if not tasks:
        tasks.append({"type": "monitor", "title": "常规巡检监测", "objective": "降本",
                      "priority": "low", "when": (now + timedelta_h(12)).isoformat()})
    return tasks


def timedelta_h(h: int):
    from datetime import timedelta
    return timedelta(hours=h)


# 5. 设备调度 Agent
async def n_control(state: dict) -> dict:
    t0 = time.time()
    rid = state.get("request_id")
    plan = state.get("plan", {})
    results = []
    for task in plan.get("tasks", []):
        if task["type"] not in ("irrigate", "spray", "ventilate"):
            continue
        r = await tools.tool_control(rid, task["type"], None, {"reason": task["title"]})
        results.append(r)
    out = {"control": {"commands": results, "llm_mode": llm_mode()},
           "trace": [{"node": "control", "commands": len(results)}]}
    await _log(rid, "n_control", "end", {"commands": len(results)}, int((time.time() - t0) * 1000))
    return out


# 6. 预警研判 Agent
async def n_alert(state: dict) -> dict:
    t0 = time.time()
    rid = state.get("request_id")
    perception = state.get("perception", {})
    risks = _evaluate_risks(perception)
    created = []
    for r in risks:
        res = await tools.tool_alert(rid, (perception.get("field") or {}).get("id"),
                                     r["type"], r["level"], r["title"], r["detail"])
        created.append({**r, **res})
    prompt = f"多源风险 {risks}，农场现状 {perception}。请做风险推理与分级说明。"
    text = invoke_llm(prompt, {"kind": "alert", "system": "你是农业风险研判专家。"})
    need_confirm = any(r["level"] == "紧急" for r in risks)
    out = {"alert": {"risks": created, "analysis": text, "llm_mode": llm_mode()},
           "need_confirm": state.get("need_confirm", False) or need_confirm,
           "trace": [{"node": "alert", "risk_count": len(created)}]}
    await _log(rid, "n_alert", "end", {"risk_count": len(created)}, int((time.time() - t0) * 1000))
    return out


def _evaluate_risks(perception: dict) -> list[dict]:
    risks = []
    metrics = perception.get("metrics", {})
    weather_fc = perception.get("weather", [])
    sm = metrics.get("soil_moisture", {}).get("avg")
    tmax = max([w.get("temp_max", 0) or 0 for w in weather_fc] or [0])
    tmin = min([w.get("temp_min", 99) or 99 for w in weather_fc] or [99])
    rain = max([w.get("rain", 0) or 0 for w in weather_fc] or [0])
    if sm is not None and sm < 25:
        risks.append({"type": "drought", "level": "重要", "title": "土壤干旱预警",
                      "detail": f"土壤湿度 {sm}% 偏低，存在干旱风险"})
    if sm is not None and sm > 88:
        risks.append({"type": "waterlog", "level": "一般", "title": "渍涝风险",
                      "detail": f"土壤湿度 {sm}% 过高，注意排水"})
    if tmax >= 35:
        risks.append({"type": "heat", "level": "紧急" if tmax >= 38 else "重要",
                      "title": "高温热害预警", "detail": f"预计最高温 {tmax}℃"})
    if tmin <= 2:
        risks.append({"type": "frost", "level": "紧急" if tmin <= 0 else "重要",
                      "title": "低温冻害预警", "detail": f"预计最低温 {tmin}℃"})
    if rain >= 30:
        risks.append({"type": "rain", "level": "重要", "title": "强降雨预警",
                      "detail": f"预计降雨 {rain}mm，注意防涝"})
    diag = perception.get("diagnosis_hint")
    if diag:
        risks.append({"type": "pest", "level": "重要", "title": "病虫害爆发风险", "detail": diag})
    return risks


# 7. 问答交互 Agent
async def n_chat(state: dict) -> dict:
    t0 = time.time()
    rid = state.get("request_id")
    user_input = state.get("user_input", "")
    perception = state.get("perception", {})
    refs = await retriever.retrieve(user_input)
    ctx = retriever.format_refs(refs)
    sys = ("你是智慧农场助手，回答需结合农场现状与知识库命中项，"
           "结论附知识依据；未命中时明确提示以实地判断为准，不得编造农艺建议。")
    prompt = f"农场现状：{perception}\n知识库：\n{ctx}\n用户问题：{user_input}"
    text = invoke_llm(prompt, {"kind": "chat", "refs": refs, "user_input": user_input, "system": sys})
    out = {"answer": {"text": text, "refs": refs, "intent": _route_intent(user_input),
                      "llm_mode": llm_mode()},
           "trace": [{"node": "chat", "refs": len(refs)}]}
    await _log(rid, "n_chat", "end", {"refs": len(refs)}, int((time.time() - t0) * 1000))
    return out


def _route_intent(text: str) -> str:
    t = text or ""
    if any(k in t for k in ["病", "虫", "叶", "斑"]):
        return "diagnose"
    if any(k in t for k in ["长", "产量", "成熟", "缺素"]):
        return "growth"
    if any(k in t for k in ["浇", "灌", "施肥", "打药", "采收", "计划", "排期"]):
        return "plan"
    if any(k in t for k in ["预警", "风险", "干旱", "高温", "冻"]):
        return "alert"
    return "chat"

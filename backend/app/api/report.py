"""AI 运营分析报告：聚合农场数据，调用 LLM（或离线兜底）生成 Markdown 报告。"""
from fastapi import APIRouter
from app.common.result import Result
from app.models import Field, Alert, Diagnosis, GrowthDiagnosis, FarmTask, Device
from app.agent.llm import invoke_llm, llm_mode

router = APIRouter(prefix="/report", tags=["AI报表"])


@router.get("/operations", response_model=Result, summary="报表-生成AI运营分析")
async def operations_report():
    fields = await Field.all()
    alerts = await Alert.filter(status="open").limit(50)
    diagnoses = await Diagnosis.all().order_by("-id").limit(20)
    growths = await GrowthDiagnosis.all().order_by("-id").limit(20)
    tasks = await FarmTask.filter(status="pending").limit(30)
    devices = await Device.all()

    summary = {
        "地块数": len(fields),
        "总面积(亩)": round(sum(f.area or 0 for f in fields), 1),
        "未关闭预警": len(alerts),
        "紧急预警": sum(1 for a in alerts if a.level == "紧急"),
        "近期诊断数": len(diagnoses),
        "平均长势评分": round(sum(g.score for g in growths) / len(growths), 1) if growths else None,
        "待办农事": len(tasks),
        "设备在线率": f"{sum(1 for d in devices if d.online)}/{len(devices)}",
        "主要病害": list({d.disease for d in diagnoses if d.disease})[:5],
        "预警类型分布": {t: sum(1 for a in alerts if a.type == t)
                      for t in {a.type for a in alerts}},
    }

    prompt = (f"以下是智慧农场运营数据汇总：\n{summary}\n"
              f"请生成一份结构化运营分析报告（Markdown），包含：总体概况、风险研判、"
              f"长势评估、农事建议、设备与预警处置建议。")
    text = invoke_llm(prompt, {"kind": "report",
                               "system": "你是农业运营分析师，输出专业、可执行的 Markdown 报告。"})

    markdown = _to_markdown(summary, text)
    return Result.ok({"summary": summary, "markdown": markdown, "llm_mode": llm_mode()})


def _to_markdown(summary: dict, ai_text: str) -> str:
    lines = ["# 智慧农场 AI 运营分析报告", "", "## 一、数据概览", ""]
    for k, v in summary.items():
        lines.append(f"- **{k}**：{v}")
    lines += ["", "## 二、AI 分析", "", ai_text, ""]
    return "\n".join(lines)

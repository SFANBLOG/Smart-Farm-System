"""视觉双通道之本地像素内核：Pillow 计算绿度/黄化/褐斑占比。
视觉大模型可用时由 agent 层调用远程；这里始终提供确定性的本地兜底。"""
from __future__ import annotations
import os
from app.config import settings

try:
    from PIL import Image
    HAS_PIL = True
except Exception:
    HAS_PIL = False


def analyze_pixels(path: str) -> dict:
    """返回 {green_ratio, yellow_ratio, brown_ratio, health_score, hint}。"""
    if not HAS_PIL or not os.path.exists(path):
        return _heuristic(path)
    try:
        img = Image.open(path).convert("RGB").resize((128, 128))
    except Exception:
        return _heuristic(path)
    px = list(img.getdata())
    green = yellow = brown = 0
    for r, g, b in px:
        if g > r and g > b and g > 60:
            green += 1
        elif r > 120 and g > 100 and b < 80:
            yellow += 1
        elif r > 90 and g < 80 and b < 70 and abs(r - g) < 60:
            brown += 1
    n = len(px) or 1
    gr, yr, br = green / n, yellow / n, brown / n
    health = max(0.0, min(1.0, gr * 1.2 - yr * 0.8 - br * 1.0))
    hint = "叶片整体偏绿，长势良好"
    if yr > 0.15:
        hint = "黄化占比偏高，疑似缺素或早期病害"
    if br > 0.12:
        hint = "褐斑占比偏高，疑似真菌性病害"
    return {
        "green_ratio": round(gr, 4), "yellow_ratio": round(yr, 4),
        "brown_ratio": round(br, 4), "health_score": round(health * 100, 1),
        "hint": hint, "channel": "local-pixel",
    }


def _heuristic(path: str) -> dict:
    """无 Pillow / 文件缺失时的启发式兜底（文件名哈希 → 稳定伪结果）。"""
    import hashlib
    h = int(hashlib.md5((path or "x").encode()).hexdigest()[:8], 16)
    gr = 0.45 + (h % 30) / 100.0
    yr = 0.05 + ((h >> 4) % 15) / 100.0
    br = 0.02 + ((h >> 8) % 12) / 100.0
    health = max(0.0, min(1.0, gr * 1.2 - yr * 0.8 - br * 1.0))
    return {"green_ratio": round(gr, 4), "yellow_ratio": round(yr, 4),
            "brown_ratio": round(br, 4), "health_score": round(health * 100, 1),
            "hint": "启发式解析（未启用真实像素计算）", "channel": "heuristic"}


def analyze_remote_or_local(path: str) -> dict:
    """视觉理解统一入口：远程视觉大模型可用则调用，否则本地像素内核。"""
    if settings.LLM_ENABLED and settings.LLM_API_KEY and HAS_PIL and os.path.exists(path):
        try:
            return _vision_llm(path)
        except Exception:
            pass
    return analyze_pixels(path)


def _vision_llm(path: str) -> dict:
    """调用 OpenAI 兼容视觉接口（base64 图片）。失败由上层降级。"""
    import base64
    import httpx
    from app.agent.llm import extract_json
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    payload = {
        "model": settings.LLM_MODEL,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": "分析这张作物叶片/航拍图，输出 JSON：{disease, severity(轻度/中度/重度), health_score(0-100), green_ratio, yellow_ratio, brown_ratio, hint}"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}],
        "temperature": 0.1,
    }
    r = httpx.post(f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions",
                   json=payload, headers={"Authorization": f"Bearer {settings.LLM_API_KEY}"},
                   timeout=60)
    data = r.json()
    text = data["choices"][0]["message"]["content"]
    parsed = extract_json(text) or {}
    parsed["channel"] = "vision-llm"
    parsed.setdefault("health_score", 80)
    return parsed

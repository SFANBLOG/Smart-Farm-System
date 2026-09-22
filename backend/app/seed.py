"""首次启动播种演示数据：地块/作物/传感器/设备/知识库/大模型配置。"""
from __future__ import annotations
import random
from datetime import datetime, timedelta

from app.models import (User, Field, Crop, Sensor, SensorData, Device, KnowledgeDoc,
                        KnowledgeChunk, LLMConfig)
from app.rag.vectorstore import hash_embedding, tokenize, chunk_text
from app.common.security import hash_password

SEEDED_FLAG = "_seeded"


async def ensure_seed():
    if await User.exists():
        return
    await _seed_user()
    await _seed_llm_config()
    fields = await _seed_fields()
    await _seed_devices(fields)
    sensors = await _seed_sensors(fields)
    await _seed_sensor_data(sensors)
    await _seed_knowledge()


async def backfill_knowledge():
    """公开入口：每次启动安全调用，按标题幂等补齐演示知识库。"""
    return await _backfill_knowledge()


async def _seed_user():
    await User.create(username="admin", password_hash=hash_password("admin123"),
                      real_name="农场管理员", role="admin")


async def _seed_llm_config():
    await LLMConfig.create(name="本地规则内核(离线)", provider="local", model="local-rule-engine",
                           is_active=True)
    await LLMConfig.create(name="OpenAI 兼容", provider="openai",
                           base_url="https://api.openai.com/v1", model="gpt-4o-mini",
                           embedding_model="text-embedding-3-small", is_active=False)
    await LLMConfig.create(name="通义千问", provider="dashscope",
                           base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                           model="qwen-plus", is_active=False)


async def _seed_fields() -> list[Field]:
    data = [
        ("F001", "东区水稻田", 120.0, "壤土", 28.21, 112.99),
        ("F002", "西区蔬菜大棚", 45.0, "沙壤土", 28.19, 112.95),
        ("F003", "南区果园", 80.0, "黏壤土", 28.16, 113.02),
    ]
    out = []
    for code, name, area, soil, lat, lon in data:
        out.append(await Field.create(code=code, name=name, area=area, soil_type=soil,
                                      lat=lat, lon=lon, status="normal"))
    stages = ["分蘖期", "苗期", "灌浆期"]
    crops = [("水稻", "黄华占"), ("番茄", "粉果"), ("柑橘", "沃柑")]
    for i, f in enumerate(out):
        await Crop.create(field=f, name=crops[i][0], variety=crops[i][1], stage=stages[i],
                          planted_at=datetime.now() - timedelta(days=60),
                          expected_harvest_at=datetime.now() + timedelta(days=40),
                          target_yield=600 + i * 50)
    return out


async def _seed_devices(fields: list[Field]):
    specs = [("P001", "1号水泵", "pump"), ("V001", "东区电磁阀", "valve"),
             ("S001", "打药机", "sprayer"), ("F001", "大棚风机", "fan")]
    for i, (code, name, typ) in enumerate(specs):
        await Device.create(code=code, name=name, type=typ,
                            field=fields[i % len(fields)], online=True, status="idle")


async def _seed_sensors(fields: list[Field]) -> list[Sensor]:
    metrics = [("soil_moisture", "土壤湿度", "%"), ("temp", "气温", "℃"),
               ("humidity", "空气湿度", "%"), ("light", "光照", "lux"), ("ph", "土壤pH", "")]
    sensors = []
    idx = 0
    for f in fields:
        for m, name, unit in metrics:
            idx += 1
            sensors.append(await Sensor.create(code=f"SN{idx:03d}", name=f"{f.name}-{name}",
                                               metric=m, unit=unit, field=f, online=True))
    return sensors


async def _seed_sensor_data(sensors: list[Sensor]):
    rnd = random.Random(42)
    ranges = {"soil_moisture": (35, 70), "temp": (18, 32), "humidity": (50, 85),
              "light": (8000, 60000), "ph": (6.0, 7.5)}
    for s in sensors:
        lo, hi = ranges.get(s.metric, (20, 80))
        for k in range(20):
            v = round(rnd.uniform(lo, hi), 2)
            await SensorData.create(sensor=s, value=v)


async def _seed_knowledge():
    await _backfill_knowledge()


async def _backfill_knowledge():
    """重置并重建演示知识库：仅删除 source=seed 的旧文档及其分块（用户自导入的保留），
    再按最新内容重建。幂等，可安全地在每次启动调用。"""
    old_docs = await KnowledgeDoc.filter(source="seed")
    if old_docs:
        old_ids = [d.id for d in old_docs]
        await KnowledgeChunk.filter(doc_id__in=old_ids).delete()
        await KnowledgeDoc.filter(id__in=old_ids).delete()
    from app.kb_seed_data import KNOWLEDGE_DOCS as docs
    existing = {d.title for d in await KnowledgeDoc.all()}
    added = 0
    for title, content in docs:
        if title in existing:
            continue
        chunks = chunk_text(content)
        doc = await KnowledgeDoc.create(title=title, source="seed", kind="txt",
                                        size=len(content), chunk_count=len(chunks))
        for i, c in enumerate(chunks):
            indexed = f"{title}。{c}"  # 标题入索引，提升"大棚/稻瘟病"等题面词召回
            await KnowledgeChunk.create(doc=doc, idx=i, content=c,
                                        embedding=hash_embedding(indexed), tokens=tokenize(indexed))
        added += 1
    return added


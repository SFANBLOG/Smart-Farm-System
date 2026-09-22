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
    docs = [
        ("水稻常见病害防治手册",
         "水稻主要病害有稻瘟病、纹枯病、白叶枯病三种。稻瘟病分叶瘟和穗颈瘟，发病初期叶片出现褐色纺锤形病斑，"
         "可用三环唑或苯醚甲环唑喷雾防治，安全间隔期7天，休药期14天。纹枯病多发于高温高湿、密植通风不良的田块，"
         "应加强通风降湿、合理施肥、及时清除病株，发病初期用井冈霉素喷雾。白叶枯病属细菌性病害，"
         "发现中心病株后立即用噻唑锌或氯溴异氰尿酸喷淋，禁止串灌漫灌以防蔓延。"),
        ("水稻生育期水肥管理",
         "水稻分蘖期以促为主，保持浅水层3-5厘米并追施分蘖肥，每亩尿素5-8公斤，提高有效分蘖数。"
         "拔节孕穗期是需水需肥临界期，应保证土壤湿度充足，重施穗肥，追施复合肥10-15公斤加钾肥5公斤。"
         "灌浆期干湿交替灌溉，保持土壤湿度60%-80%，忌过早断穗导致秕谷增加。"
         "晒田标准是田间裂缝达1厘米、踩后不留脚印，控制无效分蘖、增强根系活力。"),
        ("番茄栽培与缺素诊断",
         "番茄缺氮表现为老叶均匀黄化、植株矮小；缺钾表现为老叶叶缘焦枯呈烧灼状；"
         "缺钙易得脐腐病，果实脐部出现黑褐色凹陷斑；缺镁表现为叶脉间黄化而叶脉仍绿。"
         "苗期应控水蹲苗促进根系下扎，结果期保持土壤湿度60%-75%，避免忽干忽湿引发裂果。"
         "黄化严重时喷施氨基酸叶面肥800倍液或0.3%磷酸二氢钾，安全间隔期3天。"
         "脐腐病初期补施硝酸钙1000倍液，每7天一次连喷两次。"),
        ("番茄常见病害与生理障碍",
         "番茄晚疫病是高湿低温型病害，叶片水渍状暗绿病斑、果实油渍状褐斑，发现后立即用霜脲氰锰锌或氟吡菌胺喷雾，"
         "并降低棚内湿度。青枯病属细菌性萎蔫，中午萎蔫早晚恢复数日后枯死，须拔除病株并用中生菌素灌根。"
         "病毒病由蚜虫、粉虱传播，表现为花叶蕨叶，应防治传毒媒介并及时拔除病株。"
         "畸形果多因花期温度过低或点花浓度不当，需调控棚温并用适宜浓度防落素点花。"),
        ("柑橘水分与高温管理",
         "柑橘灌浆期与果实膨大期需水量大，土壤湿度低于40%应及时灌溉，采用滴灌或沟灌小水勤浇。"
         "夏季最高温超过35℃需防日灼，可覆盖遮阳网或树盘覆草降温保墒。"
         "灌溉前应检查未来24小时降雨预报，避免与强降雨叠加造成渍涝伤根。"
         "连续阴雨天气要及时清沟排水，防止根系缺氧烂根引发黄化落果。"),
        ("柑橘黄龙病与木虱防控",
         "柑橘黄龙病是毁灭性检疫病害，由韧皮部杆菌引起，通过柑桔木虱传播，表现为斑驳型黄化叶、均匀黄化、"
         "红鼻子果和青果。一旦确诊立即砍除病株并连根挖除，杜绝传染源。"
         "防控关键是选用无病苗木、防治木虱、清除病株三板斧。木虱防治在春梢萌发期喷施噻虫嗪或高效氯氟氰菊酯，"
         "新梢期是防木虱关键窗口，做到统一放梢、集中喷药。"),
        ("黄瓜霜霉病与白粉病防治",
         "黄瓜霜霉病由鞭毛菌引起，高温高湿易流行，叶片正面出现黄色多角形病斑、背面生灰黑色霉层。"
         "防治以控湿为核心，加强通风，避免叶面结露，发病初期用烯酰吗啉或霜脲氰锰锌喷雾，隔7天连喷两三次。"
         "白粉病叶片出现白色粉状霉层，可用腈菌唑或醚菌酯防治，注意轮换用药延缓抗药性。"
         "保护地栽培优先采用百菌清烟剂熏棚，减少喷雾增湿。"),
        ("农药安全使用规范",
         "所有化学防治须严格遵守安全间隔期与休药期，确保农产品农药残留达标。"
         "施药前检查风力风向，风力大于6米每秒禁止喷雾以防药液飘移污染邻田。"
         "施药人员须穿戴防护服、口罩和手套，避免皮肤接触和吸入药液，施药后及时清洗。"
         "剩余药液和包装物不得随意倾倒于水源和田间，应集中回收无害化处理。"
         "不同作用机理的农药应轮换使用，延缓病虫抗药性产生，严禁超剂量超范围用药。"),
        ("智能灌溉决策要点",
         "灌溉决策应综合土壤湿度、未来降雨、水源水位与设备状态四项因素，做到按需精准灌溉。"
         "当土壤湿度已达上限或未来24小时有强降雨时，应暂缓灌溉避免渍涝。"
         "水泵离线、管道故障或水源不足时禁止启动灌溉，避免设备损坏和灌溉失败。"
         "宜在清晨或傍晚蒸发弱时灌溉，减少水分蒸损。滴灌比漫灌节水30%-50%，优先采用。"
         "每次灌溉后应记录水量与土壤湿度变化，用于优化后续灌溉策略。"),
        ("温室大棚通风降湿技术",
         "保护地栽培湿度过高是病害流行的主因，应以通风降湿为核心管理手段。"
         "晴天上午棚温升至25℃以上时逐步揭开顶风口排湿，下午降至20℃前闭棚保温，避免夜间结露。"
         "阴雨天也应短时揭顶膜换气，配合地面覆膜和膜下滴灌减少土壤水分蒸发。"
         "湿度控制目标为白天60%-70%、夜间不高于85%。可加装循环风扇促进空气流动，"
         "并采用无滴膜减少棚顶滴水。浇水后应立即提温排湿，防止高湿诱发灰霉病和霜霉病。"),
        ("常见害虫绿色综合防控",
         "蚜虫、白粉虱、红蜘蛛和菜青虫是主要害虫，应坚持物理防治与生物防治优先的绿色防控策略。"
         "悬挂黄板诱杀蚜虫和粉虱，每亩20-30张；蓝板诱杀蓟马；安装防虫网阻隔迁飞性害虫。"
         "释放丽蚜小蜂防治粉虱，捕食螨防治红蜘蛛，以虫治虫减少用药。"
         "药剂防治优先选用低毒生物农药，如苦参碱防治菜青虫、阿维菌素防治红蜘蛛，"
         "在害虫低龄期施药效果最佳，注意避开花期保护蜜蜂等传粉昆虫。"),
        ("测土配方施肥与土壤改良",
         "施肥前应先测土，掌握氮磷钾含量与有机质水平，按目标产量和需肥规律配方施肥，避免盲目过量。"
         "土壤pH低于5.5偏酸时施用生石灰或钙镁磷肥调节，高于8.0偏碱时施硫磺粉或酸性肥料。"
         "增施有机肥和秸秆还田可提高土壤有机质、改善团粒结构、增强保水保肥能力。"
         "大量元素氮磷钾配合中微量元素硼锌钙镁施用，缺硼导致花而不实，缺锌引起小叶病，"
         "应基施与叶面补肥结合。化肥深施覆土减少挥发损失，提高肥料利用率。"),
    ]
    existing = {d.title for d in await KnowledgeDoc.all()}
    added = 0
    for title, content in docs:
        if title in existing:
            continue
        chunks = chunk_text(content)
        doc = await KnowledgeDoc.create(title=title, source="seed", kind="txt",
                                        size=len(content), chunk_count=len(chunks))
        for i, c in enumerate(chunks):
            await KnowledgeChunk.create(doc=doc, idx=i, content=c,
                                        embedding=hash_embedding(c), tokens=tokenize(c))
        added += 1
    return added


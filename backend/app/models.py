"""智慧农场业务模型：18 张表。Tortoise ORM 全异步。"""
from tortoise.models import Model
from tortoise import fields


class TimestampMixin:
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)


# 1. 用户
class User(TimestampMixin, Model):
    username = fields.CharField(max_length=64, unique=True)
    password_hash = fields.CharField(max_length=255)
    real_name = fields.CharField(max_length=64, null=True)
    role = fields.CharField(max_length=32, default="admin")  # admin / operator / viewer
    avatar = fields.CharField(max_length=255, null=True)
    enabled = fields.BooleanField(default=True)

    class Meta:
        table = "sys_user"


# 2. 大模型配置
class LLMConfig(TimestampMixin, Model):
    name = fields.CharField(max_length=64)
    provider = fields.CharField(max_length=32, default="openai")
    base_url = fields.CharField(max_length=255, null=True)
    api_key = fields.CharField(max_length=255, null=True)
    model = fields.CharField(max_length=64)
    embedding_model = fields.CharField(max_length=64, null=True)
    temperature = fields.FloatField(default=0.2)
    is_active = fields.BooleanField(default=False)

    class Meta:
        table = "llm_config"


# 3. 地块
class Field(TimestampMixin, Model):
    code = fields.CharField(max_length=32, unique=True)
    name = fields.CharField(max_length=64)
    area = fields.FloatField(default=0.0)  # 亩
    soil_type = fields.CharField(max_length=32, null=True)
    lat = fields.FloatField(null=True)
    lon = fields.FloatField(null=True)
    status = fields.CharField(max_length=16, default="normal")

    class Meta:
        table = "farm_field"


# 4. 作物
class Crop(TimestampMixin, Model):
    field = fields.ForeignKeyField("models.Field", related_name="crops", on_delete=fields.CASCADE)
    name = fields.CharField(max_length=64)
    variety = fields.CharField(max_length=64, null=True)
    stage = fields.CharField(max_length=32, default="苗期")  # 生育期
    planted_at = fields.DatetimeField(null=True)
    expected_harvest_at = fields.DatetimeField(null=True)
    target_yield = fields.FloatField(default=0.0)

    class Meta:
        table = "farm_crop"


# 5. 设备
class Device(TimestampMixin, Model):
    code = fields.CharField(max_length=32, unique=True)
    name = fields.CharField(max_length=64)
    type = fields.CharField(max_length=32)  # pump / valve / sprayer / fan / light
    field = fields.ForeignKeyField("models.Field", related_name="devices",
                                   null=True, on_delete=fields.SET_NULL)
    online = fields.BooleanField(default=True)
    status = fields.CharField(max_length=32, default="idle")

    class Meta:
        table = "iot_device"


# 6. 设备指令
class DeviceCommand(TimestampMixin, Model):
    request_id = fields.CharField(max_length=64, index=True)
    device = fields.ForeignKeyField("models.Device", related_name="commands", on_delete=fields.CASCADE)
    action = fields.CharField(max_length=32)  # open / close / set
    params = fields.JSONField(null=True)
    source = fields.CharField(max_length=32, default="agent")  # agent / manual
    passed = fields.BooleanField(default=True)  # 安全校验是否通过
    blocked_reason = fields.CharField(max_length=255, null=True)
    executed = fields.BooleanField(default=False)

    class Meta:
        table = "iot_device_command"


# 7. 传感器
class Sensor(TimestampMixin, Model):
    code = fields.CharField(max_length=32, unique=True)
    name = fields.CharField(max_length=64)
    metric = fields.CharField(max_length=32)  # soil_moisture / temp / humidity / light / ph / ec
    unit = fields.CharField(max_length=16, null=True)
    field = fields.ForeignKeyField("models.Field", related_name="sensors",
                                   null=True, on_delete=fields.SET_NULL)
    online = fields.BooleanField(default=True)

    class Meta:
        table = "iot_sensor"


# 8. 传感器数据
class SensorData(Model):
    sensor = fields.ForeignKeyField("models.Sensor", related_name="datas", on_delete=fields.CASCADE)
    value = fields.FloatField()
    is_anomaly = fields.BooleanField(default=False)
    ts = fields.DatetimeField(auto_now_add=True, index=True)

    class Meta:
        table = "iot_sensor_data"


# 9. 气象
class WeatherRecord(Model):
    field = fields.ForeignKeyField("models.Field", related_name="weathers",
                                   null=True, on_delete=fields.SET_NULL)
    source = fields.CharField(max_length=16, default="open-meteo")  # open-meteo / local
    date = fields.CharField(max_length=16)
    temp_max = fields.FloatField(null=True)
    temp_min = fields.FloatField(null=True)
    rain = fields.FloatField(null=True)
    humidity = fields.FloatField(null=True)
    wind = fields.FloatField(null=True)
    fetched_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "weather_record"


# 10. 病虫害诊断
class Diagnosis(TimestampMixin, Model):
    request_id = fields.CharField(max_length=64, index=True, null=True)
    field = fields.ForeignKeyField("models.Field", related_name="diagnoses",
                                   null=True, on_delete=fields.SET_NULL)
    disease = fields.CharField(max_length=64)
    severity = fields.CharField(max_length=16, default="轻度")  # 轻度/中度/重度
    confidence = fields.FloatField(default=0.0)
    pesticide = fields.CharField(max_length=64, null=True)
    dosage = fields.CharField(max_length=64, null=True)
    safety_interval = fields.CharField(max_length=32, null=True)  # 安全间隔期
    withdrawal_period = fields.CharField(max_length=32, null=True)  # 休药期
    suggestion = fields.TextField(null=True)
    knowledge_refs = fields.JSONField(null=True)
    media = fields.ForeignKeyField("models.Media", related_name="diagnoses",
                                   null=True, on_delete=fields.SET_NULL)
    need_confirm = fields.BooleanField(default=False)  # Human-in-the-loop
    confirmed = fields.BooleanField(default=False)
    status = fields.CharField(max_length=16, default="pending")  # pending/confirmed/rejected/done

    class Meta:
        table = "biz_diagnosis"


# 11. 生长诊断
class GrowthDiagnosis(TimestampMixin, Model):
    request_id = fields.CharField(max_length=64, index=True, null=True)
    field = fields.ForeignKeyField("models.Field", related_name="growths",
                                   null=True, on_delete=fields.SET_NULL)
    crop = fields.ForeignKeyField("models.Crop", related_name="growths",
                                   null=True, on_delete=fields.SET_NULL)
    score = fields.FloatField(default=0.0)  # 长势评分 0-100
    green_index = fields.FloatField(default=0.0)
    nutrient_issue = fields.CharField(max_length=64, null=True)  # 缺素判断
    stage = fields.CharField(max_length=32, null=True)
    days_to_harvest = fields.IntField(null=True)
    estimated_yield = fields.FloatField(null=True)
    analysis = fields.TextField(null=True)

    class Meta:
        table = "biz_growth_diagnosis"


# 12. 农事计划
class FarmTask(TimestampMixin, Model):
    request_id = fields.CharField(max_length=64, index=True, null=True)
    field = fields.ForeignKeyField("models.Field", related_name="tasks",
                                   null=True, on_delete=fields.SET_NULL)
    type = fields.CharField(max_length=32)  # irrigate / fertilize / spray / weed / harvest
    title = fields.CharField(max_length=128)
    detail = fields.TextField(null=True)
    plan_start = fields.DatetimeField(null=True)
    plan_end = fields.DatetimeField(null=True)
    priority = fields.CharField(max_length=16, default="normal")
    status = fields.CharField(max_length=16, default="pending")  # pending/running/done/cancelled
    objective = fields.CharField(max_length=32, null=True)  # 节水/降本/增产

    class Meta:
        table = "biz_farm_task"


# 13. 预警
class Alert(TimestampMixin, Model):
    request_id = fields.CharField(max_length=64, index=True, null=True)
    field = fields.ForeignKeyField("models.Field", related_name="alerts",
                                   null=True, on_delete=fields.SET_NULL)
    type = fields.CharField(max_length=32)  # drought/waterlog/heat/frost/rain/device/pest
    level = fields.CharField(max_length=16, default="一般")  # 一般/重要/紧急
    title = fields.CharField(max_length=128)
    detail = fields.TextField(null=True)
    status = fields.CharField(max_length=16, default="open")  # open/closed
    resolved_at = fields.DatetimeField(null=True)

    class Meta:
        table = "biz_alert"


# 14. 影像
class Media(TimestampMixin, Model):
    kind = fields.CharField(max_length=16, default="image")  # image / video
    path = fields.CharField(max_length=255)
    filename = fields.CharField(max_length=128, null=True)
    field = fields.ForeignKeyField("models.Field", related_name="medias",
                                   null=True, on_delete=fields.SET_NULL)
    meta = fields.JSONField(null=True)  # 抽帧数、像素分析等

    class Meta:
        table = "biz_media"


# 15. 知识文档
class KnowledgeDoc(TimestampMixin, Model):
    title = fields.CharField(max_length=128)
    source = fields.CharField(max_length=255, null=True)
    kind = fields.CharField(max_length=16, default="txt")
    size = fields.IntField(default=0)
    chunk_count = fields.IntField(default=0)

    class Meta:
        table = "kb_doc"


# 16. 知识切片
class KnowledgeChunk(Model):
    doc = fields.ForeignKeyField("models.KnowledgeDoc", related_name="chunks", on_delete=fields.CASCADE)
    idx = fields.IntField(default=0)
    content = fields.TextField()
    embedding = fields.JSONField(null=True)  # 本地哈希向量
    tokens = fields.JSONField(null=True)  # 关键词

    class Meta:
        table = "kb_chunk"


# 17. 会话
class ChatSession(TimestampMixin, Model):
    title = fields.CharField(max_length=128, default="新会话")
    user = fields.ForeignKeyField("models.User", related_name="sessions",
                                  null=True, on_delete=fields.SET_NULL)

    class Meta:
        table = "chat_session"


# 18. 消息
class ChatMessage(Model):
    session = fields.ForeignKeyField("models.ChatSession", related_name="messages", on_delete=fields.CASCADE)
    role = fields.CharField(max_length=16)  # user / assistant
    content = fields.TextField()
    knowledge_refs = fields.JSONField(null=True)
    request_id = fields.CharField(max_length=64, null=True)
    ts = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "chat_message"


# 附：Agent 节点日志（审计用，非业务表）
class AgentLog(Model):
    request_id = fields.CharField(max_length=64, index=True)
    node = fields.CharField(max_length=32)
    phase = fields.CharField(max_length=16)  # start / end
    payload = fields.JSONField(null=True)
    cost_ms = fields.IntField(default=0)
    status = fields.CharField(max_length=16, default="ok")
    ts = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "agent_log"


MODELS = [
    "app.models.User", "app.models.LLMConfig", "app.models.Field", "app.models.Crop",
    "app.models.Device", "app.models.DeviceCommand", "app.models.Sensor", "app.models.SensorData",
    "app.models.WeatherRecord", "app.models.Diagnosis", "app.models.GrowthDiagnosis",
    "app.models.FarmTask", "app.models.Alert", "app.models.Media", "app.models.KnowledgeDoc",
    "app.models.KnowledgeChunk", "app.models.ChatSession", "app.models.ChatMessage",
    "app.models.AgentLog",
]

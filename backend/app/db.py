"""Tortoise ORM 初始化与关闭。"""
from tortoise import Tortoise
from app.config import settings

TORTOISE_ORM = {
    "connections": {"default": settings.DB_URL},
    "apps": {
        "models": {
            "models": ["app.models"],
            "default_connection": "default",
        }
    },
}


async def init_db():
    await Tortoise.init(config=TORTOISE_ORM)
    # 本地演示自动生成表；生产建议用 aerich 迁移
    await Tortoise.generate_schemas(safe=True)


async def close_db():
    await Tortoise.close_connections()

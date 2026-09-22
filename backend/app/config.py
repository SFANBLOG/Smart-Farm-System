"""全局配置：数据库、模型、并发、超时等。全部可用环境变量覆盖。"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "AI Agent 智慧农场系统"
    APP_VERSION: str = "1.0.0"

    # 数据库：默认 MySQL 8；本地无 MySQL 时可设 DB_URL=sqlite://data/farm.db
    DB_URL: str = "mysql://root:123456@127.0.0.1:3306/smart_farm"
    DB_ECHO: bool = False

    # 安全
    SECRET_KEY: str = "smart-farm-secret-key-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # AI 引擎：默认离线兜底（offline）。启用后可切 langgraph
    ENGINE_MODE: str = "offline"  # offline | langgraph

    # 大模型（可在【系统管理→大模型配置】热切换，这里给默认值）
    LLM_ENABLED: bool = False
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # 气象
    WEATHER_API: str = "https://api.open-meteo.com/v1/forecast"
    WEATHER_CACHE_TTL: int = 600  # 10 分钟缓存
    WEATHER_DEFAULT_LAT: float = 28.2
    WEATHER_DEFAULT_LON: float = 112.9

    # 批量研判并发
    SCAN_CONCURRENCY: int = 3

    # RAG
    RAG_CHUNK_SIZE: int = 400
    RAG_CHUNK_OVERLAP: int = 60
    RAG_TOP_K: int = 6

    CORS_ORIGINS: str = "*"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

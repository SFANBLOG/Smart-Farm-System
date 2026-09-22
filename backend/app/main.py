"""FastAPI 入口：自动扫描 api/ 挂载路由 + 统一异常 + 生命周期。"""
import importlib
import pkgutil
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError

from app import api as api_pkg
from app.common.exceptions import (BizError, biz_error_handler, http_error_handler,
                                   validation_error_handler, unhandled_error_handler)
from app.common.result import Result
from app.config import settings
from app.db import init_db, close_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    # 首次启动播种演示数据
    from app.seed import ensure_seed
    await ensure_seed()
    yield
    await close_db()


app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.CORS_ORIGINS == "*" else settings.CORS_ORIGINS.split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(BizError, biz_error_handler)
app.add_exception_handler(StarletteHTTPException, http_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)


def auto_mount():
    """扫描 app/api 下每个模块的 router 并挂载。"""
    for _, name, _ in pkgutil.iter_modules(api_pkg.__path__):
        module = importlib.import_module(f"app.api.{name}")
        router = getattr(module, "router", None)
        if router is not None:
            app.include_router(router)


auto_mount()


@app.get("/", response_model=Result)
async def root():
    return Result.ok({"app": settings.APP_NAME, "version": settings.APP_VERSION,
                      "engine": settings.ENGINE_MODE, "llm_enabled": settings.LLM_ENABLED})


@app.get("/health", response_model=Result)
async def health():
    from app.agent.service import engine_status
    return Result.ok(engine_status())


# 上传文件静态托管
import os
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

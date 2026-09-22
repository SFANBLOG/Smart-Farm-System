"""统一返回体 Result。"""
from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class Result(BaseModel, Generic[T]):
    code: int = 200
    msg: str = "ok"
    data: Optional[T] = None

    @classmethod
    def ok(cls, data: Any = None, msg: str = "ok") -> "Result":
        return cls(code=200, msg=msg, data=data)

    @classmethod
    def fail(cls, msg: str = "error", code: int = 500, data: Any = None) -> "Result":
        return cls(code=code, msg=msg, data=data)


class Page(BaseModel, Generic[T]):
    total: int = 0
    page: int = 1
    size: int = 20
    items: list[T] = []

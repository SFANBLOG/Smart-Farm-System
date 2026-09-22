"""统一异常处理。"""
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


class BizError(Exception):
    """业务异常：主动抛出可被前端读取的错误。"""

    def __init__(self, msg: str, code: int = 400):
        self.msg = msg
        self.code = code
        super().__init__(msg)


async def biz_error_handler(_: Request, exc: BizError):
    return JSONResponse(status_code=200, content={"code": exc.code, "msg": exc.msg, "data": None})


async def http_error_handler(_: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code,
                        content={"code": exc.status_code, "msg": str(exc.detail), "data": None})


async def validation_error_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(status_code=200,
                        content={"code": 422, "msg": "参数校验失败", "data": exc.errors()})


async def unhandled_error_handler(_: Request, exc: Exception):
    return JSONResponse(status_code=500,
                        content={"code": 500, "msg": f"服务器内部错误: {exc}", "data": None})

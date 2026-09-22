"""认证：登录 / 当前用户 / 修改密码。"""
from fastapi import APIRouter
from pydantic import BaseModel

from app.common.result import Result
from app.common.security import verify_password, create_token, hash_password
from app.models import User

router = APIRouter(prefix="/auth", tags=["认证"])


class LoginIn(BaseModel):
    username: str
    password: str


class PwdIn(BaseModel):
    old_password: str
    new_password: str


@router.post("/login", response_model=Result)
async def login(body: LoginIn):
    user = await User.filter(username=body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        return Result.fail("用户名或密码错误", 401)
    if not user.enabled:
        return Result.fail("账号已禁用", 403)
    token = create_token(user.username, user.role)
    return Result.ok({"token": token, "user": {"id": user.id, "username": user.username,
                                              "real_name": user.real_name, "role": user.role}})


@router.get("/me", response_model=Result)
async def me(username: str = ""):
    user = await User.filter(username=username).first()
    if not user:
        return Result.fail("用户不存在", 404)
    return Result.ok({"id": user.id, "username": user.username,
                      "real_name": user.real_name, "role": user.role})


@router.post("/password", response_model=Result)
async def change_password(body: PwdIn, username: str = ""):
    user = await User.filter(username=username).first()
    if not user or not verify_password(body.old_password, user.password_hash):
        return Result.fail("原密码错误", 400)
    user.password_hash = hash_password(body.new_password)
    await user.save()
    return Result.ok(None, "密码已更新")

"""通用 CRUD 路由工厂：一行生成 list/page/get/create/update/delete 六个接口。"""
from __future__ import annotations
from typing import Type
from fastapi import APIRouter, Query
from pydantic import BaseModel
from tortoise.models import Model

from app.common.crud import to_list, to_page, dump_one
from app.common.result import Result


def build_crud_router(model: Type[Model], prefix: str, tag: str,
                      order: str = "-id") -> APIRouter:
    router = APIRouter(prefix=prefix, tags=[tag])

    async def _body():
        pass

    @router.get("", response_model=Result, summary=f"{tag}-列表")
    async def list_items():
        return Result.ok(await to_list(model))

    @router.get("/page", response_model=Result, summary=f"{tag}-分页")
    async def page_items(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=200)):
        return Result.ok(await to_page(model, page, size, order))

    @router.get("/{item_id}", response_model=Result, summary=f"{tag}-详情")
    async def get_item(item_id: int):
        obj = await model.filter(id=item_id).first()
        return Result.ok(dump_one(obj)) if obj else Result.fail("不存在", 404)

    @router.post("", response_model=Result, summary=f"{tag}-新建")
    async def create_item(payload: dict):
        obj = await model.create(**_filter_fields(model, payload))
        return Result.ok(dump_one(obj))

    @router.put("/{item_id}", response_model=Result, summary=f"{tag}-更新")
    async def update_item(item_id: int, payload: dict):
        obj = await model.filter(id=item_id).first()
        if not obj:
            return Result.fail("不存在", 404)
        data = _filter_fields(model, payload, exclude_id=True)
        for k, v in data.items():
            setattr(obj, k, v)
        await obj.save()
        return Result.ok(dump_one(obj))

    @router.delete("/{item_id}", response_model=Result, summary=f"{tag}-删除")
    async def delete_item(item_id: int):
        await model.filter(id=item_id).delete()
        return Result.ok({"id": item_id})

    return router


def _filter_fields(model: Type[Model], payload: dict, exclude_id: bool = False) -> dict:
    """过滤出模型自身的标量字段；外键 xxx_id 保留。"""
    from tortoise.fields.relational import (ForeignKeyFieldInstance, ReverseRelation,
                                            ManyToManyFieldInstance)
    valid = set()
    for name, f in model._meta.fields_map.items():
        if isinstance(f, (ReverseRelation, ManyToManyFieldInstance)):
            continue
        valid.add(name)
        if isinstance(f, ForeignKeyFieldInstance):
            valid.add(f"{name}_id")
    out = {}
    for k, v in (payload or {}).items():
        if exclude_id and k == "id":
            continue
        if k in valid:
            out[k] = v
    return out

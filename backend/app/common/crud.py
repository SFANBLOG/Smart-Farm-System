"""通用 CRUD 收敛：把"建表→出接口→分页查询"收敛成一行调用。"""
from typing import Any, Type
from pydantic import BaseModel, create_model
from tortoise.models import Model
from tortoise import fields
from tortoise.fields.relational import ForeignKeyFieldInstance, RelationalField


def _py_type(f: fields.Field) -> Any:
    if isinstance(f, fields.BooleanField):
        return bool
    if isinstance(f, (fields.IntField, fields.SmallIntField, fields.BigIntField)):
        return int
    if isinstance(f, (fields.FloatField, fields.DecimalField)):
        return float
    if isinstance(f, fields.DatetimeField):
        return str
    return str


def make_schemas(model: Type[Model]) -> tuple[Type[BaseModel], Type[BaseModel]]:
    """根据 ORM 模型自动生成 Create / Read 两个 Pydantic Schema。"""
    create_fields: dict[str, tuple] = {}
    read_fields: dict[str, tuple] = {"id": (int, ...)}
    for name, f in model._meta.fields_map.items():
        if name == "id" or isinstance(f, RelationalField):
            continue
        py = _py_type(f)
        nullable = f.null or not f.required
        default = f.default if f.default is not None else None
        if nullable or default is not None:
            create_fields[name] = (py, default)
            read_fields[name] = (py, default)
        else:
            create_fields[name] = (py, ...)
            read_fields[name] = (py, ...)

    Create = create_model(f"{model.__name__}Create", **create_fields)
    Read = create_model(f"{model.__name__}Read", **read_fields)
    Read.model_config = {"from_attributes": True}
    return Create, Read


def dump_one(obj: Model) -> dict:
    """ORM 实例 → dict：仅标量列 + 外键 xxx_id，自动跳过反向关系。"""
    out: dict[str, Any] = {}
    for name in obj._meta.fields_db_projection.keys():
        v = getattr(obj, name, None)
        if hasattr(v, "isoformat"):
            v = v.isoformat()
        out[name] = v
    for name, f in obj._meta.fields_map.items():
        if isinstance(f, ForeignKeyFieldInstance):
            out[f"{name}_id"] = getattr(obj, f"{name}_id", None)
    return out


def _as_queryset(qs):
    """允许传模型类或 QuerySet。"""
    if isinstance(qs, type) and issubclass(qs, Model):
        return qs.all()
    return qs


async def to_list(queryset, **filters) -> list[dict]:
    qs = _as_queryset(queryset)
    if filters:
        qs = qs.filter(**filters)
    rows = await qs
    return [dump_one(r) for r in rows]


async def to_page(queryset, page: int = 1, size: int = 20, order: str = "-id", **filters) -> dict:
    qs = _as_queryset(queryset)
    if filters:
        qs = qs.filter(**filters)
    total = await qs.count()
    rows = await qs.order_by(order).offset((page - 1) * size).limit(size)
    return {"total": total, "page": page, "size": size, "items": [dump_one(r) for r in rows]}

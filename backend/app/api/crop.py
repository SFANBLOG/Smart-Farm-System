"""作物模块：标准 CRUD。"""
from app.common.crud_router import build_crud_router
from app.models import Crop

router = build_crud_router(Crop, "/crop", "作物")

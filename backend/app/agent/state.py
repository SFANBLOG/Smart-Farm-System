"""FarmState：节点间共享的统一农场状态，带自定义 reducer。"""
from __future__ import annotations
import operator
from typing import Annotated, Any, TypedDict


def merge_dict(left: dict, right: dict) -> dict:
    """字典合并 reducer：后者覆盖前者，保留历史键。"""
    out = dict(left or {})
    out.update(right or {})
    return out


def append_list(left: list, right: list) -> list:
    """列表追加 reducer。"""
    out = list(left or [])
    out.extend(right or [])
    return out


class FarmState(TypedDict, total=False):
    # 输入
    request_id: str
    task_type: str            # diagnose/growth/plan/control/alert/chat/full
    user_input: str
    field_id: int | None
    media_paths: Annotated[list[str], append_list]

    # 感知
    perception: Annotated[dict, merge_dict]   # 标准化"农场现状"

    # 诊断/长势/规划/控制/预警/问答 结果
    diagnosis: Annotated[dict, merge_dict]
    growth: Annotated[dict, merge_dict]
    plan: Annotated[dict, merge_dict]
    control: Annotated[dict, merge_dict]
    alert: Annotated[dict, merge_dict]
    answer: Annotated[dict, merge_dict]

    # Human-in-the-loop
    need_confirm: bool
    resume_decision: str      # approve / reject

    # 审计
    trace: Annotated[list[dict], append_list]

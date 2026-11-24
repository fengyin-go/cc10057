"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class FieldRouteService(BaseModuleService):
    MODULE = "field_route"
    ENTITY = "路线记录"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["路线编号", "区域集合", "门店顺序", "预计时长", "生效标记"]
    REQUIRED_FIELDS = ["路线编号", "区域集合", "门店顺序"]
    STATUS_ORDER = ["草稿", "已生效", "已调整"]
    ACTION_RULES = {"生效路线": "已生效", "调整路线": "已调整"}
    NEGATIVE_ACTIONS = []

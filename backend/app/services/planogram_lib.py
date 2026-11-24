"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class PlanogramLibService(BaseModuleService):
    MODULE = "planogram_lib"
    ENTITY = "陈列标准"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["标准编号", "货架区段", "商品码序列", "排面下限", "生效版本"]
    REQUIRED_FIELDS = ["标准编号", "货架区段", "商品码序列"]
    STATUS_ORDER = ["草稿", "已生效", "已下线"]
    ACTION_RULES = {"生效标准": "已生效", "下线标准": "已下线"}
    NEGATIVE_ACTIONS = ["下线标准"]

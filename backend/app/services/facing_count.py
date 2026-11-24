"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class FacingCountService(BaseModuleService):
    MODULE = "facing_count"
    ENTITY = "计数记录"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["记录编号", "陈列区域", "商品码", "排面数", "计数版本"]
    REQUIRED_FIELDS = ["记录编号", "陈列区域", "商品码"]
    STATUS_ORDER = ["草稿", "已确认", "已修正"]
    ACTION_RULES = {"确认计数": "已确认", "修正计数": "已修正"}
    NEGATIVE_ACTIONS = []

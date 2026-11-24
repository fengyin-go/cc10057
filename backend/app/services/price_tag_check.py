"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class PriceTagCheckService(BaseModuleService):
    MODULE = "price_tag_check"
    ENTITY = "价签记录"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["记录编号", "陈列位置", "标价金额", "系统金额", "核对结论"]
    REQUIRED_FIELDS = ["记录编号", "陈列位置", "标价金额"]
    STATUS_ORDER = ["待核对", "已核对", "差异待处理"]
    ACTION_RULES = {"执行核对": "已核对", "标记差异": "差异待处理"}
    NEGATIVE_ACTIONS = []

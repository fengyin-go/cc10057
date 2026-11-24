"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class GapCheckService(BaseModuleService):
    MODULE = "gap_check"
    ENTITY = "缺货记录"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["记录编号", "陈列区域", "缺货商品码", "空位数量", "发现时间"]
    REQUIRED_FIELDS = ["记录编号", "陈列区域", "缺货商品码"]
    STATUS_ORDER = ["已发现", "已确认", "已补货"]
    ACTION_RULES = {"确认缺货": "已确认", "标记补货": "已补货"}
    NEGATIVE_ACTIONS = []

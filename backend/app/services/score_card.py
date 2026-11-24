"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class ScoreCardService(BaseModuleService):
    MODULE = "score_card"
    ENTITY = "得分记录"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["记录编号", "门店标识", "稽核周期", "得分值", "扣分明细"]
    REQUIRED_FIELDS = ["记录编号", "门店标识", "稽核周期"]
    STATUS_ORDER = ["待生成", "已生成", "已公示"]
    ACTION_RULES = {"生成得分": "已生成", "公示得分": "已公示"}
    NEGATIVE_ACTIONS = []

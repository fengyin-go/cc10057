"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class AuditResultService(BaseModuleService):
    MODULE = "audit_result"
    ENTITY = "稽核结论"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["结论编号", "任务标识", "达标项数", "违例项数", "结论版本"]
    REQUIRED_FIELDS = ["结论编号", "任务标识", "达标项数"]
    STATUS_ORDER = ["待汇总", "已汇总", "已复核"]
    ACTION_RULES = {"执行汇总": "已汇总", "提交复核": "已复核"}
    NEGATIVE_ACTIONS = []

"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class AuditReviewService(BaseModuleService):
    MODULE = "audit_review"
    ENTITY = "复核事项"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["事项编号", "争议记录", "机器结论", "人工结论", "复核状态"]
    REQUIRED_FIELDS = ["事项编号", "争议记录", "机器结论"]
    STATUS_ORDER = ["待复核", "复核中", "已裁定"]
    ACTION_RULES = {"开始复核": "复核中", "提交裁定": "已裁定"}
    NEGATIVE_ACTIONS = []

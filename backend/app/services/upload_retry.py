"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class UploadRetryService(BaseModuleService):
    MODULE = "upload_retry"
    ENTITY = "重试项"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["队列编号", "失败原因", "重试次数", "退避间隔", "下次执行"]
    REQUIRED_FIELDS = ["队列编号", "失败原因", "重试次数"]
    STATUS_ORDER = ["排队中", "重试中", "已放弃"]
    ACTION_RULES = {"执行重试": "重试中", "放弃重试": "已放弃"}
    NEGATIVE_ACTIONS = []

"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class AuditArchiveService(BaseModuleService):
    MODULE = "audit_archive"
    ENTITY = "归档记录"
    OPERATION_TERM = "归档"
    LIST_FIELDS = ["记录编号", "归档范围", "保留期限", "归档位置", "归档指纹"]
    REQUIRED_FIELDS = ["记录编号", "归档范围", "保留期限"]
    STATUS_ORDER = ["待归档", "已归档", "已清理"]
    ACTION_RULES = {"执行归档": "已归档", "清理过期": "已清理"}
    NEGATIVE_ACTIONS = []

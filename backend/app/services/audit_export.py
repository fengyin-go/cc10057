"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class AuditExportService(BaseModuleService):
    MODULE = "audit_export"
    ENTITY = "导出任务"
    OPERATION_TERM = "导出"
    LIST_FIELDS = ["导出编号", "数据范围", "字段清单", "文件指纹", "导出状态"]
    REQUIRED_FIELDS = ["导出编号", "数据范围", "字段清单"]
    STATUS_ORDER = ["排队中", "导出中", "已完成"]
    ACTION_RULES = {"开始导出": "导出中", "标记完成": "已完成"}
    NEGATIVE_ACTIONS = []

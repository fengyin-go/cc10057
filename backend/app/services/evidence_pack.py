"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class EvidencePackService(BaseModuleService):
    MODULE = "evidence_pack"
    ENTITY = "证据包"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["包编号", "任务标识", "图像清单", "结论清单", "打包指纹"]
    REQUIRED_FIELDS = ["包编号", "任务标识", "图像清单"]
    STATUS_ORDER = ["待打包", "已打包", "已分发"]
    ACTION_RULES = {"执行打包": "已打包", "分发证据": "已分发"}
    NEGATIVE_ACTIONS = []

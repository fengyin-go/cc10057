"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class ImageDedupService(BaseModuleService):
    MODULE = "image_dedup"
    ENTITY = "去重记录"
    OPERATION_TERM = "去重"
    LIST_FIELDS = ["记录编号", "图像指纹", "相似簇号", "保留标记", "比对阈值"]
    REQUIRED_FIELDS = ["记录编号", "图像指纹", "相似簇号"]
    STATUS_ORDER = ["待比对", "已去重", "已合并"]
    ACTION_RULES = {"执行比对": "已去重", "合并簇": "已合并"}
    NEGATIVE_ACTIONS = []

"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class ShelfDetectService(BaseModuleService):
    MODULE = "shelf_detect"
    ENTITY = "检测记录"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["记录编号", "图像指纹", "层板数", "检测置信", "框选坐标"]
    REQUIRED_FIELDS = ["记录编号", "图像指纹", "层板数"]
    STATUS_ORDER = ["待检测", "已检测", "复检中"]
    ACTION_RULES = {"执行检测": "已检测", "提交复检": "复检中"}
    NEGATIVE_ACTIONS = []

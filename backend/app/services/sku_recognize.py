"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class SkuRecognizeService(BaseModuleService):
    MODULE = "sku_recognize"
    ENTITY = "识别记录"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["记录编号", "陈列区域", "候选商品码", "识别置信", "复核标记"]
    REQUIRED_FIELDS = ["记录编号", "陈列区域", "候选商品码"]
    STATUS_ORDER = ["待识别", "已识别", "低置信"]
    ACTION_RULES = {"执行识别": "已识别", "转人工": "低置信"}
    NEGATIVE_ACTIONS = []

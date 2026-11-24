"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class StoreListService(BaseModuleService):
    MODULE = "store_list"
    ENTITY = "门店条目"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["门店编号", "门店名称", "所属区域", "巡检频率", "联系人标识"]
    REQUIRED_FIELDS = ["门店编号", "门店名称", "所属区域"]
    STATUS_ORDER = ["待建档", "已建档", "已闭店"]
    ACTION_RULES = {"建档门店": "已建档", "闭店门店": "已闭店"}
    NEGATIVE_ACTIONS = []

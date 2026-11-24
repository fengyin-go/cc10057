"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class ShelfTaskService(BaseModuleService):
    MODULE = "shelf_task"
    ENTITY = "稽核任务"
    OPERATION_TERM = "采集"
    LIST_FIELDS = ["任务编号", "门店标识", "巡检日期", "货架区段", "任务状态"]
    REQUIRED_FIELDS = ["任务编号", "门店标识", "巡检日期"]
    STATUS_ORDER = ["待派单", "已派单", "已采集", "已归档"]
    ACTION_RULES = {"派发任务": "已派单", "确认采集": "已采集", "归档任务": "已归档"}
    NEGATIVE_ACTIONS = []

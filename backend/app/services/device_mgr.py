"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class DeviceMgrService(BaseModuleService):
    MODULE = "device_mgr"
    ENTITY = "采集设备"
    OPERATION_TERM = "采集"
    LIST_FIELDS = ["设备编号", "设备型号", "绑定巡检员", "固件版本", "在线状态"]
    REQUIRED_FIELDS = ["设备编号", "设备型号", "绑定巡检员"]
    STATUS_ORDER = ["待绑定", "在线", "离线"]
    ACTION_RULES = {"绑定设备": "在线", "标记离线": "离线"}
    NEGATIVE_ACTIONS = []

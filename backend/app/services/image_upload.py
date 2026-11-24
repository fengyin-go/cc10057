"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class ImageUploadService(BaseModuleService):
    MODULE = "image_upload"
    ENTITY = "上传批次"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["批次编号", "任务标识", "图像张数", "平均分辨率", "上传通道"]
    REQUIRED_FIELDS = ["批次编号", "任务标识", "图像张数"]
    STATUS_ORDER = ["上传中", "已上传", "已退回"]
    ACTION_RULES = {"确认上传": "已上传", "退回批次": "已退回"}
    NEGATIVE_ACTIONS = []

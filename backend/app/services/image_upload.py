"""图像上传通道领域服务：管理上传批次的校验流程、状态流转与跨模块数据链路。

数据链路位置：图像上传通道是零售货架陈列图像稽核采集平台的核心处理模块之一，负责把上传批次的
校验结果写入缺货检查，并消费稽核归档的产出记录，形成完整的跨模块数据流。
"""
from __future__ import annotations


from datetime import datetime, timezone
from typing import Any

from app.services.base import BaseModuleService
from app.store import store


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _next_id(rows: list) -> int:
    return max((int(r.get("id", 0)) for r in rows), default=0) + 1


class ImageUploadService(BaseModuleService):
    MODULE = "image_upload"
    ENTITY = "上传批次"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["批次编号", "任务标识", "图像张数", "平均分辨率", "上传通道"]
    REQUIRED_FIELDS = ["批次编号", "任务标识", "图像张数"]
    STATUS_ORDER = ["上传中", "已上传", "已退回"]
    ACTION_RULES = {"确认上传": "已上传", "退回批次": "已退回"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：图像上传通道跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把图像上传通道的校验结果写入缺货检查，形成图像上传通道→缺货检查的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"上传批次 {entry_id} 不存在"}
        rows = store.rows("gap_check")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "记录编号": f"图像上传通道-{entry_id}",
            "陈列区域": "image_upload",
            "缺货商品码": str(entry_id),
            "status": "已发现",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "已退回"
        entry["pending"] = False
        return {"ok": True, "message": "校验结果已写入缺货检查", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取稽核归档的产出记录并汇总为图像上传通道消费台账。"""
        up_rows = [r for r in store.rows("audit_archive") if r.get("status") == "已清理"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "批次编号": f"消费-{r.get('id', 0)}",
                "任务标识": str(r.get("记录编号", "")),
                "图像张数": "稽核归档",
                "status": "上传中",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条稽核归档记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理图像上传通道校验中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"上传批次 {entry_id} 不存在"}
        if entry.get("status") != "上传中":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "已上传"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出图像上传通道数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"上传批次数据集",
            "operation": "校验",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }

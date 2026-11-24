"""排面计数领域服务：管理计数记录的校验流程、状态流转与跨模块数据链路。

数据链路位置：排面计数是零售货架陈列图像稽核采集平台的核心处理模块之一，负责把计数记录的
校验结果写入巡检路线规划，并消费图像去重的产出记录，形成完整的跨模块数据流。
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


class FacingCountService(BaseModuleService):
    MODULE = "facing_count"
    ENTITY = "计数记录"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["记录编号", "陈列区域", "商品码", "排面数", "计数版本"]
    REQUIRED_FIELDS = ["记录编号", "陈列区域", "商品码"]
    STATUS_ORDER = ["草稿", "已确认", "已修正"]
    ACTION_RULES = {"确认计数": "已确认", "修正计数": "已修正"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：排面计数跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把排面计数的校验结果写入巡检路线规划，形成排面计数→巡检路线规划的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"计数记录 {entry_id} 不存在"}
        rows = store.rows("field_route")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "路线编号": f"排面计数-{entry_id}",
            "区域集合": "facing_count",
            "门店顺序": str(entry_id),
            "status": "草稿",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "已修正"
        entry["pending"] = False
        return {"ok": True, "message": "校验结果已写入巡检路线规划", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取图像去重的产出记录并汇总为排面计数消费台账。"""
        up_rows = [r for r in store.rows("image_dedup") if r.get("status") == "已合并"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "记录编号": f"消费-{r.get('id', 0)}",
                "陈列区域": str(r.get("记录编号", "")),
                "商品码": "图像去重",
                "status": "草稿",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条图像去重记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理排面计数校验中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"计数记录 {entry_id} 不存在"}
        if entry.get("status") != "草稿":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "已确认"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出排面计数数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"计数记录数据集",
            "operation": "校验",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }

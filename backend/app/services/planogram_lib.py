"""陈列标准库领域服务：管理陈列标准的校验流程、状态流转与跨模块数据链路。

数据链路位置：陈列标准库是零售货架陈列图像稽核采集平台的核心处理模块之一，负责把陈列标准的
校验结果写入采集设备管理，并消费货架检测的产出记录，形成完整的跨模块数据流。
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


class PlanogramLibService(BaseModuleService):
    MODULE = "planogram_lib"
    ENTITY = "陈列标准"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["标准编号", "货架区段", "商品码序列", "排面下限", "生效版本"]
    REQUIRED_FIELDS = ["标准编号", "货架区段", "商品码序列"]
    STATUS_ORDER = ["草稿", "已生效", "已下线"]
    ACTION_RULES = {"生效标准": "已生效", "下线标准": "已下线"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：陈列标准库跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把陈列标准库的校验结果写入采集设备管理，形成陈列标准库→采集设备管理的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"陈列标准 {entry_id} 不存在"}
        rows = store.rows("device_mgr")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "设备编号": f"陈列标准库-{entry_id}",
            "设备型号": "planogram_lib",
            "绑定巡检员": str(entry_id),
            "status": "待绑定",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "已下线"
        entry["pending"] = False
        return {"ok": True, "message": "校验结果已写入采集设备管理", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取货架检测的产出记录并汇总为陈列标准库消费台账。"""
        up_rows = [r for r in store.rows("shelf_detect") if r.get("status") == "复检中"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "标准编号": f"消费-{r.get('id', 0)}",
                "货架区段": str(r.get("记录编号", "")),
                "商品码序列": "货架检测",
                "status": "草稿",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条货架检测记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理陈列标准库校验中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"陈列标准 {entry_id} 不存在"}
        if entry.get("status") != "草稿":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "已生效"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出陈列标准库数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"陈列标准数据集",
            "operation": "校验",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }

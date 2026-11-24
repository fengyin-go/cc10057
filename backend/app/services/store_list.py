"""门店名录领域服务：管理门店条目的校验流程、状态流转与跨模块数据链路。

数据链路位置：门店名录是零售货架陈列图像稽核采集平台的核心处理模块之一，负责把门店条目的
校验结果写入排面计数，并消费稽核导出中心的产出记录，形成完整的跨模块数据流。
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


class StoreListService(BaseModuleService):
    MODULE = "store_list"
    ENTITY = "门店条目"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["门店编号", "门店名称", "所属区域", "巡检频率", "联系人标识"]
    REQUIRED_FIELDS = ["门店编号", "门店名称", "所属区域"]
    STATUS_ORDER = ["待建档", "已建档", "已闭店"]
    ACTION_RULES = {"建档门店": "已建档", "闭店门店": "已闭店"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：门店名录跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把门店名录的校验结果写入排面计数，形成门店名录→排面计数的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"门店条目 {entry_id} 不存在"}
        rows = store.rows("facing_count")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "记录编号": f"门店名录-{entry_id}",
            "陈列区域": "store_list",
            "商品码": str(entry_id),
            "status": "草稿",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "已闭店"
        entry["pending"] = False
        return {"ok": True, "message": "校验结果已写入排面计数", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取稽核导出中心的产出记录并汇总为门店名录消费台账。"""
        up_rows = [r for r in store.rows("audit_export") if r.get("status") == "已完成"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "门店编号": f"消费-{r.get('id', 0)}",
                "门店名称": str(r.get("导出编号", "")),
                "所属区域": "稽核导出中心",
                "status": "待建档",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条稽核导出中心记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理门店名录校验中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"门店条目 {entry_id} 不存在"}
        if entry.get("status") != "待建档":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "已建档"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出门店名录数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"门店条目数据集",
            "operation": "校验",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }

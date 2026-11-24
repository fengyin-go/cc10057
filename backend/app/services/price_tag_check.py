"""价签核对领域服务：管理价签记录的校验流程、状态流转与跨模块数据链路。

数据链路位置：价签核对是零售货架陈列图像稽核采集平台的核心处理模块之一，负责把价签记录的
校验结果写入稽核证据包，并消费排面计数的产出记录，形成完整的跨模块数据流。
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


class PriceTagCheckService(BaseModuleService):
    MODULE = "price_tag_check"
    ENTITY = "价签记录"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["记录编号", "陈列位置", "标价金额", "系统金额", "核对结论"]
    REQUIRED_FIELDS = ["记录编号", "陈列位置", "标价金额"]
    STATUS_ORDER = ["待核对", "已核对", "差异待处理"]
    ACTION_RULES = {"执行核对": "已核对", "标记差异": "差异待处理"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：价签核对跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把价签核对的校验结果写入稽核证据包，形成价签核对→稽核证据包的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"价签记录 {entry_id} 不存在"}
        rows = store.rows("evidence_pack")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "包编号": f"价签核对-{entry_id}",
            "任务标识": "price_tag_check",
            "图像清单": str(entry_id),
            "status": "待打包",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "差异待处理"
        entry["pending"] = False
        return {"ok": True, "message": "校验结果已写入稽核证据包", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取排面计数的产出记录并汇总为价签核对消费台账。"""
        up_rows = [r for r in store.rows("facing_count") if r.get("status") == "已修正"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "记录编号": f"消费-{r.get('id', 0)}",
                "陈列位置": str(r.get("记录编号", "")),
                "标价金额": "排面计数",
                "status": "待核对",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条排面计数记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理价签核对校验中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"价签记录 {entry_id} 不存在"}
        if entry.get("status") != "待核对":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "已核对"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出价签核对数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"价签记录数据集",
            "operation": "校验",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }

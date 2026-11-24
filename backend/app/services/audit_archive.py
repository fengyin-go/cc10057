"""稽核归档领域服务：管理归档记录的归档流程、状态流转与跨模块数据链路。

数据链路位置：稽核归档是零售货架陈列图像稽核采集平台的核心处理模块之一，负责把归档记录的
归档结果写入商品识别，并消费稽核证据包的产出记录，形成完整的跨模块数据流。
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


class AuditArchiveService(BaseModuleService):
    MODULE = "audit_archive"
    ENTITY = "归档记录"
    OPERATION_TERM = "归档"
    LIST_FIELDS = ["记录编号", "归档范围", "保留期限", "归档位置", "归档指纹"]
    REQUIRED_FIELDS = ["记录编号", "归档范围", "保留期限"]
    STATUS_ORDER = ["待归档", "已归档", "已清理"]
    ACTION_RULES = {"执行归档": "已归档", "清理过期": "已清理"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：稽核归档跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把稽核归档的归档结果写入商品识别，形成稽核归档→商品识别的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"归档记录 {entry_id} 不存在"}
        rows = store.rows("sku_recognize")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "记录编号": f"稽核归档-{entry_id}",
            "陈列区域": "audit_archive",
            "候选商品码": str(entry_id),
            "status": "待识别",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "已清理"
        entry["pending"] = False
        return {"ok": True, "message": "归档结果已写入商品识别", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取稽核证据包的产出记录并汇总为稽核归档消费台账。"""
        up_rows = [r for r in store.rows("evidence_pack") if r.get("status") == "已分发"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "记录编号": f"消费-{r.get('id', 0)}",
                "归档范围": str(r.get("包编号", "")),
                "保留期限": "稽核证据包",
                "status": "待归档",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条稽核证据包记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理稽核归档归档中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"归档记录 {entry_id} 不存在"}
        if entry.get("status") != "待归档":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "已归档"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出稽核归档数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"归档记录数据集",
            "operation": "归档",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }

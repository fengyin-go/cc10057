"""稽核结果汇总领域服务：管理稽核结论的校验流程、状态流转与跨模块数据链路。

数据链路位置：稽核结果汇总是零售货架陈列图像稽核采集平台的核心处理模块之一，负责把稽核结论的
校验结果写入稽核导出中心，并消费陈列标准库的产出记录，形成完整的跨模块数据流。
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


class AuditResultService(BaseModuleService):
    MODULE = "audit_result"
    ENTITY = "稽核结论"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["结论编号", "任务标识", "达标项数", "违例项数", "结论版本"]
    REQUIRED_FIELDS = ["结论编号", "任务标识", "达标项数"]
    STATUS_ORDER = ["待汇总", "已汇总", "已复核"]
    ACTION_RULES = {"执行汇总": "已汇总", "提交复核": "已复核"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：稽核结果汇总跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把稽核结果汇总的校验结果写入稽核导出中心，形成稽核结果汇总→稽核导出中心的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"稽核结论 {entry_id} 不存在"}
        rows = store.rows("audit_export")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "导出编号": f"稽核结果汇总-{entry_id}",
            "数据范围": "audit_result",
            "字段清单": str(entry_id),
            "status": "排队中",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "已复核"
        entry["pending"] = False
        return {"ok": True, "message": "校验结果已写入稽核导出中心", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取陈列标准库的产出记录并汇总为稽核结果汇总消费台账。"""
        up_rows = [r for r in store.rows("planogram_lib") if r.get("status") == "已下线"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "结论编号": f"消费-{r.get('id', 0)}",
                "任务标识": str(r.get("标准编号", "")),
                "达标项数": "陈列标准库",
                "status": "待汇总",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条陈列标准库记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理稽核结果汇总校验中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"稽核结论 {entry_id} 不存在"}
        if entry.get("status") != "待汇总":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "已汇总"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出稽核结果汇总数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"稽核结论数据集",
            "operation": "校验",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }

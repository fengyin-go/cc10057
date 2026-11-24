"""人工复核台领域服务：管理复核事项的校验流程、状态流转与跨模块数据链路。

数据链路位置：人工复核台是零售货架陈列图像稽核采集平台的核心处理模块之一，负责把复核事项的
校验结果写入门店得分卡，并消费缺货检查的产出记录，形成完整的跨模块数据流。
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


class AuditReviewService(BaseModuleService):
    MODULE = "audit_review"
    ENTITY = "复核事项"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["事项编号", "争议记录", "机器结论", "人工结论", "复核状态"]
    REQUIRED_FIELDS = ["事项编号", "争议记录", "机器结论"]
    STATUS_ORDER = ["待复核", "复核中", "已裁定"]
    ACTION_RULES = {"开始复核": "复核中", "提交裁定": "已裁定"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：人工复核台跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把人工复核台的校验结果写入门店得分卡，形成人工复核台→门店得分卡的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"复核事项 {entry_id} 不存在"}
        rows = store.rows("score_card")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "记录编号": f"人工复核台-{entry_id}",
            "门店标识": "audit_review",
            "稽核周期": str(entry_id),
            "status": "待生成",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "已裁定"
        entry["pending"] = False
        return {"ok": True, "message": "校验结果已写入门店得分卡", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取缺货检查的产出记录并汇总为人工复核台消费台账。"""
        up_rows = [r for r in store.rows("gap_check") if r.get("status") == "已补货"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "事项编号": f"消费-{r.get('id', 0)}",
                "争议记录": str(r.get("记录编号", "")),
                "机器结论": "缺货检查",
                "status": "待复核",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条缺货检查记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理人工复核台校验中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"复核事项 {entry_id} 不存在"}
        if entry.get("status") != "待复核":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "复核中"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出人工复核台数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"复核事项数据集",
            "operation": "校验",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }

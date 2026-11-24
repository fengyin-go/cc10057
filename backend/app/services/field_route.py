"""巡检路线规划领域服务：管理路线记录的校验流程、状态流转与跨模块数据链路。

数据链路位置：巡检路线规划是零售货架陈列图像稽核采集平台的核心处理模块之一，负责把路线记录的
校验结果写入稽核归档，并消费价签核对的产出记录，形成完整的跨模块数据流。
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


class FieldRouteService(BaseModuleService):
    MODULE = "field_route"
    ENTITY = "路线记录"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["路线编号", "区域集合", "门店顺序", "预计时长", "生效标记"]
    REQUIRED_FIELDS = ["路线编号", "区域集合", "门店顺序"]
    STATUS_ORDER = ["草稿", "已生效", "已调整"]
    ACTION_RULES = {"生效路线": "已生效", "调整路线": "已调整"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：巡检路线规划跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把巡检路线规划的校验结果写入稽核归档，形成巡检路线规划→稽核归档的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"路线记录 {entry_id} 不存在"}
        rows = store.rows("audit_archive")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "记录编号": f"巡检路线规划-{entry_id}",
            "归档范围": "field_route",
            "保留期限": str(entry_id),
            "status": "待归档",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "已调整"
        entry["pending"] = False
        return {"ok": True, "message": "校验结果已写入稽核归档", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取价签核对的产出记录并汇总为巡检路线规划消费台账。"""
        up_rows = [r for r in store.rows("price_tag_check") if r.get("status") == "差异待处理"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "路线编号": f"消费-{r.get('id', 0)}",
                "区域集合": str(r.get("记录编号", "")),
                "门店顺序": "价签核对",
                "status": "草稿",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条价签核对记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理巡检路线规划校验中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"路线记录 {entry_id} 不存在"}
        if entry.get("status") != "草稿":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "已生效"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出巡检路线规划数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"路线记录数据集",
            "operation": "校验",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }

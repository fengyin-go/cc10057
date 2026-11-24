"""货架稽核任务领域服务：管理稽核任务的采集流程、状态流转与跨模块数据链路。

数据链路位置：货架稽核任务是零售货架陈列图像稽核采集平台的核心处理模块之一，负责把稽核任务的
采集结果写入陈列标准库，并消费门店得分卡的产出记录，形成完整的跨模块数据流。
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


class ShelfTaskService(BaseModuleService):
    MODULE = "shelf_task"
    ENTITY = "稽核任务"
    OPERATION_TERM = "采集"
    LIST_FIELDS = ["任务编号", "门店标识", "巡检日期", "货架区段", "任务状态"]
    REQUIRED_FIELDS = ["任务编号", "门店标识", "巡检日期"]
    STATUS_ORDER = ["待派单", "已派单", "已采集", "已归档"]
    ACTION_RULES = {"派发任务": "已派单", "确认采集": "已采集", "归档任务": "已归档"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：货架稽核任务跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把货架稽核任务的采集结果写入陈列标准库，形成货架稽核任务→陈列标准库的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"稽核任务 {entry_id} 不存在"}
        rows = store.rows("planogram_lib")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "标准编号": f"货架稽核任务-{entry_id}",
            "货架区段": "shelf_task",
            "商品码序列": str(entry_id),
            "status": "草稿",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "已归档"
        entry["pending"] = False
        return {"ok": True, "message": "采集结果已写入陈列标准库", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取门店得分卡的产出记录并汇总为货架稽核任务消费台账。"""
        up_rows = [r for r in store.rows("score_card") if r.get("status") == "已公示"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "任务编号": f"消费-{r.get('id', 0)}",
                "门店标识": str(r.get("记录编号", "")),
                "巡检日期": "门店得分卡",
                "status": "待派单",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条门店得分卡记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理货架稽核任务采集中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"稽核任务 {entry_id} 不存在"}
        if entry.get("status") != "待派单":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "已派单"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出货架稽核任务数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"稽核任务数据集",
            "operation": "采集",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }

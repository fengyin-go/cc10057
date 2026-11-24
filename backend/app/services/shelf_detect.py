"""货架检测领域服务：管理检测记录的校验流程、状态流转与跨模块数据链路。

数据链路位置：货架检测是零售货架陈列图像稽核采集平台的核心处理模块之一，负责把检测记录的
校验结果写入稽核结果汇总，并消费货架稽核任务的产出记录，形成完整的跨模块数据流。
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


class ShelfDetectService(BaseModuleService):
    MODULE = "shelf_detect"
    ENTITY = "检测记录"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["记录编号", "图像指纹", "层板数", "检测置信", "框选坐标"]
    REQUIRED_FIELDS = ["记录编号", "图像指纹", "层板数"]
    STATUS_ORDER = ["待检测", "已检测", "复检中"]
    ACTION_RULES = {"执行检测": "已检测", "提交复检": "复检中"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：货架检测跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把货架检测的校验结果写入稽核结果汇总，形成货架检测→稽核结果汇总的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"检测记录 {entry_id} 不存在"}
        rows = store.rows("audit_result")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "结论编号": f"货架检测-{entry_id}",
            "任务标识": "shelf_detect",
            "达标项数": str(entry_id),
            "status": "待汇总",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "复检中"
        entry["pending"] = False
        return {"ok": True, "message": "校验结果已写入稽核结果汇总", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取货架稽核任务的产出记录并汇总为货架检测消费台账。"""
        up_rows = [r for r in store.rows("shelf_task") if r.get("status") == "已归档"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "记录编号": f"消费-{r.get('id', 0)}",
                "图像指纹": str(r.get("任务编号", "")),
                "层板数": "货架稽核任务",
                "status": "待检测",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条货架稽核任务记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理货架检测校验中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"检测记录 {entry_id} 不存在"}
        if entry.get("status") != "待检测":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "已检测"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出货架检测数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"检测记录数据集",
            "operation": "校验",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }

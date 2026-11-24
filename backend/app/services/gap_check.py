"""缺货检查领域服务：管理缺货记录的校验流程、状态流转与跨模块数据链路。

数据链路位置：缺货检查是零售货架陈列图像稽核采集平台的核心处理模块之一，负责把缺货记录的
校验结果写入上传重试队列，并消费商品识别的产出记录，形成完整的跨模块数据流。
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


class GapCheckService(BaseModuleService):
    MODULE = "gap_check"
    ENTITY = "缺货记录"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["记录编号", "陈列区域", "缺货商品码", "空位数量", "发现时间"]
    REQUIRED_FIELDS = ["记录编号", "陈列区域", "缺货商品码"]
    STATUS_ORDER = ["已发现", "已确认", "已补货"]
    ACTION_RULES = {"确认缺货": "已确认", "标记补货": "已补货"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：缺货检查跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把缺货检查的校验结果写入上传重试队列，形成缺货检查→上传重试队列的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"缺货记录 {entry_id} 不存在"}
        rows = store.rows("upload_retry")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "队列编号": f"缺货检查-{entry_id}",
            "失败原因": "gap_check",
            "重试次数": str(entry_id),
            "status": "排队中",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "已补货"
        entry["pending"] = False
        return {"ok": True, "message": "校验结果已写入上传重试队列", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取商品识别的产出记录并汇总为缺货检查消费台账。"""
        up_rows = [r for r in store.rows("sku_recognize") if r.get("status") == "低置信"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "记录编号": f"消费-{r.get('id', 0)}",
                "陈列区域": str(r.get("记录编号", "")),
                "缺货商品码": "商品识别",
                "status": "已发现",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条商品识别记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理缺货检查校验中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"缺货记录 {entry_id} 不存在"}
        if entry.get("status") != "已发现":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "已确认"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出缺货检查数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"缺货记录数据集",
            "operation": "校验",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }

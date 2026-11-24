"""图像去重领域服务：管理去重记录的去重流程、状态流转与跨模块数据链路。

数据链路位置：图像去重是零售货架陈列图像稽核采集平台的核心处理模块之一，负责把去重记录的
去重结果写入价签核对，并消费门店名录的产出记录，形成完整的跨模块数据流。
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


class ImageDedupService(BaseModuleService):
    MODULE = "image_dedup"
    ENTITY = "去重记录"
    OPERATION_TERM = "去重"
    LIST_FIELDS = ["记录编号", "图像指纹", "相似簇号", "保留标记", "比对阈值"]
    REQUIRED_FIELDS = ["记录编号", "图像指纹", "相似簇号"]
    STATUS_ORDER = ["待比对", "已去重", "已合并"]
    ACTION_RULES = {"执行比对": "已去重", "合并簇": "已合并"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：图像去重跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把图像去重的去重结果写入价签核对，形成图像去重→价签核对的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"去重记录 {entry_id} 不存在"}
        rows = store.rows("price_tag_check")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "记录编号": f"图像去重-{entry_id}",
            "陈列位置": "image_dedup",
            "标价金额": str(entry_id),
            "status": "待核对",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "已合并"
        entry["pending"] = False
        return {"ok": True, "message": "去重结果已写入价签核对", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取门店名录的产出记录并汇总为图像去重消费台账。"""
        up_rows = [r for r in store.rows("store_list") if r.get("status") == "已闭店"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "记录编号": f"消费-{r.get('id', 0)}",
                "图像指纹": str(r.get("门店编号", "")),
                "相似簇号": "门店名录",
                "status": "待比对",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条门店名录记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理图像去重去重中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"去重记录 {entry_id} 不存在"}
        if entry.get("status") != "待比对":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "已去重"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出图像去重数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"去重记录数据集",
            "operation": "去重",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }

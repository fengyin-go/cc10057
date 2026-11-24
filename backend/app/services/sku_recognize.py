"""商品识别领域服务：管理识别记录的校验流程、状态流转与跨模块数据链路。

数据链路位置：商品识别是零售货架陈列图像稽核采集平台的核心处理模块之一，负责把识别记录的
校验结果写入人工复核台，并消费图像上传通道的产出记录，形成完整的跨模块数据流。
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


class SkuRecognizeService(BaseModuleService):
    MODULE = "sku_recognize"
    ENTITY = "识别记录"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["记录编号", "陈列区域", "候选商品码", "识别置信", "复核标记"]
    REQUIRED_FIELDS = ["记录编号", "陈列区域", "候选商品码"]
    STATUS_ORDER = ["待识别", "已识别", "低置信"]
    ACTION_RULES = {"执行识别": "已识别", "转人工": "低置信"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：商品识别跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把商品识别的校验结果写入人工复核台，形成商品识别→人工复核台的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"识别记录 {entry_id} 不存在"}
        rows = store.rows("audit_review")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "事项编号": f"商品识别-{entry_id}",
            "争议记录": "sku_recognize",
            "机器结论": str(entry_id),
            "status": "待复核",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "低置信"
        entry["pending"] = False
        return {"ok": True, "message": "校验结果已写入人工复核台", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取图像上传通道的产出记录并汇总为商品识别消费台账。"""
        up_rows = [r for r in store.rows("image_upload") if r.get("status") == "已退回"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "记录编号": f"消费-{r.get('id', 0)}",
                "陈列区域": str(r.get("批次编号", "")),
                "候选商品码": "图像上传通道",
                "status": "待识别",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条图像上传通道记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理商品识别校验中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"识别记录 {entry_id} 不存在"}
        if entry.get("status") != "待识别":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "已识别"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出商品识别数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"识别记录数据集",
            "operation": "校验",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }

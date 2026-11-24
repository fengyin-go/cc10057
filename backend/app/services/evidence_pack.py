"""稽核证据包领域服务：管理证据包的校验流程、状态流转与跨模块数据链路。

数据链路位置：稽核证据包是零售货架陈列图像稽核采集平台的核心处理模块之一，负责把证据包的
校验结果写入图像上传通道，并消费巡检路线规划的产出记录，形成完整的跨模块数据流。
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


class EvidencePackService(BaseModuleService):
    MODULE = "evidence_pack"
    ENTITY = "证据包"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["包编号", "任务标识", "图像清单", "结论清单", "打包指纹"]
    REQUIRED_FIELDS = ["包编号", "任务标识", "图像清单"]
    STATUS_ORDER = ["待打包", "已打包", "已分发"]
    ACTION_RULES = {"执行打包": "已打包", "分发证据": "已分发"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：稽核证据包跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把稽核证据包的校验结果写入图像上传通道，形成稽核证据包→图像上传通道的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"证据包 {entry_id} 不存在"}
        rows = store.rows("image_upload")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "批次编号": f"稽核证据包-{entry_id}",
            "任务标识": "evidence_pack",
            "图像张数": str(entry_id),
            "status": "上传中",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "已分发"
        entry["pending"] = False
        return {"ok": True, "message": "校验结果已写入图像上传通道", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取巡检路线规划的产出记录并汇总为稽核证据包消费台账。"""
        up_rows = [r for r in store.rows("field_route") if r.get("status") == "已调整"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "包编号": f"消费-{r.get('id', 0)}",
                "任务标识": str(r.get("路线编号", "")),
                "图像清单": "巡检路线规划",
                "status": "待打包",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条巡检路线规划记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理稽核证据包校验中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"证据包 {entry_id} 不存在"}
        if entry.get("status") != "待打包":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "已打包"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出稽核证据包数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"证据包数据集",
            "operation": "校验",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }

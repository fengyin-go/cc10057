"""上传重试队列领域服务：管理重试项的校验流程、状态流转与跨模块数据链路。

数据链路位置：上传重试队列是零售货架陈列图像稽核采集平台的核心处理模块之一，负责把重试项的
校验结果写入货架稽核任务，并消费人工复核台的产出记录，形成完整的跨模块数据流。
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


class UploadRetryService(BaseModuleService):
    MODULE = "upload_retry"
    ENTITY = "重试项"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["队列编号", "失败原因", "重试次数", "退避间隔", "下次执行"]
    REQUIRED_FIELDS = ["队列编号", "失败原因", "重试次数"]
    STATUS_ORDER = ["排队中", "重试中", "已放弃"]
    ACTION_RULES = {"执行重试": "重试中", "放弃重试": "已放弃"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：上传重试队列跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把上传重试队列的校验结果写入货架稽核任务，形成上传重试队列→货架稽核任务的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"重试项 {entry_id} 不存在"}
        rows = store.rows("shelf_task")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "任务编号": f"上传重试队列-{entry_id}",
            "门店标识": "upload_retry",
            "巡检日期": str(entry_id),
            "status": "待派单",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "已放弃"
        entry["pending"] = False
        return {"ok": True, "message": "校验结果已写入货架稽核任务", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取人工复核台的产出记录并汇总为上传重试队列消费台账。"""
        up_rows = [r for r in store.rows("audit_review") if r.get("status") == "已裁定"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "队列编号": f"消费-{r.get('id', 0)}",
                "失败原因": str(r.get("事项编号", "")),
                "重试次数": "人工复核台",
                "status": "排队中",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条人工复核台记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理上传重试队列校验中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"重试项 {entry_id} 不存在"}
        if entry.get("status") != "排队中":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "重试中"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出上传重试队列数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"重试项数据集",
            "operation": "校验",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }

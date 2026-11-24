"""门店得分卡领域服务：管理得分记录的校验流程、状态流转与跨模块数据链路。

数据链路位置：门店得分卡是零售货架陈列图像稽核采集平台的核心处理模块之一，负责把得分记录的
校验结果写入货架检测，并消费上传重试队列的产出记录，形成完整的跨模块数据流。
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


class ScoreCardService(BaseModuleService):
    MODULE = "score_card"
    ENTITY = "得分记录"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["记录编号", "门店标识", "稽核周期", "得分值", "扣分明细"]
    REQUIRED_FIELDS = ["记录编号", "门店标识", "稽核周期"]
    STATUS_ORDER = ["待生成", "已生成", "已公示"]
    ACTION_RULES = {"生成得分": "已生成", "公示得分": "已公示"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：门店得分卡跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把门店得分卡的校验结果写入货架检测，形成门店得分卡→货架检测的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"得分记录 {entry_id} 不存在"}
        rows = store.rows("shelf_detect")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "记录编号": f"门店得分卡-{entry_id}",
            "图像指纹": "score_card",
            "层板数": str(entry_id),
            "status": "待检测",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "已公示"
        entry["pending"] = False
        return {"ok": True, "message": "校验结果已写入货架检测", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取上传重试队列的产出记录并汇总为门店得分卡消费台账。"""
        up_rows = [r for r in store.rows("upload_retry") if r.get("status") == "已放弃"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "记录编号": f"消费-{r.get('id', 0)}",
                "门店标识": str(r.get("队列编号", "")),
                "稽核周期": "上传重试队列",
                "status": "待生成",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条上传重试队列记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理门店得分卡校验中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"得分记录 {entry_id} 不存在"}
        if entry.get("status") != "待生成":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "已生成"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出门店得分卡数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"得分记录数据集",
            "operation": "校验",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }

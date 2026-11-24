"""采集设备管理领域服务：管理采集设备的采集流程、状态流转与跨模块数据链路。

数据链路位置：采集设备管理是零售货架陈列图像稽核采集平台的核心处理模块之一，负责把采集设备的
采集结果写入门店名录，并消费稽核结果汇总的产出记录，形成完整的跨模块数据流。
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


class DeviceMgrService(BaseModuleService):
    MODULE = "device_mgr"
    ENTITY = "采集设备"
    OPERATION_TERM = "采集"
    LIST_FIELDS = ["设备编号", "设备型号", "绑定巡检员", "固件版本", "在线状态"]
    REQUIRED_FIELDS = ["设备编号", "设备型号", "绑定巡检员"]
    STATUS_ORDER = ["待绑定", "在线", "离线"]
    ACTION_RULES = {"绑定设备": "在线", "标记离线": "离线"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：采集设备管理跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把采集设备管理的采集结果写入门店名录，形成采集设备管理→门店名录的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"采集设备 {entry_id} 不存在"}
        rows = store.rows("store_list")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "门店编号": f"采集设备管理-{entry_id}",
            "门店名称": "device_mgr",
            "所属区域": str(entry_id),
            "status": "待建档",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "离线"
        entry["pending"] = False
        return {"ok": True, "message": "采集结果已写入门店名录", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取稽核结果汇总的产出记录并汇总为采集设备管理消费台账。"""
        up_rows = [r for r in store.rows("audit_result") if r.get("status") == "已复核"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "设备编号": f"消费-{r.get('id', 0)}",
                "设备型号": str(r.get("结论编号", "")),
                "绑定巡检员": "稽核结果汇总",
                "status": "待绑定",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条稽核结果汇总记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理采集设备管理采集中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"采集设备 {entry_id} 不存在"}
        if entry.get("status") != "待绑定":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "在线"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出采集设备管理数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"采集设备数据集",
            "operation": "采集",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }

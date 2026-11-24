"""领域服务注册表：通用资源路由按模块 key 分派到独立业务服务。"""
from __future__ import annotations

from app.services.base import BaseModuleService
from app.services.store_list import StoreListService
from app.services.shelf_task import ShelfTaskService
from app.services.image_upload import ImageUploadService
from app.services.image_dedup import ImageDedupService
from app.services.shelf_detect import ShelfDetectService
from app.services.sku_recognize import SkuRecognizeService
from app.services.facing_count import FacingCountService
from app.services.planogram_lib import PlanogramLibService
from app.services.gap_check import GapCheckService
from app.services.price_tag_check import PriceTagCheckService
from app.services.audit_result import AuditResultService
from app.services.audit_review import AuditReviewService
from app.services.field_route import FieldRouteService
from app.services.device_mgr import DeviceMgrService
from app.services.upload_retry import UploadRetryService
from app.services.evidence_pack import EvidencePackService
from app.services.audit_export import AuditExportService
from app.services.score_card import ScoreCardService
from app.services.audit_archive import AuditArchiveService

SERVICES: dict[str, BaseModuleService] = {
    "store_list": StoreListService(),
    "shelf_task": ShelfTaskService(),
    "image_upload": ImageUploadService(),
    "image_dedup": ImageDedupService(),
    "shelf_detect": ShelfDetectService(),
    "sku_recognize": SkuRecognizeService(),
    "facing_count": FacingCountService(),
    "planogram_lib": PlanogramLibService(),
    "gap_check": GapCheckService(),
    "price_tag_check": PriceTagCheckService(),
    "audit_result": AuditResultService(),
    "audit_review": AuditReviewService(),
    "field_route": FieldRouteService(),
    "device_mgr": DeviceMgrService(),
    "upload_retry": UploadRetryService(),
    "evidence_pack": EvidencePackService(),
    "audit_export": AuditExportService(),
    "score_card": ScoreCardService(),
    "audit_archive": AuditArchiveService(),
}


def service_for(module: str) -> BaseModuleService | None:
    return SERVICES.get(module)

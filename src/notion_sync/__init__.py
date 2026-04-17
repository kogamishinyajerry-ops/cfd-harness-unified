"""Public surface for Phase 8 Notion synchronization."""

from .client_binding import OfficialNotionAdapter, resolve_official_notion_client
from .schemas import (
    CANONICAL_DOC_STATUS,
    CANONICAL_DOC_TYPE,
    PHASE_ACTIVE_STATUS,
    SUPPORTED_CASE_IDS,
    SUGGEST_ONLY_BANNER,
    CanonicalDocCreate,
    CaseSyncRecord,
    PageUpdate,
    SyncPlan,
    SyncTargets,
)
from .syncer import NotionSync

__all__ = [
    "CANONICAL_DOC_STATUS",
    "CANONICAL_DOC_TYPE",
    "PHASE_ACTIVE_STATUS",
    "SUPPORTED_CASE_IDS",
    "SUGGEST_ONLY_BANNER",
    "CanonicalDocCreate",
    "CaseSyncRecord",
    "NotionSync",
    "OfficialNotionAdapter",
    "PageUpdate",
    "SyncPlan",
    "SyncTargets",
    "resolve_official_notion_client",
]

"""Structured contracts for deterministic Notion sync payloads."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, Tuple

SUPPORTED_CASE_IDS = (
    "lid_driven_cavity_benchmark",
    "backward_facing_step_steady",
    "cylinder_crossflow",
)
SUGGEST_ONLY_BANNER = "suggest-only, not auto-applied"
PHASE_ACTIVE_STATUS = "Active"
CANONICAL_DOC_TYPE = "Reference"
CANONICAL_DOC_STATUS = "Active"


@dataclass(frozen=True)
class SyncTargets:
    phase_page_id: str
    auto_verifier_task_page_id: str
    report_engine_task_page_id: str
    canonical_docs_data_source_id: str


@dataclass(frozen=True)
class CaseSyncRecord:
    case_id: str
    verdict: str
    comparison_overall: str
    report_repo_path: str
    auto_verify_repo_path: str
    correction_policy: str
    summary: str


@dataclass(frozen=True)
class PageUpdate:
    page_id: str
    properties: Dict[str, Any]


@dataclass(frozen=True)
class CanonicalDocCreate:
    parent_data_source_id: str
    properties: Dict[str, Any]


@dataclass(frozen=True)
class SyncPlan:
    task_updates: Tuple[PageUpdate, ...]
    phase_update: PageUpdate
    canonical_doc_creates: Tuple[CanonicalDocCreate, ...]

    def stable_repr(self) -> str:
        """Return a byte-stable JSON representation for replay tests."""
        return json.dumps(asdict(self), ensure_ascii=True, sort_keys=True)

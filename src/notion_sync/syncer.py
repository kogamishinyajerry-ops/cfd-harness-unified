"""Deterministic Phase 8 Notion sync plan generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml  # type: ignore[import-untyped]

from .client_binding import NotionAdapter
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

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORTS_ROOT = REPO_ROOT / "reports"


class NotionSync:
    """Build and optionally apply Notion updates from Phase 8 artifacts."""

    def __init__(
        self,
        adapter: Optional[NotionAdapter] = None,
        reports_root: Path = REPORTS_ROOT,
    ) -> None:
        self._adapter = adapter
        self._reports_root = reports_root

    def build_phase8_plan(self, targets: SyncTargets) -> SyncPlan:
        records = tuple(self._collect_case_record(case_id) for case_id in SUPPORTED_CASE_IDS)
        return SyncPlan(
            task_updates=(
                self._build_auto_verifier_update(targets.auto_verifier_task_page_id, records),
                self._build_report_engine_update(targets.report_engine_task_page_id, records),
            ),
            phase_update=self._build_phase_update(targets.phase_page_id),
            canonical_doc_creates=tuple(
                self._build_canonical_doc_create(
                    case_record=record,
                    phase_page_id=targets.phase_page_id,
                    report_engine_task_page_id=targets.report_engine_task_page_id,
                    canonical_docs_data_source_id=targets.canonical_docs_data_source_id,
                )
                for record in records
            ),
        )

    def apply_phase8_plan(self, targets: SyncTargets) -> SyncPlan:
        plan = self.build_phase8_plan(targets)
        if self._adapter is None:
            raise RuntimeError("Notion adapter is required to apply sync plan")
        for update in plan.task_updates:
            self._adapter.update_page(update.page_id, update.properties)
        self._adapter.update_page(plan.phase_update.page_id, plan.phase_update.properties)
        for create_request in plan.canonical_doc_creates:
            self._adapter.create_page(
                create_request.parent_data_source_id,
                create_request.properties,
            )
        return plan

    def _collect_case_record(self, case_id: str) -> CaseSyncRecord:
        report_path = self._reports_root / case_id / "report.md"
        auto_verify_path = self._reports_root / case_id / "auto_verify_report.yaml"
        if not report_path.exists():
            raise ValueError(f"Missing report.md for {case_id}: {report_path}")
        if not auto_verify_path.exists():
            raise ValueError(f"Missing auto_verify_report.yaml for {case_id}: {auto_verify_path}")

        report_markdown = report_path.read_text(encoding="utf-8")
        if SUGGEST_ONLY_BANNER not in report_markdown:
            raise ValueError(f"Missing suggest-only banner in {report_path}")

        auto_verify_report = yaml.safe_load(auto_verify_path.read_text(encoding="utf-8"))
        verdict = auto_verify_report.get("verdict", "UNKNOWN")
        overall = auto_verify_report.get("gold_standard_comparison", {}).get("overall", "UNKNOWN")
        summary = (
            f"Verdict={verdict}; Comparison={overall}; "
            f"CorrectionSpec={SUGGEST_ONLY_BANNER}; "
            f"RepoPath=reports/{case_id}/report.md"
        )
        return CaseSyncRecord(
            case_id=case_id,
            verdict=verdict,
            comparison_overall=overall,
            report_repo_path=f"reports/{case_id}/report.md",
            auto_verify_repo_path=f"reports/{case_id}/auto_verify_report.yaml",
            correction_policy=SUGGEST_ONLY_BANNER,
            summary=summary,
        )

    @staticmethod
    def _build_auto_verifier_update(
        page_id: str,
        records: Tuple[CaseSyncRecord, ...],
    ) -> PageUpdate:
        joined = "; ".join(f"{record.case_id}={record.verdict}" for record in records)
        next_step = (
            f"AutoVerifier snapshot synced: {joined}. "
            f"CorrectionSpec remains {SUGGEST_ONLY_BANNER}. "
            "Anchor scope frozen to OF-01/OF-02/OF-03."
        )
        return PageUpdate(
            page_id=page_id,
            properties={"Next Step": _rich_text_property(next_step)},
        )

    @staticmethod
    def _build_report_engine_update(
        page_id: str,
        records: Tuple[CaseSyncRecord, ...],
    ) -> PageUpdate:
        joined = "; ".join(record.report_repo_path for record in records)
        next_step = (
            f"Canonical Docs sync prepared for 3/3 anchor reports: {joined}. "
            f"CorrectionSpec remains {SUGGEST_ONLY_BANNER}."
        )
        return PageUpdate(
            page_id=page_id,
            properties={"Next Step": _rich_text_property(next_step)},
        )

    @staticmethod
    def _build_phase_update(page_id: str) -> PageUpdate:
        return PageUpdate(
            page_id=page_id,
            properties={"Status": {"status": {"name": PHASE_ACTIVE_STATUS}}},
        )

    @staticmethod
    def _build_canonical_doc_create(
        case_record: CaseSyncRecord,
        phase_page_id: str,
        report_engine_task_page_id: str,
        canonical_docs_data_source_id: str,
    ) -> CanonicalDocCreate:
        return CanonicalDocCreate(
            parent_data_source_id=canonical_docs_data_source_id,
            properties={
                "Name": _title_property(f"CFD Report — {case_record.case_id}"),
                "Type": {"select": {"name": CANONICAL_DOC_TYPE}},
                "Status": {"select": {"name": CANONICAL_DOC_STATUS}},
                "Version": _rich_text_property("phase8-8b-2"),
                "Summary": _rich_text_property(case_record.summary),
                "Repo Path": _rich_text_property(case_record.report_repo_path),
                "Tasks": {"relation": [{"id": report_engine_task_page_id}]},
                "Phases": {"relation": [{"id": phase_page_id}]},
            },
        )


def _title_property(value: str) -> Dict[str, Any]:
    return {"title": [{"type": "text", "text": {"content": value}}]}


def _rich_text_property(value: str) -> Dict[str, Any]:
    return {"rich_text": [{"type": "text", "text": {"content": value}}]}

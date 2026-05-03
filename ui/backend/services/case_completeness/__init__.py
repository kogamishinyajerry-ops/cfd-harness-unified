"""DEC-V61-116 · case_completeness service.

Diffs a case's current YAML against governance/contract requirements
(case_manifest schema · gold_standard physics_contract preconditions ·
flow-type appropriate solver/turbulence pairings) and emits a prioritized
"missing fields" list for the engineer's right-rail "距离入库标准还差 N 项"
card.

Read-only consumer of:
    - knowledge/whitelist.yaml (whitelist case definitions)
    - knowledge/gold_standards/*.yaml (physics_contract + observables)
    - ui/backend/user_drafts/{case_id}.yaml (whitelist-forked drafts)
    - ui/backend/user_drafts/imported/{case_id}/case_manifest.yaml (v2 manifest)

Public entry point:
    analyze_case_completeness(case_id) -> CaseCompletenessReport

Returns 404-equivalent (None) if case_id resolves to nothing. Otherwise
always returns a valid report — the WHOLE POINT of this service is to
surface incompleteness without crashing on incomplete data.
"""
from __future__ import annotations

from .analyzer import (
    CaseNotFoundError,
    analyze_case_completeness,
)
from .schemas import (
    CaseCompletenessReport,
    CaseKind,
    MissingField,
    Severity,
)

__all__ = [
    "CaseNotFoundError",
    "analyze_case_completeness",
    "CaseCompletenessReport",
    "CaseKind",
    "MissingField",
    "Severity",
]

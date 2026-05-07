"""DEC-V61-153 (N5.2) · honest issue enumerator.

Pure rule-based scanner that walks case state and emits structured
:class:`Issue` records. Reuses the N5.1 case-state walker
(`build_beginner_report`) so the issue list and the report stay
coherent — they emit complementary views (red flags vs verdict)
of the same source data.

Public surface:
    enumerate_issues(case_dir) -> IssueList
"""
from __future__ import annotations

from ui.backend.services.case_issues.enumerator import enumerate_issues

__all__ = ["enumerate_issues"]

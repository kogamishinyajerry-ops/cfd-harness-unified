"""DEC-V61-152 (N5.1) · case beginner report module.

Public surface:
    build_beginner_report(case_dir) -> BeginnerReport
        Walks case state and populates the 5-section report.
    render_beginner_report_markdown(report) -> str
        Templates the report into a markdown string.
    derive_verdict(geometry, mesh, physics, solver) -> VerdictSection
        Pure rule function emitting the verdict literal + reason.
"""
from __future__ import annotations

from ui.backend.services.case_report.builder import build_beginner_report
from ui.backend.services.case_report.markdown_renderer import (
    render_beginner_report_markdown,
)
from ui.backend.services.case_report.verdict_rules import derive_verdict

__all__ = [
    "build_beginner_report",
    "derive_verdict",
    "render_beginner_report_markdown",
]

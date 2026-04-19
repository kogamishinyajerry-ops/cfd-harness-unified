"""Structured data contracts for report generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ReportContext:
    case_id: str
    case_meta: Dict[str, Any]
    gold_standard: Dict[str, Any]
    auto_verify_report: Dict[str, Any]
    attribution_report: Optional[Dict[str, Any]]
    correction_spec: Optional[Dict[str, Any]]
    project_progress: Dict[str, Any]


@dataclass
class RenderResult:
    case_id: str
    markdown: str
    section_count: int
    status: str = "rendered"
    reason: Optional[str] = None
    output_path: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


@dataclass
class VisualAcceptanceResult:
    html: str
    case_count: int
    chart_count: int
    output_path: Optional[str] = None

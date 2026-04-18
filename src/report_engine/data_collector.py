"""Collect deterministic report inputs from repo artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import yaml  # type: ignore[import-untyped]

from .schemas import ReportContext

REPO_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_ROOT = REPO_ROOT / "knowledge"
REPORTS_ROOT = REPO_ROOT / "reports"

CASE_ID_TO_WHITELIST_ID = {
    "lid_driven_cavity_benchmark": "lid_driven_cavity",
    "backward_facing_step_steady": "backward_facing_step",
    "cylinder_crossflow": "circular_cylinder_wake",
    "fully_developed_turbulent_pipe_flow": "fully_developed_pipe",
    "axisymmetric_impinging_jet": "impinging_jet",
    "fully_developed_plane_channel_flow": "plane_channel_flow",
}

TOTAL_PROJECT_CASES = 15


class ReportDataCollector:
    """Load report data with graceful degradation on missing optional inputs."""

    def collect(self, case_id: str) -> ReportContext:
        auto_verify_report = self._normalize_auto_verify(self._load_auto_verify(case_id))
        gold_standard = self._load_gold_standard(case_id)
        case_meta = self._load_case_meta(case_id)
        attribution_report = self._load_optional_yaml(REPORTS_ROOT / case_id / "attribution_report.yaml")
        correction_spec = self._load_optional_yaml(REPORTS_ROOT / case_id / "correction_spec.yaml")
        if correction_spec is None:
            correction_spec = auto_verify_report.get("correction_spec")
        correction_spec = self._normalize_correction_spec(correction_spec)

        if attribution_report is None and auto_verify_report.get("correction_spec") is not None:
            src = auto_verify_report["correction_spec"]
            attribution_report = {
                "primary_cause": src.get("primary_cause", "unknown"),
                "confidence": src.get("confidence", "LOW"),
                "suggested_correction": src.get(
                    "suggested_correction",
                    src.get("resolution") or src.get("note", "No suggestion available."),
                ),
            }
        elif attribution_report is not None:
            attribution_report.setdefault("primary_cause", "unknown")
            attribution_report.setdefault("confidence", "LOW")
            attribution_report.setdefault("suggested_correction", "No suggestion available.")

        return ReportContext(
            case_id=case_id,
            case_meta=case_meta,
            gold_standard=gold_standard,
            auto_verify_report=auto_verify_report,
            attribution_report=attribution_report,
            correction_spec=correction_spec,
            project_progress=self._project_progress(),
        )

    def _load_auto_verify(self, case_id: str) -> Dict[str, Any]:
        path = REPORTS_ROOT / case_id / "auto_verify_report.yaml"
        if not path.exists():
            raise ValueError(f"Missing auto_verify_report for {case_id}: {path}")
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    def _load_gold_standard(self, case_id: str) -> Dict[str, Any]:
        path = KNOWLEDGE_ROOT / "gold_standards" / f"{case_id}.yaml"
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    def _load_case_meta(self, case_id: str) -> Dict[str, Any]:
        case_path = KNOWLEDGE_ROOT / "cases" / f"{case_id}.yaml"
        if case_path.exists():
            data = yaml.safe_load(case_path.read_text(encoding="utf-8"))
            data.setdefault("meta_source", str(case_path))
            return data

        whitelist = yaml.safe_load((KNOWLEDGE_ROOT / "whitelist.yaml").read_text(encoding="utf-8"))
        whitelist_id = CASE_ID_TO_WHITELIST_ID.get(case_id, case_id)
        record = next((case for case in whitelist.get("cases", []) if case.get("id") == whitelist_id), None)

        if record is None:
            return {
                "case_id": case_id,
                "name": "[DATA MISSING]",
                "description": "[DATA MISSING]",
                "solver": "[DATA MISSING]",
                "turbulence_model": "[DATA MISSING]",
                "mesh_strategy": "[DATA MISSING]",
                "key_parameters": {},
                "meta_source": "[DATA MISSING]",
            }

        return {
            "case_id": case_id,
            "name": record.get("name", "[DATA MISSING]"),
            "description": record.get("reference", "[DATA MISSING]"),
            "solver": record.get("solver", "[DATA MISSING]"),
            "turbulence_model": record.get("turbulence_model", "[DATA MISSING]"),
            "mesh_strategy": record.get("mesh_strategy", "[DATA MISSING]"),
            "key_parameters": record.get("parameters", {}),
            "meta_source": "[DATA MISSING]",
        }

    def _project_progress(self) -> Dict[str, Any]:
        done_cases = 0
        generated_reports = 0
        for report_path in REPORTS_ROOT.glob("*/auto_verify_report.yaml"):
            generated_reports += 1
            report = yaml.safe_load(report_path.read_text(encoding="utf-8"))
            if report.get("verdict") in {"PASS", "PASS_WITH_DEVIATIONS"}:
                done_cases += 1
        return {
            "done_cases": done_cases,
            "total_cases": TOTAL_PROJECT_CASES,
            "progress_ratio": done_cases / TOTAL_PROJECT_CASES,
            "auto_verify_reports": generated_reports,
        }

    @staticmethod
    def _load_optional_yaml(path: Path) -> Optional[Dict[str, Any]]:
        if not path.exists():
            return None
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    @staticmethod
    def _normalize_auto_verify(report: Dict[str, Any]) -> Dict[str, Any]:
        """Defend Jinja StrictUndefined against schema drift in hand-written reports."""
        comparison = report.setdefault("gold_standard_comparison", {})
        comparison.setdefault("overall", "SKIPPED")
        comparison.setdefault("observables", [])
        comparison.setdefault("warnings", [])
        convergence = report.setdefault("convergence", {})
        convergence.setdefault("status", "UNKNOWN")
        convergence.setdefault("final_residual", None)
        convergence.setdefault("target_residual", 1e-5)
        convergence.setdefault("residual_ratio", None)
        convergence.setdefault("warnings", [])
        physics = report.setdefault("physics_check", {})
        physics.setdefault("status", "UNKNOWN")
        physics.setdefault("warnings", [])
        report.setdefault("verdict", "UNKNOWN")
        report.setdefault("correction_spec_needed", report.get("verdict") not in ("PASS", "UNKNOWN", None))
        return report

    @staticmethod
    def _normalize_correction_spec(spec: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if spec is None:
            return None
        spec.setdefault("primary_cause", "unknown")
        spec.setdefault("confidence", "LOW")
        if "suggested_correction" not in spec:
            spec["suggested_correction"] = spec.get("resolution") or spec.get(
                "note",
                "No suggestion available.",
            )
        return spec

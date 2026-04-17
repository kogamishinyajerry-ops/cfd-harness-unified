"""AutoVerifier orchestration and optional post-execute hook."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import yaml  # type: ignore[import-untyped]

from .config import (
    ANCHOR_CASE_IDS,
    CASE_ID_TO_GOLD_FILE,
    DEFAULT_TIMESTAMP,
    REPORTS_ROOT,
    TASK_NAME_TO_CASE_ID,
)
from .convergence_checker import ConvergenceChecker
from .correction_suggester import CorrectionSuggester
from .gold_standard_comparator import GoldStandardComparator
from .physics_checker import PhysicsChecker
from .schemas import AutoVerifyReport, ConvergenceReport, GoldStandardComparison, PhysicsCheck


class AutoVerifier:
    """Deterministic, suggest-only verification over existing execution evidence."""

    def __init__(self) -> None:
        self._convergence_checker = ConvergenceChecker()
        self._gold_standard_comparator = GoldStandardComparator()
        self._physics_checker = PhysicsChecker()
        self._correction_suggester = CorrectionSuggester()

    def verify(
        self,
        *,
        case_id: str,
        log_file: Path,
        gold_standard: Dict[str, Any],
        sim_results: Dict[str, Any],
        output_path: Optional[Path] = None,
        post_processing_dir: Optional[Path] = None,
        timestamp: str = DEFAULT_TIMESTAMP,
    ) -> AutoVerifyReport:
        _ = post_processing_dir
        if case_id not in ANCHOR_CASE_IDS:
            report = AutoVerifyReport(
                case_id=case_id,
                timestamp=timestamp,
                convergence=ConvergenceReport(
                    status="UNKNOWN",
                    final_residual=None,
                    target_residual=self._convergence_checker._target_residual,
                    residual_ratio=None,
                    warnings=["out_of_scope_case"],
                ),
                gold_standard_comparison=GoldStandardComparison(
                    overall="SKIPPED",
                    warnings=["out_of_scope_case"],
                ),
                physics_check=PhysicsCheck(status="WARN", warnings=["out_of_scope_case"]),
                verdict="PASS_WITH_DEVIATIONS",
                correction_spec_needed=False,
                correction_spec=None,
                out_of_scope_reason="Phase 8a is frozen to the Phase 7 coverage anchor set.",
            )
            if output_path is not None:
                self.write_report(output_path, report)
            return report

        convergence = self._convergence_checker.check(log_file)
        comparison = self._gold_standard_comparator.compare(gold_standard, sim_results)
        physics = self._physics_checker.check(sim_results)
        verdict = self._determine_verdict(convergence, comparison, physics)
        correction = self._correction_suggester.suggest(
            convergence,
            comparison,
            physics,
            transient_case=case_id == "cylinder_crossflow",
        )
        report = AutoVerifyReport(
            case_id=case_id,
            timestamp=timestamp,
            convergence=convergence,
            gold_standard_comparison=comparison,
            physics_check=physics,
            verdict=verdict,
            correction_spec_needed=verdict != "PASS",
            correction_spec=correction if verdict != "PASS" else None,
        )
        if output_path is not None:
            self.write_report(output_path, report)
        return report

    def verify_from_files(
        self,
        *,
        case_id: str,
        log_file: Path,
        gold_standard_file: Path,
        sim_results_file: Path,
        output_path: Path,
        post_processing_dir: Optional[Path] = None,
        timestamp: str = DEFAULT_TIMESTAMP,
    ) -> AutoVerifyReport:
        gold_standard = yaml.safe_load(gold_standard_file.read_text(encoding="utf-8"))
        sim_results = self._load_mapping_file(sim_results_file)
        return self.verify(
            case_id=case_id,
            log_file=log_file,
            gold_standard=gold_standard,
            sim_results=sim_results,
            output_path=output_path,
            post_processing_dir=post_processing_dir,
            timestamp=timestamp,
        )

    def build_post_execute_hook(
        self,
        *,
        enabled: bool,
        output_root: Path = REPORTS_ROOT,
        timestamp: str = DEFAULT_TIMESTAMP,
    ) -> "PostExecuteHook":
        return PostExecuteHook(
            verifier=self,
            enabled=enabled,
            output_root=output_root,
            timestamp=timestamp,
        )

    @staticmethod
    def write_report(output_path: Path, report: AutoVerifyReport) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            yaml.safe_dump(report.to_dict(), sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

    @staticmethod
    def resolve_case_id(name_or_case_id: str) -> str:
        return TASK_NAME_TO_CASE_ID.get(name_or_case_id, name_or_case_id)

    @staticmethod
    def _determine_verdict(
        convergence: ConvergenceReport,
        comparison: GoldStandardComparison,
        physics: PhysicsCheck,
    ) -> str:
        if convergence.status == "DIVERGED" or comparison.overall == "FAIL" or physics.status == "FAIL":
            return "FAIL"
        if (
            convergence.status == "CONVERGED"
            and comparison.overall == "PASS"
            and physics.status == "PASS"
        ):
            return "PASS"
        return "PASS_WITH_DEVIATIONS"

    @staticmethod
    def _load_mapping_file(path: Path) -> Dict[str, Any]:
        if path.suffix.lower() == ".json":
            return json.loads(path.read_text(encoding="utf-8"))
        return yaml.safe_load(path.read_text(encoding="utf-8"))


class PostExecuteHook:
    """Optional sidecar hook for future TaskRunner integration."""

    def __init__(
        self,
        *,
        verifier: AutoVerifier,
        enabled: bool,
        output_root: Path,
        timestamp: str,
    ) -> None:
        self._verifier = verifier
        self._enabled = enabled
        self._output_root = output_root
        self._timestamp = timestamp

    def __call__(self, task_spec, exec_result, comparison_result=None, correction_spec=None):  # noqa: ANN001
        _ = comparison_result
        _ = correction_spec
        if not self._enabled:
            return {"enabled": False, "status": "disabled"}

        case_id = self._verifier.resolve_case_id(task_spec.name)
        if case_id not in ANCHOR_CASE_IDS:
            return {
                "enabled": True,
                "status": "out_of_scope",
                "case_id": case_id,
                "reason": "Phase 8a is frozen to the Phase 7 coverage anchor set.",
            }

        raw_output_path = Path(exec_result.raw_output_path or "")
        log_file = self._find_log_file(raw_output_path)
        report = self._verifier.verify(
            case_id=case_id,
            log_file=log_file,
            gold_standard=yaml.safe_load(CASE_ID_TO_GOLD_FILE[case_id].read_text(encoding="utf-8")),
            sim_results=dict(exec_result.key_quantities),
            output_path=self._output_root / case_id / "auto_verify_report.yaml",
            timestamp=self._timestamp,
        )
        return report

    @staticmethod
    def _find_log_file(raw_output_path: Path) -> Path:
        if not raw_output_path.exists():
            raise FileNotFoundError(f"raw_output_path does not exist: {raw_output_path}")
        log_files = sorted(raw_output_path.glob("log.*"))
        if not log_files:
            raise FileNotFoundError(f"no log.* file found under {raw_output_path}")
        return log_files[0]

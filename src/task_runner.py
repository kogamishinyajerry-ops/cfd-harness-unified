"""核心编排器：从 Notion 读取任务 → 执行 → 对比 → 记录 → 回写"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from .foam_agent_adapter import FoamAgentExecutor, MockExecutor
from .knowledge_db import KnowledgeDB
from .metrics import (
    CaseProfileError,
    MetricClass,
    MetricReport,
    MetricStatus,
    TrustGateReport,
    load_tolerance_policy,
    reduce_reports,
)
from .models import (
    AttributionReport,
    BatchResult,
    CFDExecutor,
    ComparisonResult,
    Compressibility,
    CorrectionSpec,
    ExecutionResult,
    FlowType,
    GeometryType,
    SteadyState,
    SystematicPattern,
    TaskSpec,
)
from .notion_client import NotionClient
from .result_comparator import ResultComparator
from .correction_recorder import CorrectionRecorder
from .error_attributor import ErrorAttributor

if TYPE_CHECKING:
    from .convergence_attestor import AttestationResult

PostExecuteHook = Callable[
    [TaskSpec, ExecutionResult, Optional[ComparisonResult], Optional[CorrectionSpec]],
    Any,
]

CORRECTION_POLICIES = ("legacy_auto_save", "suggest_only")

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# P1-T5 · TrustGate integration helper
# ---------------------------------------------------------------------------

_ATTEST_VERDICT_TO_STATUS: Dict[str, MetricStatus] = {
    "ATTEST_PASS": MetricStatus.PASS,
    "ATTEST_HAZARD": MetricStatus.WARN,
    "ATTEST_FAIL": MetricStatus.FAIL,
    "ATTEST_NOT_APPLICABLE": MetricStatus.WARN,
}


def _build_trust_gate_report(
    *,
    task_name: str,
    comparison: Optional[ComparisonResult],
    attestation: Optional["AttestationResult"],
) -> Optional[TrustGateReport]:
    """Aggregate legacy ComparisonResult + AttestationResult into a
    TrustGateReport for P1-T5 downstream consumers.

    Pre-P1-T4 ObservableDef formalization, this produces synthetic
    MetricReports (one residual-class from attestor verdict, one
    pointwise-class from gold comparison) and reduces them worst-wins.
    Returns None when neither input is available (e.g. Notion-only path).

    Plane: Control → Evaluation (import src.metrics). ADR-001 matrix row
    `Control | ✓ (orchestrate) |` authorizes this.

    DEC-V61-071 · P1 tail · load_tolerance_policy is invoked here so the
    policy-dispatch path is exercised in production before P1-T4
    (ObservableDef formalization) unblocks per-observable threshold
    application. Today the loaded policy is stamped into provenance for
    observability — verdict semantics are unchanged.
    """
    try:
        tolerance_policy = load_tolerance_policy(task_name)
    except CaseProfileError as exc:
        logger.warning(
            "load_tolerance_policy failed for %s: %s; "
            "falling back to empty policy",
            task_name,
            exc,
        )
        tolerance_policy = {}

    reports: List[MetricReport] = []

    if attestation is not None:
        status = _ATTEST_VERDICT_TO_STATUS.get(
            attestation.overall, MetricStatus.WARN
        )
        concerns = [c for c in attestation.checks if c.verdict != "PASS"]
        concerns_text = "; ".join(
            f"{c.check_id}/{c.concern_type}: {c.summary}" for c in concerns
        )
        if concerns_text:
            notes = concerns_text
        elif attestation.overall == "ATTEST_NOT_APPLICABLE":
            # Mirror src.metrics.residual: preserve the WARN reason on the
            # no-log path so Control-plane consumers don't see an unexplained
            # warning. Codex DEC-V61-056 finding #1.
            notes = (
                "attestor not applicable (no solver log resolvable "
                "from artifacts)"
            )
        else:
            notes = None
        reports.append(
            MetricReport(
                name=f"{task_name}_convergence_attestation",
                metric_class=MetricClass.RESIDUAL,
                status=status,
                provenance={
                    "attest_verdict": attestation.overall,
                    "source": "task_runner._build_trust_gate_report",
                },
                notes=notes,
            )
        )

    if comparison is not None:
        status = MetricStatus.PASS if comparison.passed else MetricStatus.FAIL
        deviation: Optional[float] = None
        if comparison.deviations:
            errs = [
                d.relative_error
                for d in comparison.deviations
                if d.relative_error is not None
            ]
            if errs:
                deviation = max(errs)
        provenance: Dict[str, Any] = {
            "source": "task_runner._build_trust_gate_report",
            "comparator_summary": comparison.summary,
            "tolerance_policy_observables": sorted(tolerance_policy.keys()),
        }
        if comparison.gold_standard_id:
            provenance["gold_standard_id"] = comparison.gold_standard_id
        reports.append(
            MetricReport(
                name=f"{task_name}_gold_comparison",
                metric_class=MetricClass.POINTWISE,
                status=status,
                deviation=deviation,
                provenance=provenance,
                notes=comparison.summary if not comparison.passed else None,
            )
        )

    if not reports:
        return None
    return reduce_reports(reports)


@dataclass
class RunReport:
    """单次任务运行的完整报告"""
    task_spec: TaskSpec
    execution_result: ExecutionResult
    comparison_result: Optional[ComparisonResult]
    correction_spec: Optional[CorrectionSpec]
    summary: str
    attestation: Optional["AttestationResult"] = None
    auto_verify_report: Any = None  # AutoVerifyReport or hook-returned status dict, when hook configured
    trust_gate_report: Optional[TrustGateReport] = None
    """P1-T5 · aggregated PASS/WARN/FAIL verdict across attestation +
    gold-comparison for this task. Populated by `_build_trust_gate_report`
    from the existing comparison_result + attestation outputs — no
    refactor of the comparator/attestor paths. Pre-P1-T4 ObservableDef
    formalization, this is a 2-report reduce (one residual-class from
    attestor, one pointwise-class from comparator) wrapped in TrustGate's
    worst-wins aggregation. When neither attestation nor comparison
    applies (e.g. Notion-only write-back path), this is None."""


class TaskRunner:
    """核心编排器

    使用方式：
        runner = TaskRunner(executor=MockExecutor())
        reports = runner.run_all()
    """

    def __init__(
        self,
        executor: Optional[CFDExecutor] = None,
        notion_client: Optional[NotionClient] = None,
        knowledge_db: Optional[KnowledgeDB] = None,
        deviation_threshold: float = 0.10,
        post_execute_hook: Optional[PostExecuteHook] = None,
        correction_policy: str = "legacy_auto_save",
    ) -> None:
        if correction_policy not in CORRECTION_POLICIES:
            raise ValueError(
                f"correction_policy must be one of {CORRECTION_POLICIES}, got {correction_policy!r}"
            )
        # Precedence: explicit executor kwarg > EXECUTOR_MODE env var > MockExecutor
        if executor is not None:
            self._executor: CFDExecutor = executor
        else:
            mode = os.environ.get("EXECUTOR_MODE", "mock").lower()
            if mode == "mock":
                self._executor = MockExecutor()
            elif mode == "foam_agent":
                self._executor = FoamAgentExecutor()
            else:
                raise ValueError(
                    f'EXECUTOR_MODE must be "mock" or "foam_agent", got "{mode}"'
                )
        self._notion = notion_client or NotionClient()
        self._db = knowledge_db or KnowledgeDB()
        self._comparator = ResultComparator(threshold=deviation_threshold)
        self._recorder = CorrectionRecorder()
        self._attributor = ErrorAttributor(knowledge_db=self._db)
        self._post_execute_hook = post_execute_hook
        self._correction_policy = correction_policy

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def run_task(self, task_spec: TaskSpec) -> RunReport:
        """执行单个任务，返回完整报告"""
        logger.info("Running task: %s", task_spec.name)

        # 1. 执行 CFD
        exec_result = self._executor.execute(task_spec)
        logger.info("Execution success=%s is_mock=%s", exec_result.success, exec_result.is_mock)

        # 2. 先做收敛 attestation；ATTEST_FAIL 不再进入 compare/correction。
        attestation = self._compute_attestation(exec_result, task_spec)

        # 3. 加载 Gold Standard
        gold = self._db.load_gold_standard(task_spec.name)
        comparison: Optional[ComparisonResult] = None
        correction: Optional[CorrectionSpec] = None

        # 4. 对比结果（仅 ATTEST_FAIL short-circuit；HAZARD 仍保留诊断值）
        if (
            gold is not None
            and exec_result.success
            and attestation.overall != "ATTEST_FAIL"
        ):
            comparison = self._comparator.compare(exec_result, gold)
            logger.info("Comparison passed=%s", comparison.passed)

            # 5. 如有偏差 → 生成 CorrectionSpec (saved only under legacy_auto_save policy)
            if not comparison.passed:
                correction = self._recorder.record(task_spec, exec_result, comparison)
                if self._correction_policy == "legacy_auto_save":
                    self._db.save_correction(correction)
                else:
                    logger.info(
                        "correction_policy=%s: CorrectionSpec built but not persisted",
                        self._correction_policy,
                    )

        # 6. AutoVerifier post-execute hook (SPEC §INT-1, additive)
        auto_verify_report: Any = None
        if self._post_execute_hook is not None:
            try:
                auto_verify_report = self._post_execute_hook(
                    task_spec, exec_result, comparison, correction
                )
            except Exception:  # noqa: BLE001 - hook is optional, must not kill run
                logger.exception("post_execute_hook raised; continuing without verify report")

        # 7. 生成摘要
        summary = self._build_summary(exec_result, comparison, correction, attestation)

        # 8. 回写 Notion（Notion 未配置时静默跳过）
        try:
            self._notion.write_execution_result(task_spec, exec_result, summary)
        except NotImplementedError:
            logger.debug("Notion not configured, skipping write-back")

        trust_gate_report = _build_trust_gate_report(
            task_name=task_spec.name,
            comparison=comparison,
            attestation=attestation,
        )

        return RunReport(
            task_spec=task_spec,
            execution_result=exec_result,
            comparison_result=comparison,
            correction_spec=correction,
            attestation=attestation,
            summary=summary,
            auto_verify_report=auto_verify_report,
            trust_gate_report=trust_gate_report,
        )

    def run_all(self) -> List[RunReport]:
        """从 Notion 读取所有 Ready 任务并逐一运行"""
        try:
            tasks = self._notion.list_pending_tasks()
        except NotImplementedError:
            logger.warning("Notion not configured; run_all() returns empty list")
            return []

        reports = []
        for task in tasks:
            report = self.run_task(task)
            reports.append(report)
        return reports

    def run_batch(self, case_ids: List[str]) -> BatchResult:
        """批量执行指定 case_id 列表（串行，一个失败不阻塞其他）。

        每个 case 执行 run_task -> compare -> attribute 完整链路。
        """
        results: List[ComparisonResult] = []
        attribution_reports: List[Optional[AttributionReport]] = []
        errors: List[str] = []
        passed = 0
        failed = 0
        total = len(case_ids)

        for idx, case_id in enumerate(case_ids, 1):
            try:
                task_spec = self._task_spec_from_case_id(case_id)
                report = self.run_task(task_spec)

                comparison = report.comparison_result
                if comparison is None:
                    comparison = self._ensure_batch_comparison(case_id, report)

                results.append(comparison)

                # 归因（即使 passed=True 也做归因）
                if comparison is not None:
                    attribution = self._attributor.attribute(task_spec, report.execution_result, comparison)
                else:
                    attribution = None
                attribution_reports.append(attribution)

                if report.comparison_result is not None and report.comparison_result.passed:
                    passed += 1
                    print(f"Case {idx}/{total}: {case_id} [PASSED]")
                else:
                    failed += 1
                    print(f"Case {idx}/{total}: {case_id} [FAILED]")

            except Exception:
                failed += 1
                errors.append(case_id)
                results.append(ComparisonResult(passed=False, summary=f"Exception during {case_id}"))
                attribution_reports.append(None)
                logger.exception("Batch case failed: %s", case_id)
                print(f"Case {idx}/{total}: {case_id} [ERROR]")

        # Batch-level systematic pattern analysis
        systematic_patterns = self._analyze_systematic_patterns(case_ids, results, attribution_reports)

        return BatchResult(
            total=total,
            passed=passed,
            failed=failed,
            errors=errors,
            results=results,
            attribution_reports=attribution_reports,
            systematic_patterns=systematic_patterns,
        )

    def _task_spec_from_case_id(self, case_id: str) -> TaskSpec:
        """从 knowledge_db 通过 case_id 还原 TaskSpec。"""
        chain = self._db.get_execution_chain(case_id)
        if chain is None:
            raise ValueError(f"Unknown case_id: {case_id}")
        parameters = chain.get("parameters", {})
        return TaskSpec(
            name=chain.get("case_name", case_id),
            geometry_type=GeometryType(chain.get("geometry_type", "SIMPLE_GRID")),
            flow_type=FlowType(chain.get("flow_type", "INTERNAL")),
            steady_state=SteadyState(chain.get("steady_state", "STEADY")),
            compressibility=Compressibility(chain.get("compressibility", "INCOMPRESSIBLE")),
            Re=parameters.get("Re"),
            Ra=parameters.get("Ra"),
            Re_tau=parameters.get("Re_tau"),
            Ma=parameters.get("Ma"),
            boundary_conditions={**chain.get("boundary_conditions", {}), **parameters},  # includes aspect_ratio, plate_length, etc.
            description=chain.get("reference", ""),
        )

    def _ensure_batch_comparison(self, case_id: str, report: RunReport) -> ComparisonResult:
        """确保 report 有 comparison_result（如果没有则尝试生成）。"""
        if report.comparison_result is not None:
            return report.comparison_result
        if (
            report.attestation is not None
            and report.attestation.overall == "ATTEST_FAIL"
        ):
            return ComparisonResult(
                passed=False,
                summary="Comparison skipped because attestation failed before extraction",
            )
        if not report.execution_result.success:
            return ComparisonResult(
                passed=False,
                summary=report.execution_result.error_message or "Execution failed before comparison",
            )
        gold = self._db.load_gold_standard(case_id) or self._db.load_gold_standard(report.task_spec.name)
        if gold is None:
            return ComparisonResult(
                passed=False,
                summary=f"No gold standard found for case '{case_id}'",
            )
        return self._comparator.compare(report.execution_result, gold)

    def _analyze_systematic_patterns(
        self,
        case_ids: List[str],
        results: List[ComparisonResult],
        attribution_reports: List[Optional[AttributionReport]],
    ) -> List[SystematicPattern]:
        """检测批量执行中的系统性误差模式（frequency > 0.5）。"""
        cause_counts: Dict[str, List[str]] = {}
        for case_id, attr in zip(case_ids, attribution_reports):
            if attr is None:
                continue
            cause = attr.primary_cause
            if cause not in ("unknown", "none", ""):
                cause_counts.setdefault(cause, []).append(case_id)

        patterns = []
        total = len(case_ids)
        for cause, affected in cause_counts.items():
            freq = len(affected) / total
            if freq > 0.5:
                if freq > 0.75:
                    confidence = "high"
                elif freq > 0.5:
                    confidence = "medium"
                else:
                    confidence = "low"

                recommendations = {
                    "mock_executor": "Consider Docker real execution for these cases to get physical results",
                    "sample_config_mismatch": "Review sampleDict configuration — field names may not match generated output",
                    "mesh": "Consider increasing mesh resolution across affected cases",
                    "turbulence": "Review turbulence model selection — kEpsilon may be more stable than kOmegaSST for these geometries",
                    "boundary_condition": "Verify BC setup against reference literature",
                    "solver": "Check solver convergence settings — may need adjusted relaxation or time step",
                }
                patterns.append(SystematicPattern(
                    cause=cause,
                    affected_cases=affected,
                    frequency=freq,
                    confidence=confidence,
                    recommendation=recommendations.get(cause, f"Review cases with {cause} root cause"),
                ))
        return patterns

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    @staticmethod
    def _build_summary(
        exec_result: ExecutionResult,
        comparison: Optional[ComparisonResult],
        correction: Optional[CorrectionSpec],
        attestation: Optional["AttestationResult"] = None,
    ) -> str:
        parts = []
        status = "✅ Success" if exec_result.success else "❌ Failed"
        parts.append(f"{status} (mock={exec_result.is_mock}, t={exec_result.execution_time_s:.2f}s)")
        if attestation is not None:
            parts.append(f"Attestation: {attestation.overall}")
        if comparison is not None:
            parts.append(f"Comparison: {'PASS' if comparison.passed else 'FAIL'}")
            if comparison.deviations:
                parts.append(f"Deviations: {len(comparison.deviations)}")
        if correction is not None:
            parts.append(f"CorrectionSpec generated: {correction.error_type.value}")
        return " | ".join(parts)

    def _compute_attestation(
        self,
        exec_result: ExecutionResult,
        task_spec: TaskSpec,
    ) -> "AttestationResult":
        """Run the convergence attestor against the best-available solver log."""
        from .convergence_attestor import AttestationResult, attest

        log_path = self._resolve_log_path(exec_result)
        case_id = self._resolve_attestation_case_id(task_spec)
        try:
            return attest(
                log_path=log_path,
                execution_result=exec_result,
                case_id=case_id,
            )
        except Exception:  # noqa: BLE001 - attestor failure must not kill the task
            logger.exception("Attestation failed; returning ATTEST_NOT_APPLICABLE")
            return AttestationResult(overall="ATTEST_NOT_APPLICABLE", checks=[])

    def _resolve_attestation_case_id(self, task_spec: TaskSpec) -> str:
        chain = self._db.get_execution_chain(task_spec.name)
        if chain is not None and chain.get("case_id"):
            return str(chain["case_id"])
        return task_spec.name

    @staticmethod
    def _resolve_log_path(exec_result: ExecutionResult) -> Optional[Path]:
        """Resolve the newest solver log under raw_output_path."""
        if not exec_result.raw_output_path:
            return None
        base = Path(exec_result.raw_output_path)
        if base.is_file():
            return base if base.name.startswith("log.") else None
        if not base.is_dir():
            return None
        log_files = sorted(base.glob("log.*"))
        return log_files[-1] if log_files else None

"""核心编排器：从 Notion 读取任务 → 执行 → 对比 → 记录 → 回写"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from .audit_package.reference_lookup import has_docker_openfoam_reference_run
from .executor import (
    DockerOpenFOAMExecutor,
    ExecutorAbc,
    ExecutorMode,
    ExecutorStatus,
    FutureRemoteExecutor,
    HybridInitExecutor,
)
from .executor import MockExecutor as _ExecutorPlaneMockExecutor  # noqa: F401 (registry lookup)
from .executor.base import RunReport as ExecutorRunReport
from .foam_agent_adapter import FoamAgentExecutor, MockExecutor
from .knowledge_db import KnowledgeDB
from .metrics import (
    CaseProfileError,
    MetricClass,
    MetricReport,
    MetricStatus,
    SOURCE_ORIGIN_IMPORTED_USER,
    TrustGateReport,
    apply_executor_mode_routing,
    apply_source_origin_routing,
    load_tolerance_policy,
    reduce_reports,
)
from .metrics.trust_gate import ModeNotYetImplementedError
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

# DEC-V61-075 P2-T2.1 (Codex R3 P2): notes the OK-path of run_task
# propagates to the TaskRunner.RunReport summary (and thus to Notion +
# log consumers). Vocabulary is deliberately narrow — only operational-
# environment signals that change the operator's interpretation of a
# "❌ Failed" line. Trust/manifest annotations (e.g.,
# ``mock_executor_no_truth_source``) are NOT in this set; they live on
# the AuditPackage manifest's ``executor`` section per T1.b.1 + §6.1.
# Adding a new note requires:
#   1. The producing executor (e.g., FoamAgentExecutor.execute_with_run_report)
#      attaches it under a documented condition.
#   2. The note is named so consumers can ``in`` against this set.
#   3. A regression test in tests/test_task_runner_executor_mode.py
#      confirms the note reaches summary.
_OK_PATH_PROPAGATED_NOTES: frozenset[str] = frozenset({
    "docker_openfoam_preflight_failed",
})

# DEC-V61-075 P2-T2.3 Codex post-commit R2 P1 fix (refined R3 P2):
# ``legacy_case_ids`` rename metadata lives in
# ``<knowledge_root>/gold_standards/<case>.yaml`` — NOT in
# ``KnowledgeDB.load_gold_standard``'s return (which surfaces the
# embedded ``whitelist.yaml::gold_standard`` block only). The resolver
# consults this file-backed source via the **injected** KnowledgeDB's
# root so callers using ``TaskRunner(knowledge_db=KnowledgeDB(
# knowledge_dir=...))`` (custom knowledge bundles, test harnesses with
# stubbed roots) still get correct alias resolution.


def _load_legacy_aliases(case_id: str, knowledge_root: Path) -> tuple[str, ...]:
    """Read ``<knowledge_root>/gold_standards/<case_id>.yaml::legacy_case_ids``.

    Returns an empty tuple on any failure (file missing, malformed
    YAML, field absent, non-list value, non-string entries) — must
    NOT raise so the HYBRID_INIT lookup degrades gracefully to
    canonical-id-only matching when alias data is unavailable. The
    ``knowledge_root`` parameter (Codex R3 P2 fix) honors the
    KnowledgeDB injection contract: the same root the rest of the
    runner consults for whitelist + corrections.
    """
    yaml_path = knowledge_root / "gold_standards" / f"{case_id}.yaml"
    if not yaml_path.is_file():
        return ()
    try:
        import yaml  # noqa: PLC0415 — optional-cost local import

        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — alias lookup must not kill the run
        logger.exception(
            "Failed to load gold standard %s for legacy alias lookup; "
            "continuing with no aliases",
            yaml_path,
        )
        return ()
    if not isinstance(data, dict):
        return ()
    legacy = data.get("legacy_case_ids")
    if not isinstance(legacy, list):
        return ()
    return tuple(alias for alias in legacy if isinstance(alias, str))


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# P1-T5 · TrustGate integration helper
# ---------------------------------------------------------------------------


def _resolve_case_slug_for_policy(
    task_name: str, knowledge_db: Optional["KnowledgeDB"] = None
) -> str:
    """Resolve a TaskSpec.name (display title or slug) to the canonical
    case-id slug expected by load_tolerance_policy.

    DEC-V61-071 round-1 finding #1 (verbatim fix): TaskSpec.name often
    comes from display titles (Notion page titles, whitelist `name`
    field), not slugs. Walks the whitelist matching name OR id;
    returns task_name unchanged on no match. Fail-soft — resolution
    must not kill the run.

    DEC-V61-075 P2-T2.3 Codex R4 P2 fix: when ``knowledge_db`` is
    provided, walk THAT bundle's whitelist instead of instantiating
    a default ``KnowledgeDB()``. Honors the injected-DB contract for
    custom knowledge bundles (production HPC harnesses, test stubs).

    DEC-V61-075 P2-T2.3 Codex R5 P2 fix: try the injected DB first,
    fall through to the default DB when the injected one is a
    duck-typed stub that doesn't implement ``_load_whitelist`` (e.g.,
    a bare ``MagicMock`` from a test that doesn't care about slug
    resolution). The default-DB fallback recovers slug-resolution for
    standard whitelist cases without requiring every test to wire up
    ``_load_whitelist`` on its mock.
    """
    candidate_dbs: list = []
    if knowledge_db is not None:
        candidate_dbs.append(knowledge_db)
    # Always include the default DB as a fallback so duck-typed stubs
    # that miss ``_load_whitelist`` still resolve standard slugs.
    try:
        from .knowledge_db import KnowledgeDB  # noqa: PLC0415

        candidate_dbs.append(KnowledgeDB())
    except Exception:  # noqa: BLE001 - default DB construction must not kill the run
        pass

    for db in candidate_dbs:
        try:
            whitelist = db._load_whitelist()
        except Exception:  # noqa: BLE001 - duck-type guard
            continue
        if not isinstance(whitelist, dict):
            continue
        for case in whitelist.get("cases", []):
            if not isinstance(case, dict):
                continue
            if case.get("name") == task_name or case.get("id") == task_name:
                return case.get("id") or task_name
    return task_name


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

    DEC-V61-071 · P1 tail · load_tolerance_policy is invoked **only** when a
    comparison report is being built, so the policy-dispatch path is
    exercised in production whenever there's somewhere to surface the
    loaded observables. Verdict semantics are unchanged — the loaded
    policy is stamped into the comparison report's provenance for
    observability before P1-T4 (ObservableDef formalization) unblocks
    per-observable threshold application.

    Round-1 Codex fixes (DEC-V61-071 R1 verbatim):
    - F#1 MED: TaskSpec.name is often a display title ("Lid-Driven Cavity")
      not a slug ("lid_driven_cavity"). Resolve via the whitelist
      name↔id mapping before calling load_tolerance_policy.
    - F#2 LOW: Lazy-load only inside the comparison branch — no
      filesystem I/O on attestation-only or no-input paths.
    """
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
        # DEC-V61-071 R1 F#1+F#2 verbatim: resolve display-title → slug,
        # then lazy-load the tolerance_policy here (only when there's a
        # comparison report to receive provenance).
        case_slug = _resolve_case_slug_for_policy(task_name)
        try:
            tolerance_policy = load_tolerance_policy(case_slug)
        except CaseProfileError as exc:
            logger.warning(
                "load_tolerance_policy failed for %s (slug=%s): %s; "
                "falling back to empty policy",
                task_name,
                case_slug,
                exc,
            )
            tolerance_policy = {}

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
        executor_mode: Optional[ExecutorMode] = None,
        executor_abc: Optional[ExecutorAbc] = None,
        audit_package_root: Optional[Path] = None,
    ) -> None:
        if correction_policy not in CORRECTION_POLICIES:
            raise ValueError(
                f"correction_policy must be one of {CORRECTION_POLICIES}, got {correction_policy!r}"
            )
        # DEC-V61-074 P2-T1.b dispatch (EXECUTOR_ABSTRACTION §6.1):
        # `executor_abc` (explicit ExecutorAbc instance) wins; else
        # `executor_mode` resolves the canonical subclass via
        # `_resolve_executor_abc`; else None means "stay on the legacy
        # CFDExecutor protocol path" — required for backwards compat
        # with all pre-P2 callers that hand in an `executor=` kwarg or
        # rely on EXECUTOR_MODE env-var. Both new fields are additive
        # and mutually exclusive (ValueError on conflict).
        if executor_abc is not None and executor_mode is not None:
            raise ValueError(
                "executor_abc and executor_mode are mutually exclusive — "
                "pass exactly one (or neither, to keep the legacy path)"
            )
        if executor_abc is not None:
            self._executor_abc: Optional[ExecutorAbc] = executor_abc
        elif executor_mode is not None:
            self._executor_abc = self._resolve_executor_abc(executor_mode)
        else:
            self._executor_abc = None

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
        # DEC-V61-075 P2-T2.3: optional audit-package corpus root for
        # §6.3 hybrid-init reference-run resolution. None means "no
        # lookup" — apply_executor_mode_routing falls through to the
        # ``hybrid_init_invariant_unverified`` WARN ceiling, which is
        # the spec-mandated first-ever-run behavior.
        self._audit_package_root: Optional[Path] = audit_package_root

    @staticmethod
    def _resolve_executor_abc(mode: ExecutorMode) -> ExecutorAbc:
        """Map an `ExecutorMode` to its skeleton-class instance per
        EXECUTOR_ABSTRACTION.md §2 + §6.1.

        Raises `KeyError` (with the unknown mode value) if the enum is
        ever extended without updating this table — keeps the routing
        contract falsifiable per RETRO-V61-001 baseline (any new
        `ExecutorMode` value must add a row here under Codex review).
        """
        registry: Dict[ExecutorMode, type[ExecutorAbc]] = {
            ExecutorMode.DOCKER_OPENFOAM: DockerOpenFOAMExecutor,
            ExecutorMode.MOCK: _ExecutorPlaneMockExecutor,
            ExecutorMode.HYBRID_INIT: HybridInitExecutor,
            ExecutorMode.FUTURE_REMOTE: FutureRemoteExecutor,
        }
        try:
            cls = registry[mode]
        except KeyError as exc:
            raise KeyError(
                f"No ExecutorAbc subclass registered for ExecutorMode={mode!r}; "
                "add a row to TaskRunner._resolve_executor_abc"
            ) from exc
        return cls()

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def run_task(self, task_spec: TaskSpec) -> RunReport:
        """执行单个任务，返回完整报告"""
        logger.info("Running task: %s", task_spec.name)

        # 1. 执行 CFD — DEC-V61-074 P2-T1.b dispatch.
        # When an ExecutorAbc instance is configured (via executor_mode
        # or executor_abc kwarg), route through the new abstraction:
        # non-OK statuses (MODE_NOT_APPLICABLE / MODE_NOT_YET_IMPLEMENTED)
        # short-circuit before comparator/correction so downstream
        # extractors never see synthetic-or-absent ExecutionResult.
        executor_notes: tuple[str, ...] = ()
        if self._executor_abc is not None:
            executor_run_report = self._executor_abc.execute(task_spec)
            if executor_run_report.status is not ExecutorStatus.OK:
                short_report = self._build_short_circuit_report(
                    task_spec, executor_run_report
                )
                # Codex P2-T1.b.2 post-commit MED fix: surface the
                # refusal to Notion so the existing failure-handling
                # contract (notion_client maps success=False →
                # Status=Review) is honored. Without this, a refused
                # run leaves the Notion task stuck in Ready instead
                # of advancing to Review.
                try:
                    self._notion.write_execution_result(
                        task_spec,
                        short_report.execution_result,
                        short_report.summary,
                    )
                except NotImplementedError:
                    logger.debug(
                        "Notion not configured, skipping short-circuit write-back"
                    )
                return short_report
            assert executor_run_report.execution_result is not None  # OK invariant
            exec_result = executor_run_report.execution_result
            # DEC-V61-075 P2-T2.1 (Codex R3 P2 fix): preserve
            # operationally-significant OK-path executor notes for
            # downstream summary/Notion consumers. Without this,
            # Docker SDK / container / case-dir failures surface as
            # a generic "❌ Failed" line — indistinguishable from
            # solver divergence — and Notion + TrustGate consumers
            # lose the executor-emitted environment signal.
            #
            # Note vocabulary is intentionally narrow: only
            # operational-environment failures (preflight) propagate
            # to summary. Trust/manifest annotations like
            # ``mock_executor_no_truth_source`` belong on the manifest's
            # ``executor`` section (set by callers via
            # ``build_manifest(executor=...)`` per T1.b.1), not on
            # ``TaskRunner.RunReport.summary``. Mixing the two would
            # double-surface the mock ceiling and confuse log readers
            # who already see the routing-imposed WARN downstream.
            executor_notes = tuple(
                note for note in executor_run_report.notes
                if note in _OK_PATH_PROPAGATED_NOTES
            )
        else:
            # DEC-V61-075 P2-T2.1 (Codex R4 P2-A fix): legacy CFDExecutor
            # branch — when ``self._executor`` happens to be a
            # ``FoamAgentExecutor`` (the production path used by
            # scripts/p2_acceptance_run.py, scripts/phase5_audit_run.py,
            # ui/backend/services/wizard_drivers.py) detect pre-flight
            # failure inline so the same operator signal reaches
            # summary regardless of which dispatch kwarg the caller
            # used. Other CFDExecutor implementations (MockExecutor,
            # plug-ins) take the unchanged path; the FoamAgent-specific
            # branch keeps coupling minimal and avoids requiring every
            # CFDExecutor to grow a notes contract.
            exec_result = self._executor.execute(task_spec)
            if (
                isinstance(self._executor, FoamAgentExecutor)
                and not exec_result.success
                and exec_result.raw_output_path is None
            ):
                executor_notes = ("docker_openfoam_preflight_failed",)
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
        summary = self._build_summary(
            exec_result, comparison, correction, attestation,
            executor_notes=executor_notes,
        )

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

        # DEC-V61-075 P2-T2.3 · §6.3 reference-run gate wiring.
        # When ABC-dispatched, apply the per-mode TrustGate routing
        # ceilings (mock → WARN, hybrid_init → reference-run gated)
        # using the executor's identity tuple as the manifest section
        # surrogate. The audit-package lookup runs only for HYBRID_INIT
        # (other modes don't consume the flag) so DOCKER_OPENFOAM /
        # MOCK runs pay zero filesystem cost.
        if (
            self._executor_abc is not None
            and trust_gate_report is not None
        ):
            executor_section = {
                "mode": self._executor_abc.MODE.value,
                "version": self._executor_abc.VERSION,
                "contract_hash": self._executor_abc.contract_hash,
            }
            ref_present = False
            if (
                self._executor_abc.MODE is ExecutorMode.HYBRID_INIT
                and self._audit_package_root is not None
            ):
                # Codex T2.3 post-commit P2-A fix: resolve display
                # title → canonical slug before scanning manifests.
                # `task_spec.name` may be a Notion page title or
                # whitelist `name` field; archived manifests store
                # `case.id` as the canonical slug, so passing the
                # raw display name would silently miss every real
                # reference run.
                # Codex R4 P2 fix: pass the injected KnowledgeDB so
                # custom knowledge bundles get the right canonical id
                # for display-title task names.
                canonical_case_id = _resolve_case_slug_for_policy(
                    task_spec.name, knowledge_db=self._db
                )
                # Codex T2.3 post-commit R1 P2-B + R2 P1 fix: expand
                # legacy aliases from the file-backed gold-standard
                # YAML (``knowledge/gold_standards/<case>.yaml::
                # legacy_case_ids``) so the resolver can match
                # pre-rename manifests too. R1's first attempt used
                # ``KnowledgeDB.load_gold_standard`` but that returns
                # the embedded ``whitelist.yaml::gold_standard`` block,
                # which does NOT carry rename metadata; the file-backed
                # gold standard at ``knowledge/gold_standards/<case>.yaml``
                # is the canonical source for ``legacy_case_ids`` (see
                # also ``src/audit_package/manifest.py::_load_gold_standard``).
                # Failure to resolve must NOT break the run — fall
                # through to empty aliases and rely on direct id match
                # only.
                # Codex R3 P2 fix: source the knowledge root from the
                # injected KnowledgeDB (``self._db._root``) so custom
                # knowledge bundles + test harness stubs get honored.
                # Falls back to the default root if the injected DB
                # doesn't expose ``_root`` (defensive — KnowledgeDB
                # always sets it, but a future drop-in replacement
                # might not).
                kn_root = getattr(self._db, "_root", None)
                if not isinstance(kn_root, Path):
                    from .knowledge_db import _DEFAULT_KNOWLEDGE_DIR  # noqa: PLC0415
                    kn_root = _DEFAULT_KNOWLEDGE_DIR
                legacy_aliases = _load_legacy_aliases(
                    canonical_case_id, knowledge_root=kn_root
                )
                ref_present = has_docker_openfoam_reference_run(
                    case_id=canonical_case_id,
                    audit_package_root=self._audit_package_root,
                    legacy_aliases=legacy_aliases,
                )
            try:
                trust_gate_report = apply_executor_mode_routing(
                    trust_gate_report,
                    executor_section,
                    hybrid_init_reference_run_present=ref_present,
                )
            except ModeNotYetImplementedError:
                # FUTURE_REMOTE refusal — should never reach here in
                # practice (FUTURE_REMOTE returns MODE_NOT_YET_IMPLEMENTED
                # status which short-circuits at line ~342). Defensive
                # log + leave trust_gate_report unchanged so callers
                # see the underlying verdict + the OK-path note already
                # appended to summary above.
                logger.warning(
                    "ModeNotYetImplementedError raised for OK-path "
                    "future_remote run — should be unreachable; check "
                    "executor short-circuit invariant"
                )

        # DEC-V61-091 M5.1 · source-origin verdict ceiling.
        # Per DEC-V61-090 the M6.1 contract guarantees
        # `task_spec.mesh_already_provided=True` ⟺ workbench imported
        # user case (no production caller sets the flag for any other
        # case kind). Translate that boolean into the canonical
        # source-origin tag and apply the cap. Composition order:
        # source-origin ceiling runs AFTER executor-mode ceiling so
        # both ceilings stack monotonically (worst-wins preserved by
        # `_ceiling_to_warn`).
        if trust_gate_report is not None and getattr(
            task_spec, "mesh_already_provided", False
        ):
            trust_gate_report = apply_source_origin_routing(
                trust_gate_report, SOURCE_ORIGIN_IMPORTED_USER
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
    def _build_short_circuit_report(
        task_spec: TaskSpec, executor_run_report: ExecutorRunReport
    ) -> "RunReport":
        """Build a TaskRunner.RunReport for a non-OK ExecutorAbc result.

        Per EXECUTOR_ABSTRACTION.md §6.1, MODE_NOT_APPLICABLE
        (hybrid_init §5.2 escape) and MODE_NOT_YET_IMPLEMENTED
        (future_remote stub) statuses MUST NOT feed comparator /
        correction / attestor — those expect a populated
        ExecutionResult. Surface the executor's notes verbatim so the
        UI / CLI can render the refusal reason.
        """
        synthetic = ExecutionResult(
            success=False,
            is_mock=False,
            error_message=(
                f"executor_mode={executor_run_report.mode.value} "
                f"status={executor_run_report.status.value}"
            ),
            execution_time_s=0.0,
        )
        notes_repr = ", ".join(executor_run_report.notes) or "(no notes)"
        summary = (
            f"⏭ Short-circuit: {executor_run_report.mode.value} → "
            f"{executor_run_report.status.value} | notes: {notes_repr}"
        )
        return RunReport(
            task_spec=task_spec,
            execution_result=synthetic,
            comparison_result=None,
            correction_spec=None,
            summary=summary,
            attestation=None,
            auto_verify_report=None,
            trust_gate_report=None,
        )

    @staticmethod
    def _build_summary(
        exec_result: ExecutionResult,
        comparison: Optional[ComparisonResult],
        correction: Optional[CorrectionSpec],
        attestation: Optional["AttestationResult"] = None,
        executor_notes: tuple[str, ...] = (),
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
        # DEC-V61-075 P2-T2.1 (Codex R3 P2 fix): surface OK-path
        # executor notes (e.g., docker_openfoam_preflight_failed) so
        # Notion + log consumers can branch on environment failures.
        if executor_notes:
            parts.append(f"Executor notes: {', '.join(executor_notes)}")
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

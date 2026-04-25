"""ResidualMetric · P1-T1d · convergence/quality attestation.

Delegates to `src.convergence_attestor.attest()` for the A1..A6 checks
(solver crash · continuity floor · residual floor · iteration cap ·
bounding recurrence · no progress). Unlike Pointwise/Integrated/Spectral,
residual metrics do NOT have a gold-standard reference value — the
attestor produces absolute verdicts from solver log evidence + per-case
thresholds (knowledge/attestor_thresholds.yaml).

Verdict mapping (AttestVerdict → MetricStatus):
  - ATTEST_PASS           → PASS
  - ATTEST_HAZARD         → WARN  (one or more A2/A3/A5/A6 hazard)
  - ATTEST_FAIL           → FAIL  (A1 crash or A4 iteration-cap)
  - ATTEST_NOT_APPLICABLE → WARN  (no log → cannot attest; downstream
                                   TrustGate should not silently PASS)

`value`, `reference_value`, `deviation`, `tolerance_applied` are all
None (not applicable — this is an absolute attestation, not a gold-ref
deviation). The verdict string is surfaced via `provenance.attest_verdict`
for report UI / TrustGate inspection. `notes` aggregates per-check
concerns when status != PASS.

Plane: Evaluation (src.metrics.residual → src.convergence_attestor) —
both sides are Evaluation Plane per ADR-001 §2.1, same as Pointwise/
Integrated. No Execution imports.

Examples of residual metrics in the 10-case whitelist:
- `final_p_residual` (all cases · sum_local from pimpleFoam/simpleFoam log)
- `a1_continuity_attestation` .. `a6_physical_sanity_attestation`
  (convergence_attestor A1..A6 per DEC-V61-038)
- `wall_y_plus_range` (near-wall mesh quality · all RANS cases)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from ..convergence_attestor import (
    AttestationResult,
    AttestorCheck,
    attest,
)
from ..models import ExecutionResult
from .base import Metric, MetricClass, MetricReport, MetricStatus


_VERDICT_TO_STATUS: Dict[str, MetricStatus] = {
    "ATTEST_PASS": MetricStatus.PASS,
    "ATTEST_HAZARD": MetricStatus.WARN,
    "ATTEST_FAIL": MetricStatus.FAIL,
    "ATTEST_NOT_APPLICABLE": MetricStatus.WARN,
}


def _resolve_log_path(artifacts: Any, observable_def: Dict[str, Any]) -> Optional[Path]:
    """Find the solver log path across heterogeneous artifact shapes.

    Priority:
      1. observable_def["log_path"] explicit override
      2. artifacts.raw_output_path (ExecutionResult / dict) — looks for
         `{case_dir}/log.<solver>` convention
      3. artifacts["log_path"] / ExecutionResult.log_path (duck-typed)
      4. artifacts as Path / str if it is a file
    """
    explicit = observable_def.get("log_path")
    if explicit:
        p = Path(explicit)
        return p if p.is_file() else None

    if hasattr(artifacts, "log_path") and artifacts.log_path:  # type: ignore[attr-defined]
        p = Path(artifacts.log_path)  # type: ignore[attr-defined]
        if p.is_file():
            return p

    if isinstance(artifacts, dict):
        v = artifacts.get("log_path")
        if v:
            p = Path(v)
            if p.is_file():
                return p

    raw = None
    if isinstance(artifacts, ExecutionResult):
        raw = artifacts.raw_output_path
    elif isinstance(artifacts, dict):
        raw = artifacts.get("raw_output_path") or artifacts.get("case_dir")

    if raw:
        base = Path(raw)
        if base.is_file():
            return base
        if base.is_dir():
            # Codex round-6 F10: shared log-name preference order
            # across `_resolve_log_path`, `_find_latest_solver_log`
            # (scripts/render_case_report.py), and `_load_run_outputs`
            # (src/audit_package/manifest.py). Keeping the orders
            # aligned ensures mixed-log artifact dirs resolve the
            # same primary log everywhere. The order prioritizes
            # the most-common production solvers (simpleFoam, icoFoam)
            # then DEC-V61-059's pisoFoam (plane-channel laminar
            # route), then transient/buoyant tail. `log` (no suffix)
            # is a final fallback only.
            for name in (
                "log.simpleFoam",
                "log.icoFoam",
                "log.pisoFoam",
                "log.pimpleFoam",
                "log.buoyantFoam",
                "log.buoyantBoussinesqSimpleFoam",
                "log",
            ):
                candidate = base / name
                if candidate.is_file():
                    return candidate

    if isinstance(artifacts, Path) and artifacts.is_file():
        return artifacts
    if isinstance(artifacts, str):
        p = Path(artifacts)
        if p.is_file():
            return p
    return None


def _summarize_concerns(checks: list[AttestorCheck]) -> str:
    concerns = [c for c in checks if c.verdict != "PASS"]
    if not concerns:
        return ""
    return "; ".join(
        f"{c.check_id}/{c.concern_type}[{c.verdict}]: {c.summary}"
        for c in concerns
    )


class ResidualMetric(Metric):
    metric_class = MetricClass.RESIDUAL
    delegate_to_module = "src.convergence_attestor"

    def evaluate(
        self,
        artifacts: Any,
        observable_def: Dict[str, Any],
        tolerance_policy: Optional[Dict[str, Any]] = None,
    ) -> MetricReport:
        case_id = observable_def.get("case_id")
        log_path = _resolve_log_path(artifacts, observable_def)

        exec_result: Any = None
        if isinstance(artifacts, ExecutionResult):
            exec_result = artifacts

        result: AttestationResult = attest(
            log_path=log_path,
            execution_result=exec_result,
            case_id=case_id,
        )

        status = _VERDICT_TO_STATUS.get(result.overall, MetricStatus.WARN)

        provenance: Dict[str, Any] = {
            "delegate_module": self.delegate_to_module,
            "attest_verdict": result.overall,
            "log_path": str(log_path) if log_path else None,
            "checks": [
                {
                    "check_id": c.check_id,
                    "concern_type": c.concern_type,
                    "verdict": c.verdict,
                    "summary": c.summary,
                }
                for c in result.checks
            ],
        }
        if case_id:
            provenance["case_id"] = case_id

        concerns_text = _summarize_concerns(result.checks)
        if result.overall == "ATTEST_NOT_APPLICABLE":
            notes = "attestor not applicable (no solver log resolvable from artifacts)"
        elif concerns_text:
            notes = concerns_text
        else:
            notes = None

        return MetricReport(
            name=self.name,
            metric_class=self.metric_class,
            value=None,
            unit=self.unit,
            reference_value=None,
            deviation=None,
            tolerance_applied=None,
            status=status,
            provenance=provenance,
            notes=notes,
        )

"""P3 W3.3b · CHT conjugate Gnielinski gate (``cht_conjugate``, Control Plane).

Comparator wiring for the full two-region conjugate benchmark that flips
runnable-coverage 1->2: extract the fluid-PRODUCED Nusselt number from a solved
conjugate channel (Execution Plane, ``src.cht_conjugate_extractor``) and gate it
against the Gnielinski reference in
``knowledge/gold_standards/cht_pipe_gnielinski.yaml`` via the canonical
``ResultComparator`` (Evaluation Plane).

Three HARD gate components backstop the 10% Gnielinski tolerance (gold rationale):

  1. **Energy balance** — the interface wall-heat integral must equal the fluid
     enthalpy rise: ``|Q_total - mdot*cp*(T_out - T_in)| <= rel_tol*|Q_total|``.
     A non-converged or inconsistent solve (e.g. cup-mixing T that disagrees with
     the wall heat) fails here even if Nu accidentally matched.
  2. **Reynolds validity + target match** — the SOLVED Re (recovered from the
     measured inlet mass flux + patch area, NOT the gold YAML) must lie inside the
     Gnielinski band (3e3 < Re < 5e6) AND match the gold's target Re. This
     verifies the *replayed case was actually solved at the gold's flow rate*; a
     stale/drifted run cannot ride a Nu match into a false coverage flip.
  3. **Prandtl validity** — Pr (derived from mu*cp/k_fluid) must lie inside the
     Gnielinski band (0.5 < Pr < 2000). An out-of-domain fluid cannot pass.

ADR-001 plane assignment: **Control Plane** — the only plane permitted to import
BOTH Execution (the extractor) and Evaluation (the comparator), same posture as
``src.task_runner`` / ``src.cht_fin_gate``. All physical inputs come from the
gold's ``case_info.conjugate_inputs`` (the SAME contract the self-verifying
derivation test locks), so the gate carries no independent magic numbers.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

from .cht_conjugate_extractor import (
    ConjugateQoIs,
    extract_conjugate_qois,
    to_key_quantities,
)
from .models import ComparisonResult, ExecutionResult
from .result_comparator import ResultComparator

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_GOLD = _REPO_ROOT / "knowledge" / "gold_standards" / "cht_pipe_gnielinski.yaml"

# Energy-balance closure: the interface wall-heat integral and the fluid enthalpy
# rise (mdot*cp*dT_bulk) are the SAME energy measured two ways. A converged solve
# closes them to ~1%; 5% is slack enough for discretisation yet trips a
# non-converged / inconsistent dataset (which is the failure mode this guards).
_ENERGY_BALANCE_REL_TOL = 0.05

# The SOLVED Reynolds number (recovered from the measured inlet mass flux) must
# match the gold's target Re — otherwise the postProcessing set being replayed is
# not the run this gold describes (stale artifacts / drifted mass flow), and a
# Nu match against the wrong reference would be a false coverage flip.
_RE_TARGET_REL_TOL = 0.05

# Gnielinski Prandtl validity domain (gold may override via Pr_validity_{min,max}).
_PR_VALIDITY_MIN_DEFAULT = 0.5
_PR_VALIDITY_MAX_DEFAULT = 2000.0


@dataclass(frozen=True)
class ConjugateGateResult:
    """Outcome of gating the extracted conjugate Nu against the Gnielinski gold."""

    passed: bool
    qois: ConjugateQoIs
    comparisons: List[Tuple[str, ComparisonResult]]
    energy_balance_ok: bool
    reynolds_in_band: bool        # SOLVED Re inside the Gnielinski validity band
    reynolds_matches_target: bool  # SOLVED Re ~= gold target Re (right run replayed)
    prandtl_in_band: bool          # fluid Pr inside the Gnielinski validity band
    summary: str


def _load_conjugate_gold_docs(gold_path: Path) -> List[Dict[str, Any]]:
    docs = [d for d in yaml.safe_load_all(gold_path.read_text(encoding="utf-8")) if d]
    if not docs:
        raise ValueError(f"empty / unparseable gold standard: {gold_path}")
    return docs


def gate_conjugate_against_gold(
    case_dir: Path,
    gold_path: Path = _DEFAULT_GOLD,
) -> ConjugateGateResult:
    """Run the ``cht_conjugate`` gate: extract Nu, gate vs Gnielinski + hard checks.

    PASSES only if (a) every gold observable is within tolerance via the canonical
    scalar path, (b) the interface/enthalpy energy balance closes, AND (c) Re is
    inside the Gnielinski validity band.
    """
    docs = _load_conjugate_gold_docs(gold_path)
    ci = docs[0]["case_info"]["conjugate_inputs"]
    qois = extract_conjugate_qois(
        case_dir,
        D_h=float(ci["D"]),
        k_fluid=float(ci["k_fluid"]),
        cp=float(ci["cp"]),
        mu=float(ci["mu"]),
    )
    result = ExecutionResult(
        success=True,
        is_mock=False,
        key_quantities=to_key_quantities(qois),
    )

    comparator = ResultComparator()
    comparisons: List[Tuple[str, ComparisonResult]] = []
    for doc in docs:
        gold = {
            "quantity": doc["quantity"],
            "reference_values": doc["reference_values"],
            "tolerance": doc.get("tolerance", 0.10),
            "id": doc.get("case_info", {}).get("id"),
        }
        comparisons.append((doc["quantity"], comparator.compare(result, gold)))

    observables_ok = all(cmp.passed for _, cmp in comparisons)

    # HARD gate 1: energy balance (interface heat == fluid enthalpy rise).
    energy_threshold = _ENERGY_BALANCE_REL_TOL * abs(qois.q_iface_total_w)
    energy_balance_ok = qois.energy_balance_residual_w <= energy_threshold

    # HARD gate 2: Reynolds — derived from the SOLVED case (qois.reynolds_solved),
    # NOT the gold YAML. (a) it must lie inside the Gnielinski validity band, AND
    # (b) it must match the gold's target Re — else the replayed postProcessing set
    # was solved at the wrong flow rate and a Nu match would be against the wrong
    # reference (a false coverage flip). Both use the measured inlet mass flux.
    re_solved = qois.reynolds_solved
    re_target = float(ci["Re"])
    re_min = float(ci["Re_validity_min"])
    re_max = float(ci["Re_validity_max"])
    reynolds_in_band = re_min < re_solved < re_max
    reynolds_matches_target = (
        abs(re_solved - re_target) <= _RE_TARGET_REL_TOL * abs(re_target)
    )

    # HARD gate 3: Prandtl inside the Gnielinski validity band. Pr is DERIVED from
    # the fluid properties (mu*cp/k_fluid), so an alternate fluid / re-anchor with
    # an out-of-domain Pr cannot pass even if Nu + energy happen to match.
    pr = float(ci["mu"]) * float(ci["cp"]) / float(ci["k_fluid"])
    pr_min = float(ci.get("Pr_validity_min", _PR_VALIDITY_MIN_DEFAULT))
    pr_max = float(ci.get("Pr_validity_max", _PR_VALIDITY_MAX_DEFAULT))
    prandtl_in_band = pr_min < pr < pr_max

    passed = (
        observables_ok
        and energy_balance_ok
        and reynolds_in_band
        and reynolds_matches_target
        and prandtl_in_band
    )

    parts = [f"{name}={'PASS' if cmp.passed else 'FAIL'}" for name, cmp in comparisons]
    parts.append(f"energy_balance={'PASS' if energy_balance_ok else 'FAIL'}")
    parts.append(f"Re_in_band={'PASS' if reynolds_in_band else 'FAIL'}")
    parts.append(f"Re_matches_target={'PASS' if reynolds_matches_target else 'FAIL'}")
    parts.append(f"Pr_in_band={'PASS' if prandtl_in_band else 'FAIL'}")
    summary = (
        f"cht_conjugate gate {'PASS' if passed else 'FAIL'} "
        f"(Nu={qois.nusselt_number:.4f}, h={qois.h_w_m2k:.4f} W/m2.K, "
        f"dT_window={qois.delta_t_window_k:.3f} K, "
        f"energy_residual={qois.energy_balance_residual_w:.4g} W <= {energy_threshold:.4g}, "
        f"Re_solved={re_solved:.0f} (target {re_target:g}), Pr={pr:.4f}) | "
        + ", ".join(parts)
    )
    return ConjugateGateResult(
        passed=passed,
        qois=qois,
        comparisons=comparisons,
        energy_balance_ok=energy_balance_ok,
        reynolds_in_band=reynolds_in_band,
        reynolds_matches_target=reynolds_matches_target,
        prandtl_in_band=prandtl_in_band,
        summary=summary,
    )

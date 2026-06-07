"""P4 V71.A · supersonic-wedge oblique-shock gate (``wedge_oblique_shock``, Control Plane).

Comparator wiring for the first compressible / density-based / shock-capturing
coverage benchmark (V71.A rhoCentralFoam anchor): extract the oblique-shock QoIs
from a solved supersonic-wedge case (Execution Plane,
``src.wedge_oblique_shock_extractor``) and gate them against the analytical
theta-beta-M reference in ``knowledge/gold_standards/wedge_oblique_shock.yaml`` via
the canonical ``ResultComparator`` (Evaluation Plane).

All physical inputs (M1, theta, gamma, sample station, validity bands, probe names)
come from the gold's ``case_info.wedge_inputs`` — the SAME contract the
self-verifying derivation test locks — so the gate carries no independent magic
numbers (only documented relative-tolerance module constants).

Five HARD gate components backstop the 3% comparator tolerance, each independent of
the comparator and of each other:

  1. **Supersonic inflow** — the MEASURED freestream Mach (areaAverage Ma upstream)
     must exceed 1. No oblique shock exists for subsonic inflow; a subsonic field
     cannot ride a spurious beta match into a pass.
  2. **Inflow matches target** — the measured freestream Mach must match the gold's
     M1, so the replayed case is the operating point this gold describes (a case run
     at a different Mach cannot pass against the wrong reference).
  3. **Downstream still supersonic** — M2 > 1. The WEAK oblique-shock root leaves the
     flow supersonic; a strong / detached shock (M2 < 1) is the wrong solution and
     fails here even if a ratio happened to match.
  4. **Beta above the Mach angle** — beta > asin(1/M1) (the gold's
     ``beta_validity_min_deg``). A physical oblique shock is always steeper than the
     Mach wave; a degenerate / mis-located shock angle is caught here.
  5. **Ideal-gas thermodynamic consistency** — the INDEPENDENTLY measured p2, rho2,
     T2 must satisfy ``T2/T1 == (p2/p1)/(rho2/rho1)`` (p = rho R T across the shock).
     A doctored single state probe (e.g. a tampered post-shock pressure) breaks this
     even when the comparator's per-ratio check passes — it is the shock analogue of
     the conjugate gate's energy-balance hard gate.

ADR-001 plane assignment: **Control Plane** — the only plane permitted to import
BOTH Execution (the extractor) and Evaluation (the comparator), same posture as
``src.task_runner`` / ``src.cht_conjugate_gate``.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

from .models import ComparisonResult, ExecutionResult
from .result_comparator import ResultComparator
from .wedge_oblique_shock_extractor import (
    WedgeShockQoIs,
    extract_wedge_qois,
    to_key_quantities,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_GOLD = _REPO_ROOT / "knowledge" / "gold_standards" / "wedge_oblique_shock.yaml"

# The MEASURED freestream Mach must match the gold's M1 to this tolerance, else the
# replayed case is not the operating point this gold describes (wrong-reference pass).
_INFLOW_MATCH_REL_TOL = 0.02

# The independently measured p2, rho2, T2 must be ideal-gas consistent across the
# shock: T2/T1 == (p2/p1)/(rho2/rho1). 2% absorbs area-averaging / discretisation
# while still tripping a doctored single state probe.
_IDEAL_GAS_REL_TOL = 0.02


@dataclass(frozen=True)
class WedgeGateResult:
    """Outcome of gating the extracted oblique-shock QoIs against the analytical gold."""

    passed: bool
    qois: WedgeShockQoIs
    comparisons: List[Tuple[str, ComparisonResult]]
    supersonic_inflow_ok: bool       # measured freestream Ma > 1
    inflow_matches_target: bool      # measured freestream Ma ~= gold M1 (right case replayed)
    downstream_supersonic_ok: bool   # M2 > 1 (weak oblique-shock root)
    beta_above_mach_angle_ok: bool   # beta > asin(1/M1) (physical oblique shock)
    ideal_gas_consistent_ok: bool    # T2/T1 == (p2/p1)/(rho2/rho1) (no doctored state probe)
    summary: str


def _load_wedge_gold_docs(gold_path: Path) -> List[Dict[str, Any]]:
    docs = [d for d in yaml.safe_load_all(gold_path.read_text(encoding="utf-8")) if d]
    if not docs:
        raise ValueError(f"empty / unparseable gold standard: {gold_path}")
    return docs


def gate_wedge_against_gold(
    case_dir: Path,
    gold_path: Path = _DEFAULT_GOLD,
) -> WedgeGateResult:
    """Run the ``wedge_oblique_shock`` gate: extract QoIs, gate vs theta-beta-M + hard checks.

    PASSES only if (a) every gold observable is within tolerance via the canonical
    scalar path, AND (b) all five independent hard gates hold.
    """
    docs = _load_wedge_gold_docs(gold_path)
    wi = docs[0]["case_info"]["wedge_inputs"]
    qois = extract_wedge_qois(
        case_dir,
        x_shock_station=float(wi["x_shock_station"]),
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
            "tolerance": doc.get("tolerance", 0.03),
            "id": doc.get("case_info", {}).get("id"),
        }
        comparisons.append((doc["quantity"], comparator.compare(result, gold)))

    observables_ok = all(cmp.passed for _, cmp in comparisons)

    m1_target = float(wi["M1"])
    beta_floor = float(wi["beta_validity_min_deg"])

    # HARD gate 1+2: supersonic inflow, and it is the gold's operating point.
    supersonic_inflow_ok = qois.mach_freestream > 1.0
    inflow_matches_target = (
        abs(qois.mach_freestream - m1_target) <= _INFLOW_MATCH_REL_TOL * abs(m1_target)
    )

    # HARD gate 3: weak oblique-shock root leaves the flow supersonic.
    downstream_supersonic_ok = qois.mach_downstream > 1.0

    # HARD gate 4: a physical oblique shock is steeper than the Mach wave.
    beta_above_mach_angle_ok = qois.shock_angle_beta_deg > beta_floor

    # HARD gate 5: ideal-gas thermodynamic consistency of the independently measured
    # post-shock state (catches a doctored single state probe).
    t_ratio_from_states = qois.pressure_ratio / qois.density_ratio
    ideal_gas_consistent_ok = (
        abs(qois.temperature_ratio - t_ratio_from_states)
        <= _IDEAL_GAS_REL_TOL * abs(qois.temperature_ratio)
    )

    passed = (
        observables_ok
        and supersonic_inflow_ok
        and inflow_matches_target
        and downstream_supersonic_ok
        and beta_above_mach_angle_ok
        and ideal_gas_consistent_ok
    )

    parts = [f"{name}={'PASS' if cmp.passed else 'FAIL'}" for name, cmp in comparisons]
    parts.append(f"supersonic_inflow={'PASS' if supersonic_inflow_ok else 'FAIL'}")
    parts.append(f"inflow_matches_target={'PASS' if inflow_matches_target else 'FAIL'}")
    parts.append(f"downstream_supersonic={'PASS' if downstream_supersonic_ok else 'FAIL'}")
    parts.append(f"beta_above_mach_angle={'PASS' if beta_above_mach_angle_ok else 'FAIL'}")
    parts.append(f"ideal_gas_consistent={'PASS' if ideal_gas_consistent_ok else 'FAIL'}")
    mach_angle_deg = math.degrees(math.asin(1.0 / m1_target)) if m1_target > 1.0 else float("nan")
    summary = (
        f"wedge_oblique_shock gate {'PASS' if passed else 'FAIL'} "
        f"(beta={qois.shock_angle_beta_deg:.4f} deg (Mach angle {mach_angle_deg:.2f}), "
        f"M2={qois.mach_downstream:.4f}, p2/p1={qois.pressure_ratio:.4f}, "
        f"rho2/rho1={qois.density_ratio:.4f}, T2/T1={qois.temperature_ratio:.4f}, "
        f"M1_meas={qois.mach_freestream:.4f} (target {m1_target:g})) | "
        + ", ".join(parts)
    )
    return WedgeGateResult(
        passed=passed,
        qois=qois,
        comparisons=comparisons,
        supersonic_inflow_ok=supersonic_inflow_ok,
        inflow_matches_target=inflow_matches_target,
        downstream_supersonic_ok=downstream_supersonic_ok,
        beta_above_mach_angle_ok=beta_above_mach_angle_ok,
        ideal_gas_consistent_ok=ideal_gas_consistent_ok,
        summary=summary,
    )

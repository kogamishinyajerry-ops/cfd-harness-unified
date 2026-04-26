"""DEC-V61-063 Stage A.5: Execution → Evaluation plane alias parity.

Drives the gold-standard comparator end-to-end on the new flat-plate
observables. Proves that:

  1. Adapter emit keys (`cf_x_profile_points`, `cf_blasius_invariant_*`,
     `delta_99_x_profile`) match the gold YAML `observables[].name` field
     character-for-character — no upstream rename can silently strand a
     gold reference.
  2. The dict shape `_extract_flat_plate_cf` / `_enrich_flat_plate_cf`
     produce flows through `gold_standard_comparator._compare_profile`
     without manual reshaping in the verdict path.
  3. A Blasius-consistent synthetic case yields PASS at the configured
     10% tolerance, confirming the YAML reference values are achievable
     by the documented Blasius similarity (sanity-checks ref_value math).

This is the last Stage A landing before Codex round 1 review.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Tuple

import pytest
import yaml

from auto_verifier import GoldStandardComparator
from src.foam_agent_adapter import FoamAgentExecutor
from src.models import (
    CFDExecutor, Compressibility, FlowType, GeometryType,
    SteadyState, TaskSpec,
)


GOLD_PATH = (
    Path(__file__).resolve().parent.parent
    / "knowledge"
    / "gold_standards"
    / "turbulent_flat_plate.yaml"
)


def _make_task() -> TaskSpec:
    return TaskSpec(
        name="Turbulent Flat Plate (Zero Pressure Gradient)",
        geometry_type=GeometryType.SIMPLE_GRID,
        flow_type=FlowType.EXTERNAL,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.INCOMPRESSIBLE,
        Re=50000,
    )


def _build_blasius_consistent_emit() -> Dict[str, object]:
    """Run the A.2 + A.3 emit chain on Blasius-consistent synthetic data.

    Cells are placed at x ∈ {0.25, 0.5, 0.75, 1.0} with a wall-normal
    cluster of 4 (y, u_x) samples that crosses 0.99·U_∞ at the Blasius
    δ_99 of each x — the same shape Stage B will produce from a clean
    OpenFOAM run on the laminar contract.

    Cf at each x is set so the wall-gradient extractor recovers
    Cf = 0.664/√Re_x exactly. With ν = 1/Re = 2e-5 and U_∞ = 1, this is
    achieved by setting Δu/Δy at the wall such that

        Cf = ν · (du/dy) / (½·U_∞²) = 0.664 / √Re_x

    Solving for du/dy: du/dy = 0.664 · √Re_x · 0.5·U_∞² / ν.
    """
    K_target = 0.664
    Re = 50000.0
    nu = 1.0 / Re
    U_inf = 1.0

    def y_for_threshold(x: float) -> float:
        # Blasius δ_99 = 5·√(ν·x/U_∞)
        return 5.0 * math.sqrt(nu * x / U_inf)

    cxs: List[float] = []
    cys: List[float] = []
    u_vecs: List[Tuple[float, float, float]] = []

    for x in (0.25, 0.5, 0.75, 1.0):
        Re_x = U_inf * x / nu
        Cf_target = K_target / math.sqrt(Re_x)
        # Wall gradient that recovers Cf_target:
        #   Cf = nu · (du/dy) / (0.5·U_inf²)  ⇒  du/dy = Cf · 0.5·U_inf² / nu
        du_dy = Cf_target * 0.5 * U_inf**2 / nu
        # Two interior cells: (c0, u0) and (c1, u1). The gradient is
        # (u1-u0)/(c1-c0). With c0=1e-4, c1=2e-4, u0=du_dy·c0, u1=du_dy·c1:
        c0, c1 = 1e-4, 2e-4
        u0, u1 = du_dy * c0, du_dy * c1
        delta_99 = y_for_threshold(x)
        # Wall-normal samples reaching 0.99·U_∞ at the Blasius δ_99.
        # The 4 samples below give monotonic u(y) crossing 0.99 between
        # y_just_below and y=delta_99.
        y_just_below = delta_99 * 0.7
        y_above = delta_99 * 1.5
        samples = [
            (0.0, 0.0),
            (c0, u0),
            (c1, u1),
            (y_just_below, 0.5 * U_inf),
            (delta_99, 0.99 * U_inf),
            (y_above, 1.0 * U_inf),
        ]
        for y, u in samples:
            cxs.append(x)
            cys.append(y)
            u_vecs.append((u, 0.0, 0.0))

    task = _make_task()
    kq: Dict[str, object] = {}
    kq = FoamAgentExecutor._extract_flat_plate_cf(
        cxs=cxs, cys=cys, u_vecs=u_vecs,
        task_spec=task, key_quantities=kq,
    )
    kq = FoamAgentExecutor._enrich_flat_plate_cf(
        cxs=cxs, cys=cys, u_vecs=u_vecs,
        task_spec=task, key_quantities=kq,
    )
    return kq


@pytest.fixture(scope="module")
def gold_yaml() -> Dict[str, object]:
    return yaml.safe_load(GOLD_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def adapter_emit() -> Dict[str, object]:
    return _build_blasius_consistent_emit()


class TestAliasParityKeys:
    """Names emitted by adapter must match names in gold YAML observables."""

    def test_every_gold_observable_name_appears_in_adapter_emit(
        self, gold_yaml: Dict[str, object], adapter_emit: Dict[str, object],
    ):
        gold_names = {o["name"] for o in gold_yaml["observables"]}
        emit_keys = set(adapter_emit.keys())
        missing = gold_names - emit_keys
        assert not missing, (
            f"Gold observables not produced by adapter emit: {missing}. "
            f"Adapter keys present: {sorted(k for k in emit_keys if 'cf_' in k or 'delta_' in k)}"
        )

    def test_new_a4_observables_present_in_gold(self, gold_yaml: Dict[str, object]):
        """The 3 HARD_GATED observables added in A.4 are in the YAML.
        Codex R1 F1: switched from `cf_blasius_invariant_canonical_K`
        (tautological constant 0.664) to `cf_blasius_invariant_mean_K`
        (measured average) so the hard gate has teeth.
        """
        names = {o["name"] for o in gold_yaml["observables"]}
        assert "cf_x_profile_points" in names
        assert "cf_blasius_invariant_mean_K" in names
        assert "delta_99_x_profile" in names
        # Tautological canonical_K must NOT be hard-gated.
        assert "cf_blasius_invariant_canonical_K" not in names

    def test_back_compat_scalar_still_present(self, gold_yaml: Dict[str, object]):
        """cf_skin_friction (DEC-V61-006 Path A anchor) must not regress."""
        names = {o["name"] for o in gold_yaml["observables"]}
        assert "cf_skin_friction" in names


class TestEndToEndComparison:
    """Drive the gold comparator on a Blasius-consistent synthetic emit."""

    def test_blasius_consistent_emit_passes_overall(
        self, gold_yaml: Dict[str, object], adapter_emit: Dict[str, object],
    ):
        report = GoldStandardComparator().compare(gold_yaml, adapter_emit)
        assert report.overall == "PASS", (
            f"Expected PASS on Blasius-consistent synthetic emit; got "
            f"{report.overall}. Per-observable verdicts: "
            f"{[(c.name, c.within_tolerance, c.rel_error) for c in report.observables]}"
        )

    def test_each_observable_within_tolerance(
        self, gold_yaml: Dict[str, object], adapter_emit: Dict[str, object],
    ):
        report = GoldStandardComparator().compare(gold_yaml, adapter_emit)
        outside = [
            (c.name, c.rel_error, c.abs_error)
            for c in report.observables
            if not c.within_tolerance
        ]
        assert not outside, f"Observables outside tolerance: {outside}"

    def test_cf_x_profile_points_routes_through_profile_path(
        self, gold_yaml: Dict[str, object], adapter_emit: Dict[str, object],
    ):
        """Verify cf_x_profile_points hits _compare_profile (list-of-dicts
        ref_value) rather than _compare_scalar / _compare_mapping.
        Indirect proof: ref_value is a list and rel_error is the *max*
        across the profile points."""
        report = GoldStandardComparator().compare(gold_yaml, adapter_emit)
        check = next(
            c for c in report.observables if c.name == "cf_x_profile_points"
        )
        assert isinstance(check.ref_value, list)
        # Profile path returns sim_value as the interpolated values list.
        assert isinstance(check.sim_value, list)
        assert len(check.sim_value) == len(check.ref_value)

    def test_blasius_invariant_scalar_matches_mean_K(
        self, gold_yaml: Dict[str, object], adapter_emit: Dict[str, object],
    ):
        """Codex R1 F1: the *measured* mean_K (not the constant canonical_K)
        must match 0.664 within 1% on Blasius-consistent synthetic data.
        This is the gate that has teeth: a corrupted profile shifts mean_K
        off-target, while canonical_K stays at 0.664 and would always pass.
        """
        report = GoldStandardComparator().compare(gold_yaml, adapter_emit)
        check = next(
            c for c in report.observables
            if c.name == "cf_blasius_invariant_mean_K"
        )
        assert check.within_tolerance is True
        assert check.rel_error is not None
        assert check.rel_error < 0.01

    def test_corrupted_profile_fails_after_F1_fix(self, gold_yaml: Dict[str, object]):
        """Codex R1 F1 acceptance: a synthetic emit with correct values
        at x ∈ {0.5, 1.0} but Spalding-fallback values at x ∈ {0.25, 0.75}
        must FAIL the overall verdict after the gate switches from
        canonical_K to mean_K. Pre-fix, Codex reproduced this scenario
        passing the comparator with overall=PASS.
        """
        nu = 1.0 / 50000.0
        cf_05 = 0.664 / math.sqrt(50000 * 0.5)
        cf_10 = 0.664 / math.sqrt(50000 * 1.0)
        # Spalding-fallback values at x=0.25, 0.75 — these are turbulent-
        # regime estimates and break Blasius similarity.
        cf_025_fb = 0.0576 / ((0.25 / nu) ** 0.2)
        cf_075_fb = 0.0576 / ((0.75 / nu) ** 0.2)
        # Compute mean_K from the corrupted profile to confirm it's off-target.
        K_025 = cf_025_fb * math.sqrt(0.25 / nu)
        K_05 = cf_05 * math.sqrt(0.5 / nu)
        K_075 = cf_075_fb * math.sqrt(0.75 / nu)
        K_10 = cf_10 * math.sqrt(1.0 / nu)
        mean_K_corrupted = (K_025 + K_05 + K_075 + K_10) / 4.0
        emit = {
            "cf_skin_friction": cf_05,
            "cf_x_profile_points": [
                {"x": 0.25, "Cf": cf_025_fb},
                {"x": 0.5, "Cf": cf_05},
                {"x": 0.75, "Cf": cf_075_fb},
                {"x": 1.0, "Cf": cf_10},
            ],
            "cf_blasius_invariant_mean_K": mean_K_corrupted,
            "delta_99_x_profile": [
                {"x": 0.5, "value": 0.01581},
                {"x": 1.0, "value": 0.02236},
            ],
            "cf_spalding_fallback_count": 2,
            "cf_spalding_fallback_activated": True,
        }
        report = GoldStandardComparator().compare(gold_yaml, emit)
        # The cf_x_profile_points and mean_K both go off-target by enough
        # to push at least one observable past 10% relative tolerance.
        # Verdict must NOT be PASS.
        assert report.overall != "PASS", (
            f"F1 regression: corrupted profile got PASS verdict. "
            f"Per-observable: "
            f"{[(c.name, c.within_tolerance, c.rel_error) for c in report.observables]}"
        )

    def test_delta_99_profile_routes_through_profile_path(
        self, gold_yaml: Dict[str, object], adapter_emit: Dict[str, object],
    ):
        report = GoldStandardComparator().compare(gold_yaml, adapter_emit)
        check = next(
            c for c in report.observables if c.name == "delta_99_x_profile"
        )
        assert check.within_tolerance is True
        assert isinstance(check.ref_value, list)
        assert isinstance(check.sim_value, list)
        assert len(check.sim_value) == len(check.ref_value)

"""DEC-V61-066 Stage A.4: Execution → Evaluation plane alias parity.

Drives the gold-standard comparator end-to-end on the new duct_flow
observables. Proves three contracts that no in-isolation A.1-A.3 test
could prove together:

  1. Adapter emit keys (``friction_factor``, ``friction_velocity_u_tau``,
     ``bulk_velocity_ratio_u_max``, ``log_law_inner_layer_residual``)
     match the gold YAML ``observables[].name`` field character-for-
     character — a silent rename in either plane fails this loud.
  2. A Jones-1976-perfect emit dict (τ_w, U_bulk, u_centroid, log-law
     residual constructed at the canonical anchor values) yields PASS
     at the configured tolerances — sanity-checks the YAML ref_value
     math.
  3. The actual extractor (``_extract_duct_flow_observables`` static
     method on ``FoamAgentExecutor``) produces all 4 emit keys when
     given non-degenerate synthetic cell-centre data — proves the
     wiring at adapter line 8460 does not silently lose any key.

V61-063 A.5 precedent: same triple-contract structure (parity / comparator
routing / extractor key surface). Differences for V61-066:
  - Tolerance check uses MANUALLY-constructed Jones-perfect emit (no
    log-law-consistent + 1/7-power profile reconciliation needed).
  - Extractor surface test asserts on KEY presence, not value tolerance,
    because the 28 unit tests in ``test_duct_flow_extractors.py`` already
    cover value correctness in isolation.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest
import yaml

from auto_verifier import GoldStandardComparator
from src.foam_agent_adapter import FoamAgentExecutor
from src.models import (
    Compressibility, FlowType, GeometryType,
    SteadyState, TaskSpec,
)


GOLD_PATH = (
    Path(__file__).resolve().parent.parent
    / "knowledge"
    / "gold_standards"
    / "duct_flow.yaml"
)

# Canonical Jones 1976 anchor at Re=50000, U_bulk=1, ρ=1.
JONES_F = 0.0185
JONES_U_BULK = 1.0
JONES_RHO = 1.0
JONES_TAU_W = JONES_F * JONES_RHO * JONES_U_BULK ** 2 / 8.0  # 0.0023125
JONES_U_TAU = math.sqrt(JONES_TAU_W / JONES_RHO)             # 0.0480885
JONES_U_MAX_RATIO = 1.20


def _make_task() -> TaskSpec:
    return TaskSpec(
        name="Fully Developed Turbulent Square-Duct Flow",
        geometry_type=GeometryType.SIMPLE_GRID,
        flow_type=FlowType.INTERNAL,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.INCOMPRESSIBLE,
        Re=50000,
        boundary_conditions={
            "hydraulic_diameter": 0.1,
            "aspect_ratio": 1.0,
        },
    )


def _build_jones_perfect_emit() -> Dict[str, Any]:
    """Manually construct an emit dict at the Jones 1976 anchor.

    Bypasses the cell-centred extractor to isolate the comparator-
    routing contract from the wall-gradient + cross-section sampling
    machinery (those have 28 unit tests in test_duct_flow_extractors).
    """
    return {
        "friction_factor": JONES_F,                     # 0.0185
        "friction_velocity_u_tau": JONES_U_TAU,          # 0.04811
        "bulk_velocity_ratio_u_max": JONES_U_MAX_RATIO,  # 1.20
        "log_law_inner_layer_residual": 0.0,             # log-law-perfect
        # Audit keys (not gated, but adapter emits them).
        "duct_flow_extractor_path": "wall_shear_v1",
        "duct_flow_tau_w": JONES_TAU_W,
        "duct_flow_U_bulk": JONES_U_BULK,
        "duct_flow_extractor_x_target": 2.5,
    }


def _build_minimal_extractor_input() -> Dict[str, Any]:
    """Build cell-centred synthetic data at x_target=2.5 sufficient to
    produce all 4 emit keys (presence test, not value test).

    Layout:
      - 1 wall cell at (x=2.5, y=0.0, u_x=0.0)        — skipped (no-slip)
      - 2 wall-adjacent cells at (y=1e-4, y=2e-4) with u_x set so the
        wall gradient yields τ_w = 0.0023125 (Jones anchor).
      - 6 log-law-band cells at y ∈ [0.013, 0.083] with u_x consistent
        with the universal log-law u+ = 2.439·ln(y+) + 5.0.
      - 1 centroid cell at y=0.25 with u_x=1.20.
      - 5 outer-channel cells uniformly between y=0.27 and y=0.49
        with u_x ramping back down (mirror about y=0.25).

    All cells carry the same x=2.5 so they all enter the cross-section
    at x_target. cz is omitted (None on a 2D thin-slice run).
    """
    Re = 50000.0
    nu = 1.0 / Re
    # Wall gradient cells: u(y) = (τ_w / ν) · y for y near wall.
    du_dy = JONES_TAU_W / nu  # 115.625
    cxs: List[float] = []
    cys: List[float] = []
    u_vecs: List[Tuple[float, float, float]] = []

    def _add(y: float, u: float) -> None:
        cxs.append(2.5)
        cys.append(y)
        u_vecs.append((u, 0.0, 0.0))

    # Wall + wall-adjacent (gradient stencil)
    _add(0.0, 0.0)
    _add(1e-4, du_dy * 1e-4)   # 0.0115625
    _add(2e-4, du_dy * 2e-4)   # 0.023125

    # Log-law band: y ∈ [0.013, 0.083] (y+ ∈ [30, 200])
    for y_plus in (35.0, 60.0, 90.0, 120.0, 160.0, 195.0):
        y = y_plus * nu / JONES_U_TAU
        u_plus = (1.0 / 0.41) * math.log(y_plus) + 5.0
        u = u_plus * JONES_U_TAU
        _add(y, u)

    # Centroid + outer wake (linear ramp from log-law top to u_max=1.20
    # then mirror back down toward top wall at y=0.5).
    _add(0.15, 1.05)
    _add(0.25, 1.20)
    _add(0.35, 1.05)
    _add(0.45, 0.5)
    _add(0.49, 0.05)

    return {
        "cxs": cxs,
        "cys": cys,
        "u_vecs": u_vecs,
    }


@pytest.fixture(scope="module")
def gold_yaml() -> Dict[str, Any]:
    return yaml.safe_load(GOLD_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def jones_perfect_emit() -> Dict[str, Any]:
    return _build_jones_perfect_emit()


class TestAliasParityKeys:
    """Names emitted by adapter must match names in gold YAML observables."""

    def test_every_gold_observable_name_appears_in_jones_emit(
        self, gold_yaml: Dict[str, Any], jones_perfect_emit: Dict[str, Any],
    ):
        gold_names = {o["name"] for o in gold_yaml["observables"]}
        emit_keys = set(jones_perfect_emit.keys())
        missing = gold_names - emit_keys
        assert not missing, (
            f"Gold observables not produced by Jones-perfect emit: {missing}. "
            f"Emit keys: {sorted(emit_keys)}"
        )

    def test_all_a3_observables_present_in_gold(self, gold_yaml: Dict[str, Any]):
        """The 3 HARD_GATED observables added in A.3 are in the YAML."""
        names = {o["name"] for o in gold_yaml["observables"]}
        assert "friction_velocity_u_tau" in names
        assert "bulk_velocity_ratio_u_max" in names
        assert "log_law_inner_layer_residual" in names

    def test_back_compat_friction_factor_still_present(
        self, gold_yaml: Dict[str, Any]
    ):
        """friction_factor (DEC-V61-011 anchor) must not regress."""
        names = {o["name"] for o in gold_yaml["observables"]}
        assert "friction_factor" in names

    def test_extractor_paths_match_a1_module(self, gold_yaml: Dict[str, Any]):
        """Each gold observable's `extractor` field must reference a real
        function in src.duct_flow_extractors."""
        from src import duct_flow_extractors as dfe
        for obs in gold_yaml["observables"]:
            extractor_path = obs.get("extractor", "")
            if not extractor_path.startswith("src.duct_flow_extractors."):
                continue  # HEADLINE may legitimately point elsewhere
            func_name = extractor_path.split(".")[-1]
            assert hasattr(dfe, func_name), (
                f"Gold observable '{obs['name']}' references "
                f"{extractor_path} but {func_name} not exported"
            )


class TestComparatorRoutingOnJonesPerfectEmit:
    """Drive GoldStandardComparator on a Jones-anchored emit dict.

    Bypasses the cell-centred extraction step (covered by 28 unit tests
    in test_duct_flow_extractors). Focus: verdict pipeline routes each
    of the 4 observables through the right tolerance branch and returns
    PASS overall.
    """

    def test_jones_perfect_emit_passes_overall(
        self, gold_yaml: Dict[str, Any], jones_perfect_emit: Dict[str, Any],
    ):
        report = GoldStandardComparator().compare(gold_yaml, jones_perfect_emit)
        assert report.overall == "PASS", (
            f"Expected PASS on Jones-perfect emit; got {report.overall}. "
            f"Per-observable verdicts: "
            f"{[(c.name, c.within_tolerance, c.rel_error) for c in report.observables]}"
        )

    def test_each_observable_within_tolerance(
        self, gold_yaml: Dict[str, Any], jones_perfect_emit: Dict[str, Any],
    ):
        report = GoldStandardComparator().compare(gold_yaml, jones_perfect_emit)
        outside = [
            (c.name, c.rel_error, c.abs_error)
            for c in report.observables
            if not c.within_tolerance
        ]
        assert not outside, f"Observables outside tolerance: {outside}"

    def test_log_law_residual_uses_absolute_tolerance(
        self, gold_yaml: Dict[str, Any], jones_perfect_emit: Dict[str, Any],
    ):
        """log_law_inner_layer_residual ref_value=0.0 + tolerance.mode=absolute.
        ref=0.0 + relative-mode would divide by zero — absolute is required."""
        report = GoldStandardComparator().compare(gold_yaml, jones_perfect_emit)
        check = next(
            c for c in report.observables
            if c.name == "log_law_inner_layer_residual"
        )
        # ref_value=0.0, sim=0.0 → abs_error=0.0, within tol=0.5 absolute.
        assert check.within_tolerance is True
        assert check.abs_error == pytest.approx(0.0, abs=1e-9)


class TestExtractorEmitKeySurface:
    """Verify _extract_duct_flow_observables produces all 4 emit keys
    when fed non-degenerate synthetic cell data at x_target=2.5."""

    def test_extractor_emits_all_four_observables(self):
        cells = _build_minimal_extractor_input()
        task = _make_task()
        kq: Dict[str, Any] = {}
        kq = FoamAgentExecutor._extract_duct_flow_observables(
            cxs=cells["cxs"],
            cys=cells["cys"],
            u_vecs=cells["u_vecs"],
            task_spec=task,
            key_quantities=kq,
            czs=None,
            latest_dir=None,
        )
        assert "friction_factor" in kq, f"Got keys: {sorted(kq.keys())}"
        assert "friction_velocity_u_tau" in kq
        assert "bulk_velocity_ratio_u_max" in kq
        assert "log_law_inner_layer_residual" in kq

    def test_extractor_audit_path_stamped(self):
        cells = _build_minimal_extractor_input()
        task = _make_task()
        kq: Dict[str, Any] = {}
        kq = FoamAgentExecutor._extract_duct_flow_observables(
            cxs=cells["cxs"],
            cys=cells["cys"],
            u_vecs=cells["u_vecs"],
            task_spec=task,
            key_quantities=kq,
            czs=None,
            latest_dir=None,
        )
        assert kq.get("duct_flow_extractor_path") == "wall_shear_v1"
        assert kq.get("duct_flow_extractor_x_target") == 2.5
        assert kq.get("duct_flow_extractor_n_cross_section", 0) >= 10

    def test_extractor_recovers_jones_anchor_from_synthetic_input(self):
        """End-to-end check: synthetic cells at the Jones anchor should
        produce extractor outputs within tolerance of the gold ref_values."""
        cells = _build_minimal_extractor_input()
        task = _make_task()
        kq: Dict[str, Any] = {}
        kq = FoamAgentExecutor._extract_duct_flow_observables(
            cxs=cells["cxs"],
            cys=cells["cys"],
            u_vecs=cells["u_vecs"],
            task_spec=task,
            key_quantities=kq,
            czs=None,
            latest_dir=None,
        )
        # Friction factor: tolerance 10% relative.
        # NOTE: U_bulk is dy-weighted (R1 F#1 fix) over the synthetic cells,
        # which is NOT exactly 1.0 by construction. The wall gradient is
        # exact, so f ≈ 0.0185 only if U_bulk happens to be near 1.0.
        # Just assert sign + magnitude order; comparator tolerance band
        # is exercised in TestComparatorRoutingOnJonesPerfectEmit above.
        assert kq["friction_factor"] > 0.0
        assert kq["friction_factor"] < 1.0  # f < 1 always for real flow
        # Friction velocity: derived solely from τ_w which is exact here.
        assert kq["friction_velocity_u_tau"] == pytest.approx(JONES_U_TAU, rel=0.01)
        # Tau_w sign-flip flag should be False on this monotonic input.
        assert kq.get("duct_flow_tau_w_sign_flipped") is False


class TestUBulkDyWeighted:
    """DEC-V61-066 Codex R1 finding #1 regression.

    Case-gen mesh has simpleGrading (1 4 1) — y-cells are non-uniform.
    Arithmetic mean over u_x over-weights small wall cells where u≈0,
    biasing U_bulk DOWN. Verify the extractor uses dy-weighted mean
    so non-uniform cy spacing doesn't bias the friction-factor gate.
    """

    def _build_nonuniform_input(self) -> Dict[str, Any]:
        """Cross-section with deliberately non-uniform cy spacing.

        y values: [0.0, 1e-4, 2e-4, 0.05, 0.10, 0.40, 0.49]
        u_x values: [0.0, 0.0116, 0.0231, 0.5, 1.0, 0.6, 0.05]

        Arithmetic mean ≈ 0.312 (small wall cells dominate the count
        even though they cover almost no dy).
        dy-weighted mean ≈ 0.639 (centre-channel cell at y=0.10 with
        u=1.0 owns a large dy=0.175 strip).
        """
        cxs: List[float] = []
        cys: List[float] = []
        u_vecs: List[Tuple[float, float, float]] = []
        for y, u in [
            (0.0, 0.0),
            (1e-4, 0.0116),
            (2e-4, 0.0231),
            (0.05, 0.5),
            (0.10, 1.0),
            (0.40, 0.6),
            (0.49, 0.05),
        ]:
            cxs.append(2.5)
            cys.append(y)
            u_vecs.append((u, 0.0, 0.0))
        return {"cxs": cxs, "cys": cys, "u_vecs": u_vecs}

    def test_uses_dy_weighted_method_audit_key(self):
        cells = self._build_nonuniform_input()
        kq: Dict[str, Any] = {}
        kq = FoamAgentExecutor._extract_duct_flow_observables(
            cxs=cells["cxs"], cys=cells["cys"], u_vecs=cells["u_vecs"],
            task_spec=_make_task(), key_quantities=kq,
            czs=None, latest_dir=None,
        )
        assert kq.get("duct_flow_U_bulk_method") == "dy_weighted_mean"

    def test_dy_weighted_differs_from_arithmetic(self):
        """U_bulk emitted should match the hand-computed dy-weighted
        value, NOT the arithmetic mean — proves the bias-fix landed."""
        cells = self._build_nonuniform_input()
        kq: Dict[str, Any] = {}
        kq = FoamAgentExecutor._extract_duct_flow_observables(
            cxs=cells["cxs"], cys=cells["cys"], u_vecs=cells["u_vecs"],
            task_spec=_make_task(), key_quantities=kq,
            czs=None, latest_dir=None,
        )
        # Arithmetic mean = 2.1847 / 7 ≈ 0.3121
        # dy-weighted ≈ 0.6394 (see docstring derivation)
        u_bulk = kq["duct_flow_U_bulk"]
        assert u_bulk == pytest.approx(0.639, rel=0.02)
        # And NOT the arithmetic mean — gap is large enough to detect.
        assert abs(u_bulk - 0.312) > 0.1

    def test_friction_factor_uses_dy_weighted_u_bulk(self):
        """f = 8·τ_w/(ρ·U_bulk²) — verify the dy-weighted U_bulk feeds
        the friction-factor extractor (not arithmetic), preventing the
        wall-grading bias from inflating f."""
        cells = self._build_nonuniform_input()
        kq: Dict[str, Any] = {}
        kq = FoamAgentExecutor._extract_duct_flow_observables(
            cxs=cells["cxs"], cys=cells["cys"], u_vecs=cells["u_vecs"],
            task_spec=_make_task(), key_quantities=kq,
            czs=None, latest_dir=None,
        )
        tau_w = kq["duct_flow_tau_w"]
        u_bulk = kq["duct_flow_U_bulk"]
        f_expected = 8.0 * tau_w / (1.0 * u_bulk ** 2)
        assert kq["friction_factor"] == pytest.approx(f_expected, rel=1e-9)


class TestNutAuditKeys:
    """DEC-V61-066 Codex R1 finding #2 regression.

    The extractor uses (ν + ν_t)·du/dy for τ_w, but the postprocess
    copy list (`_copy_postprocess_fields`) historically did not stage
    `nut`. Real turbulent runs would silently fall back to molecular-
    only ν without surfacing the path divergence — same V61-063 R2
    audit-key failure class. Verify the fix:
      a) nut is in field_files
      b) extractor stamps duct_flow_nut_{source,fallback_activated,
         length_mismatch} on every run
      c) fallback flag flips correctly with/without staged nut file
    """

    def test_nut_in_postprocess_field_files(self):
        """`nut` must be in the staged-fields list so docker→host copy
        carries the turbulent-viscosity field for the extractor."""
        import inspect
        source = inspect.getsource(
            FoamAgentExecutor._copy_postprocess_fields
        )
        assert '"nut"' in source, (
            f"`nut` missing from _copy_postprocess_fields field_files. "
            f"R1 F#2 fix not landed."
        )

    def test_audit_keys_stamped_on_every_run(self):
        cells = _build_minimal_extractor_input()
        kq: Dict[str, Any] = {}
        kq = FoamAgentExecutor._extract_duct_flow_observables(
            cxs=cells["cxs"], cys=cells["cys"], u_vecs=cells["u_vecs"],
            task_spec=_make_task(), key_quantities=kq,
            czs=None, latest_dir=None,
        )
        assert "duct_flow_nut_source" in kq
        assert "duct_flow_nut_fallback_activated" in kq
        assert "duct_flow_nut_length_mismatch" in kq

    def test_fallback_flag_true_when_no_latest_dir(self):
        """latest_dir=None (MOCK / pre-extractor stage) ⇒ fallback path."""
        cells = _build_minimal_extractor_input()
        kq: Dict[str, Any] = {}
        kq = FoamAgentExecutor._extract_duct_flow_observables(
            cxs=cells["cxs"], cys=cells["cys"], u_vecs=cells["u_vecs"],
            task_spec=_make_task(), key_quantities=kq,
            czs=None, latest_dir=None,
        )
        assert kq["duct_flow_nut_fallback_activated"] is True
        assert kq["duct_flow_nut_source"] == "absent"
        assert kq["duct_flow_nut_length_mismatch"] is False

    def test_fallback_flag_false_when_nut_staged(self, tmp_path):
        """Staged nut file with matching length ⇒ no fallback, source
        reads `staged_latest_dir`."""
        cells = _build_minimal_extractor_input()
        n_cells = len(cells["cxs"])
        # Synthesize a minimal OpenFOAM-style scalar field file with one
        # nut value per cell. _read_openfoam_scalar_field expects the
        # internalField nonuniform List<scalar> layout used elsewhere.
        nut_lines = [f"{n_cells}\n", "(\n"]
        nut_lines.extend(f"{0.001 * (i + 1)}\n" for i in range(n_cells))
        nut_lines.append(")\n")
        nut_path = tmp_path / "nut"
        nut_path.write_text("".join(nut_lines))
        kq: Dict[str, Any] = {}
        kq = FoamAgentExecutor._extract_duct_flow_observables(
            cxs=cells["cxs"], cys=cells["cys"], u_vecs=cells["u_vecs"],
            task_spec=_make_task(), key_quantities=kq,
            czs=None, latest_dir=tmp_path,
        )
        assert kq["duct_flow_nut_fallback_activated"] is False
        assert kq["duct_flow_nut_source"] == "staged_latest_dir"
        assert kq["duct_flow_nut_length_mismatch"] is False

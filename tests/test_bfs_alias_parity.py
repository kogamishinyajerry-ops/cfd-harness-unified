"""DEC-V61-067 Stage A.4: Execution → Evaluation plane alias parity.

Drives the gold-standard comparator end-to-end on the new BFS Type II
observables. Proves three contracts that no in-isolation A.1-A.3 test
could prove together:

  1. Adapter emit keys (``reattachment_length``, ``pressure_recovery``,
     ``velocity_profile_reattachment``, ``cd_mean``) match the gold YAML
     ``observables[].name`` field character-for-character.
  2. A Le/Moin/Kim-1997 + Driver-1985 anchor emit dict yields PASS at
     the configured tolerances — sanity-checks the YAML ref_value math.
  3. The actual extractor (``_extract_bfs_secondary_observables`` static
     method on ``FoamAgentExecutor``) produces all 3 new emit keys when
     given non-degenerate synthetic cell-centre + p-field + tau_x data.

V61-066 A.4 precedent: same triple-contract structure (parity / comparator
routing / extractor key surface).
"""

from __future__ import annotations

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
    / "backward_facing_step_steady.yaml"
)


def _make_task() -> TaskSpec:
    return TaskSpec(
        name="Backward-Facing Step",
        geometry_type=GeometryType.BACKWARD_FACING_STEP,
        flow_type=FlowType.INTERNAL,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.INCOMPRESSIBLE,
        Re=7600,
        boundary_conditions={"expansion_ratio": 1.125},
    )


def _build_anchor_perfect_emit() -> Dict[str, Any]:
    """Manually construct an emit dict at the Le/Moin/Kim + Driver anchors.

    Bypasses the cell-centred extractor to isolate the comparator-routing
    contract from the field-aggregation machinery (covered by 29 unit
    tests in test_bfs_extractors).
    """
    return {
        "reattachment_length": 6.26,            # Driver/Seegmiller 1985
        "pressure_recovery": {                  # Le/Moin/Kim 1997
            "inlet": -0.90,
            "outlet": 0.10,
            "delta": 1.00,
        },
        "velocity_profile_reattachment": [      # Le/Moin/Kim 1997 x/H=6
            {"x_H": 6.0, "y_H": 0.5, "u_Ubulk": 0.40},
            {"x_H": 6.0, "y_H": 1.0, "u_Ubulk": 0.85},
            {"x_H": 6.0, "y_H": 2.0, "u_Ubulk": 1.05},
        ],
        "cd_mean": 2.08,                        # legacy placeholder
        # Audit keys (not gated, but adapter emits them).
        "bfs_extractor_path": "wall_shear_v1+pressure_recovery_v1+velocity_profile_v1",
        "reattachment_method": "wall_shear_tau_x_zero_crossing",
    }


def _build_minimal_extractor_input() -> Dict[str, Any]:
    """Build minimal cell + p + tau_x synthetic data sufficient to produce
    all 3 V61-067 secondary emit keys.

    Layout matches the V61-052 BFS canonical mesh (3-block with step at
    x=0, channel y∈[0, 9·H], H=1, L_up=10·H, L_down=30·H):

      - inlet column at x=-9.5 (nearest cell to x=-10): 4 cells at y=
        {0.5, 1.0, 4.0, 7.0}, all with p=-0.45 (synthetic so Cp_inlet=-0.9)
      - outlet column at x=29.5: 4 cells at same y, all with p=0.05
        (so Cp_outlet=0.10, delta=1.00)
      - x=6.0 column for velocity_profile: 3 cells at y={0.5, 1.0, 2.0}
        with u_x = {0.40, 0.85, 1.05}
      - downstream-floor tau_x samples at y≈0, x∈{1, 5, 10, 20}: τ_x=0.005
    """
    cells_xyz_u: List[Tuple[float, float, Tuple[float, float, float]]] = []
    cells_p: List[float] = []

    # Inlet column at x=-9.5, p=-0.45 → Cp=-0.9
    for y in [0.5, 1.0, 4.0, 7.0]:
        cells_xyz_u.append((-9.5, y, (1.0, 0.0, 0.0)))
        cells_p.append(-0.45)

    # Outlet column at x=29.5, p=0.05 → Cp=+0.1
    for y in [0.5, 1.0, 4.0, 7.0]:
        cells_xyz_u.append((29.5, y, (1.0, 0.0, 0.0)))
        cells_p.append(0.05)

    # x=6.0 column for velocity_profile (Le/Moin/Kim anchor)
    for y, u in [(0.5, 0.40), (1.0, 0.85), (2.0, 1.05)]:
        cells_xyz_u.append((6.0, y, (u, 0.0, 0.0)))
        cells_p.append(0.0)

    cxs = [c[0] for c in cells_xyz_u]
    cys = [c[1] for c in cells_xyz_u]
    u_vecs = [c[2] for c in cells_xyz_u]

    # Downstream floor tau_x: 4 samples at y≈0, x>0 (post-step floor)
    tau_pts: List[Tuple[float, float, float]] = [
        (1.0, 0.0, 0.0),
        (5.0, 0.0, 0.0),
        (10.0, 0.0, 0.0),
        (20.0, 0.0, 0.0),
    ]
    tau_x: List[float] = [-0.003, 0.005, 0.005, 0.005]  # mixed-sign realism

    return {
        "cxs": cxs,
        "cys": cys,
        "u_vecs": u_vecs,
        "p_vals": cells_p,
        "tau_x": tau_x,
        "tau_pts": tau_pts,
    }


@pytest.fixture(scope="module")
def gold_yaml() -> Dict[str, Any]:
    return yaml.safe_load(GOLD_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def anchor_emit() -> Dict[str, Any]:
    return _build_anchor_perfect_emit()


class TestAliasParityKeys:
    """Names emitted by adapter must match names in gold YAML observables."""

    def test_every_gold_observable_name_appears_in_emit(
        self, gold_yaml: Dict[str, Any], anchor_emit: Dict[str, Any],
    ):
        gold_names = {o["name"] for o in gold_yaml["observables"]}
        emit_keys = set(anchor_emit.keys())
        missing = gold_names - emit_keys
        assert not missing, (
            f"Gold observables not produced by anchor emit: {missing}. "
            f"Emit keys: {sorted(emit_keys)}"
        )

    def test_all_a3_secondary_observables_present_in_gold(
        self, gold_yaml: Dict[str, Any]
    ):
        names = {o["name"] for o in gold_yaml["observables"]}
        assert "pressure_recovery" in names
        assert "velocity_profile_reattachment" in names
        assert "cd_mean" in names

    def test_back_compat_reattachment_length_still_present(
        self, gold_yaml: Dict[str, Any]
    ):
        names = {o["name"] for o in gold_yaml["observables"]}
        assert "reattachment_length" in names

    def test_extractor_paths_match_a1_module(
        self, gold_yaml: Dict[str, Any]
    ):
        """Each gold observable's `extractor` field must reference a real
        function in src.bfs_extractors (or the existing
        _extract_bfs_reattachment for the HEADLINE)."""
        from src import bfs_extractors as bfse
        for obs in gold_yaml["observables"]:
            extractor_path = obs.get("extractor", "")
            if not extractor_path.startswith("src.bfs_extractors."):
                continue  # HEADLINE points to foam_agent_adapter
            func_name = extractor_path.split(".")[-1]
            assert hasattr(bfse, func_name), (
                f"Gold observable '{obs['name']}' references "
                f"{extractor_path} but {func_name} not exported"
            )

    def test_cd_mean_is_provisional_advisory(self, gold_yaml: Dict[str, Any]):
        cd_obs = next(
            o for o in gold_yaml["observables"] if o["name"] == "cd_mean"
        )
        assert cd_obs["gate_status"] == "PROVISIONAL_ADVISORY", (
            f"R1 F#3-style downgrade not landed: cd_mean still "
            f"gate_status={cd_obs['gate_status']}"
        )
        assert "advisory_rationale" in cd_obs

    def test_three_observables_remain_hard_gated(
        self, gold_yaml: Dict[str, Any]
    ):
        hard_gated = {
            o["name"] for o in gold_yaml["observables"]
            if o.get("gate_status") == "HARD_GATED"
        }
        assert hard_gated == {
            "reattachment_length",
            "pressure_recovery",
            "velocity_profile_reattachment",
        }, f"Unexpected HARD_GATED set: {hard_gated}"


class TestComparatorRoutingOnAnchorEmit:
    """Drive GoldStandardComparator on a Le/Moin/Kim + Driver anchor emit."""

    def test_anchor_perfect_emit_passes_overall(
        self, gold_yaml: Dict[str, Any], anchor_emit: Dict[str, Any],
    ):
        report = GoldStandardComparator().compare(gold_yaml, anchor_emit)
        assert report.overall == "PASS", (
            f"Expected PASS on anchor-perfect emit; got {report.overall}. "
            f"Per-observable verdicts: "
            f"{[(c.name, c.within_tolerance, c.rel_error) for c in report.observables]}"
        )

    def test_each_hard_gated_observable_within_tolerance(
        self, gold_yaml: Dict[str, Any], anchor_emit: Dict[str, Any],
    ):
        report = GoldStandardComparator().compare(gold_yaml, anchor_emit)
        outside = [
            (c.name, c.rel_error, c.abs_error)
            for c in report.observables
            if not c.within_tolerance and c.gate_status != "PROVISIONAL_ADVISORY"
        ]
        assert not outside, f"HARD_GATED observables outside tolerance: {outside}"

    def test_pressure_recovery_routes_through_dict_branch(
        self, gold_yaml: Dict[str, Any], anchor_emit: Dict[str, Any],
    ):
        """ref_value is a dict {inlet, outlet, delta}; sim_value should be
        the same shape. Comparator should route through the dict-mapping
        branch (not scalar)."""
        report = GoldStandardComparator().compare(gold_yaml, anchor_emit)
        check = next(
            c for c in report.observables if c.name == "pressure_recovery"
        )
        assert check.within_tolerance is True
        # Comparator may store sim_value as the dict or as a per-key
        # comparison artefact — just verify the verdict is PASS.
        assert isinstance(check.ref_value, dict)

    def test_velocity_profile_routes_through_list_branch(
        self, gold_yaml: Dict[str, Any], anchor_emit: Dict[str, Any],
    ):
        report = GoldStandardComparator().compare(gold_yaml, anchor_emit)
        check = next(
            c for c in report.observables
            if c.name == "velocity_profile_reattachment"
        )
        assert check.within_tolerance is True
        assert isinstance(check.ref_value, list)


class TestExtractorEmitKeySurface:
    """Verify _extract_bfs_secondary_observables produces all 3 new emit
    keys when fed non-degenerate synthetic cell + p + tau_x data."""

    def test_extractor_emits_all_three_observables(self):
        d = _build_minimal_extractor_input()
        kq: Dict[str, Any] = {}
        kq = FoamAgentExecutor._extract_bfs_secondary_observables(
            cxs=d["cxs"], cys=d["cys"], u_vecs=d["u_vecs"],
            task_spec=_make_task(), key_quantities=kq,
            p_vals=d["p_vals"],
            tau_x=d["tau_x"], tau_pts=d["tau_pts"],
        )
        assert "pressure_recovery" in kq, f"Got keys: {sorted(kq.keys())}"
        assert "velocity_profile_reattachment" in kq
        assert "cd_mean" in kq

    def test_extractor_audit_path_stamped(self):
        d = _build_minimal_extractor_input()
        kq: Dict[str, Any] = {}
        kq = FoamAgentExecutor._extract_bfs_secondary_observables(
            cxs=d["cxs"], cys=d["cys"], u_vecs=d["u_vecs"],
            task_spec=_make_task(), key_quantities=kq,
            p_vals=d["p_vals"],
            tau_x=d["tau_x"], tau_pts=d["tau_pts"],
        )
        assert kq.get("bfs_extractor_path") == (
            "wall_shear_v1+pressure_recovery_v1+velocity_profile_v1"
        )
        assert kq.get("bfs_velocity_profile_n_points") == 3
        assert kq.get("bfs_cd_n_floor_samples") == 4

    def test_extractor_recovers_anchor_values_from_synthetic(self):
        """End-to-end: synthetic Le/Moin/Kim-consistent cells produce
        extractor outputs that match the gold ref_values."""
        d = _build_minimal_extractor_input()
        kq: Dict[str, Any] = {}
        kq = FoamAgentExecutor._extract_bfs_secondary_observables(
            cxs=d["cxs"], cys=d["cys"], u_vecs=d["u_vecs"],
            task_spec=_make_task(), key_quantities=kq,
            p_vals=d["p_vals"],
            tau_x=d["tau_x"], tau_pts=d["tau_pts"],
        )
        # pressure_recovery: synthetic p_in=-0.45, p_out=0.05, U_bulk=1, ρ=1
        # → Cp_in=-0.9, Cp_out=0.1, delta=1.0
        cp = kq["pressure_recovery"]
        assert cp["inlet"] == pytest.approx(-0.90, rel=1e-9)
        assert cp["outlet"] == pytest.approx(0.10, rel=1e-9)
        assert cp["delta"] == pytest.approx(1.00, rel=1e-9)
        # velocity_profile: 3 entries, each matches Le/Moin/Kim x/H=6 anchor
        prof = kq["velocity_profile_reattachment"]
        assert len(prof) == 3
        assert prof[0]["x_H"] == pytest.approx(6.0)
        assert prof[0]["y_H"] == pytest.approx(0.5)
        assert prof[0]["u_Ubulk"] == pytest.approx(0.40)
        assert prof[1]["u_Ubulk"] == pytest.approx(0.85)
        assert prof[2]["u_Ubulk"] == pytest.approx(1.05)
        # cd_mean: |τ_x| mean = (0.003 + 0.005·3) / 4 = 0.0045
        # cd = 0.0045 / (0.5·1·1²) = 0.009
        assert kq["cd_mean"] == pytest.approx(0.009, rel=1e-9)

    def test_extractor_folds_p_field_missing_into_audit_key(self):
        """p_vals=None ⇒ pressure_recovery_error stamped, observable absent."""
        d = _build_minimal_extractor_input()
        kq: Dict[str, Any] = {}
        kq = FoamAgentExecutor._extract_bfs_secondary_observables(
            cxs=d["cxs"], cys=d["cys"], u_vecs=d["u_vecs"],
            task_spec=_make_task(), key_quantities=kq,
            p_vals=None,  # missing
            tau_x=d["tau_x"], tau_pts=d["tau_pts"],
        )
        assert "pressure_recovery" not in kq
        assert kq.get("pressure_recovery_error") == "p_field_missing"
        # Other observables should still emit.
        assert "velocity_profile_reattachment" in kq
        assert "cd_mean" in kq

    def test_extractor_folds_tau_x_missing_into_audit_key(self):
        """tau_x=None ⇒ cd_mean_error stamped."""
        d = _build_minimal_extractor_input()
        kq: Dict[str, Any] = {}
        kq = FoamAgentExecutor._extract_bfs_secondary_observables(
            cxs=d["cxs"], cys=d["cys"], u_vecs=d["u_vecs"],
            task_spec=_make_task(), key_quantities=kq,
            p_vals=d["p_vals"],
            tau_x=None, tau_pts=None,
        )
        assert "cd_mean" not in kq
        assert kq.get("cd_mean_error") == "tau_x_field_missing"
        # Other observables should still emit.
        assert "pressure_recovery" in kq
        assert "velocity_profile_reattachment" in kq

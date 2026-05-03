"""DEC-V61-116 · case_completeness analyzer + route tests.

Three-layer coverage matrix:
    1. Whitelist case → full gold contract → high present/total ratio
    2. Imported user STL case → minimal contract (solver+turbulence+bc)
    3. Case with no gold standard → manifest-only checks + notes

Plus targeted rule checks:
    - Re-appropriate turbulence (laminar @ Re=15000 → critical)
    - Tri-state precondition preservation (false → critical, "partial" → warning)
    - 404 path on unknown case_id
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from ui.backend.main import app
from ui.backend.services import case_completeness, case_drafts, validation_report
from ui.backend.services.case_completeness import (
    CaseCompletenessReport,
    CaseNotFoundError,
    analyze_case_completeness,
)
from ui.backend.services.case_completeness.analyzer import (
    _check_gold_contract,
    _check_re_appropriate_turbulence,
    _check_whitelist_or_draft,
)
from ui.backend.services.case_scaffold import template_clone


client = TestClient(app)


# ---------------------------------------------------------------------------
# Layer 1 — whitelist case happy path
# ---------------------------------------------------------------------------


def test_whitelist_lid_driven_cavity_high_completeness(isolated_for_whitelist):
    """LDC has a fully-vetted gold contract; expected high ratio + most
    preconditions satisfied. The single critical we tolerate is precondition
    #6 (BL/BR vortex resolution) which is a known limitation, not a regression.
    """
    r = analyze_case_completeness("lid_driven_cavity")
    assert isinstance(r, CaseCompletenessReport)
    assert r.case_id == "lid_driven_cavity"
    assert r.case_kind == "whitelist"
    # Total = 7 critical (top-level) + 1 warning (parameters) + N preconds
    assert r.total_count >= 8
    assert r.percentage >= 80.0  # ≥80% completeness
    # No top-level field missing (it's a vetted whitelist case)
    top_level_missing = [
        m for m in r.missing if not m.field_path.startswith("physics_contract")
    ]
    assert top_level_missing == [], (
        "whitelist case should have all top-level fields present; "
        f"unexpected missing: {top_level_missing}"
    )


def test_whitelist_backward_facing_step_bc_demoted_to_warning(isolated_for_whitelist):
    """BACKWARD_FACING_STEP geometry inherits canonical BCs from the adapter
    scaffold; the missing `boundary_conditions:` block should be a warning,
    NOT a critical. Otherwise every adapter-driven whitelist case would be
    falsely blocked from archive.
    """
    r = analyze_case_completeness("backward_facing_step")
    bc_entries = [m for m in r.missing if m.field_path == "boundary_conditions"]
    assert len(bc_entries) == 1
    assert bc_entries[0].severity == "warning", (
        "BFS uses adapter-inferred BCs; missing block must be warning, not critical"
    )


# ---------------------------------------------------------------------------
# Layer 2 — imported user case (v2 manifest)
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_drafts(tmp_path: Path, monkeypatch):
    """Redirect IMPORTED_DIR + DRAFTS_DIR (analyzer's references) to tmp.

    The analyzer imports the constants at module load, so monkeypatching
    the source modules alone is insufficient — must patch the analyzer's
    own module-level names too.
    """
    drafts = tmp_path / "user_drafts"
    imported = drafts / "imported"
    drafts.mkdir(parents=True, exist_ok=True)
    imported.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(template_clone, "DRAFTS_DIR", drafts)
    monkeypatch.setattr(template_clone, "IMPORTED_DIR", imported)
    monkeypatch.setattr(case_drafts, "DRAFTS_DIR", drafts)
    monkeypatch.setattr(validation_report, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(case_completeness.analyzer, "IMPORTED_DIR", imported)
    monkeypatch.setattr(case_completeness.analyzer, "DRAFTS_DIR", drafts)
    return drafts, imported


@pytest.fixture
def isolated_for_whitelist(tmp_path: Path, monkeypatch):
    """For whitelist tests — point DRAFTS_DIR + IMPORTED_DIR away from the
    real user_drafts/ tree so the resolver doesn't pick up a stray draft
    that would shadow the whitelist entry under analysis.
    """
    fake_drafts = tmp_path / "empty_drafts"
    fake_imported = fake_drafts / "imported"
    fake_drafts.mkdir(parents=True, exist_ok=True)
    fake_imported.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(case_completeness.analyzer, "IMPORTED_DIR", fake_imported)
    monkeypatch.setattr(case_completeness.analyzer, "DRAFTS_DIR", fake_drafts)
    return fake_drafts


def _seed_imported_manifest(
    imported_dir: Path,
    case_id: str,
    *,
    solver: str | None = "simpleFoam",
    turbulence_model: str | None = "laminar",
    has_patches: bool = True,
) -> None:
    """Write a minimal v2 case_manifest.yaml under imported_dir/case_id/."""
    case_dir = imported_dir / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict = {
        "schema_version": 2,
        "case_id": case_id,
        "physics": {
            "solver": solver,
            "turbulence_model": turbulence_model,
            "end_time": 100.0,
            "delta_t": 1.0,
            "write_interval": 50,
        },
        "bc": {
            "patches": (
                {"inlet": {"patch_type": "patch", "fields": {}}}
                if has_patches
                else {}
            )
        },
        "numerics": {},
        "overrides": {},
        "history": [],
    }
    (case_dir / "case_manifest.yaml").write_text(
        yaml.safe_dump(manifest), encoding="utf-8"
    )


def test_imported_case_full_minimal_contract(isolated_drafts):
    """Imported case with all 3 minimal fields → 3/3, ready_for_archive=True."""
    _, imported = isolated_drafts
    case_id = "imported_2026-05-04T00-00-00Z_test001"
    _seed_imported_manifest(imported, case_id)
    r = analyze_case_completeness(case_id)
    assert r.case_kind == "imported_user"
    assert r.ready_for_archive is True
    assert r.blocked_by_critical == 0
    assert r.percentage == 100.0
    assert r.total_count == 3  # solver + turbulence + bc.patches


def test_imported_case_missing_solver_blocks_archive(isolated_drafts):
    """Imported case missing the solver → critical missing → not ready."""
    _, imported = isolated_drafts
    case_id = "imported_2026-05-04T00-00-00Z_test002"
    _seed_imported_manifest(imported, case_id, solver=None)
    r = analyze_case_completeness(case_id)
    assert r.ready_for_archive is False
    assert r.blocked_by_critical >= 1
    assert any(m.field_path == "physics.solver" for m in r.missing)


def test_imported_case_missing_patches_blocks_archive(isolated_drafts):
    """Imported case with empty bc.patches → critical missing."""
    _, imported = isolated_drafts
    case_id = "imported_2026-05-04T00-00-00Z_test003"
    _seed_imported_manifest(imported, case_id, has_patches=False)
    r = analyze_case_completeness(case_id)
    assert r.ready_for_archive is False
    assert any(m.field_path == "bc.patches" for m in r.missing)


def test_imported_case_with_unset_turbulence_in_yaml_flagged_despite_default(
    isolated_drafts,
):
    """Codex R1 P2 #1 regression — DEC-V61-116.

    `read_case_manifest()` migrates a manifest that omits
    `physics.turbulence_model` to the schema default `'laminar'`. A
    truthiness check on the migrated Pydantic instance would silently
    pass, undercounting critical gaps. The analyzer now reads the raw
    YAML so a YAML missing the field gets flagged regardless of what
    Pydantic's default-fill produced.
    """
    _, imported = isolated_drafts
    case_id = "imported_2026-05-04T00-00-00Z_unset_turb"
    case_dir = imported / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    # Note: no `turbulence_model` under `physics`. Schema default would
    # fill `'laminar'` post-migration.
    (case_dir / "case_manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 2,
                "case_id": case_id,
                "physics": {
                    "solver": "simpleFoam",
                    "end_time": 100.0,
                },
                "bc": {"patches": {"inlet": {"patch_type": "patch", "fields": {}}}},
                "numerics": {},
                "overrides": {},
                "history": [],
            }
        ),
        encoding="utf-8",
    )
    r = analyze_case_completeness(case_id)
    assert r.ready_for_archive is False, (
        "unset turbulence_model in YAML must be flagged even though "
        "Pydantic schema default fills 'laminar' post-migration"
    )
    assert any(
        m.field_path == "physics.turbulence_model" and m.severity == "critical"
        for m in r.missing
    )


def test_flat_draft_wins_over_imported_manifest(isolated_drafts):
    """Codex R1 P1 regression — DEC-V61-116.

    For an imported case the editor saves to `user_drafts/{id}.yaml`
    (flat draft) regardless of the import-time
    `imported/{id}/case_manifest.yaml` snapshot. The analyzer must
    surface the flat draft's state, not the stale manifest, so the
    right-rail card reflects the engineer's current edits.
    """
    drafts, imported = isolated_drafts
    case_id = "imported_2026-05-04T00-00-00Z_flat_wins"
    # Stale import-time manifest: complete (would report ready=True).
    _seed_imported_manifest(imported, case_id)
    # Engineer's edited flat draft: missing turbulence_model + BC →
    # would be incomplete on the flat-draft schema.
    (drafts / f"{case_id}.yaml").write_text(
        yaml.safe_dump(
            {
                "id": case_id,
                "name": "Edited",
                "flow_type": "INTERNAL",
                "geometry_type": "CUSTOM",
                # turbulence_model + solver intentionally absent
            }
        ),
        encoding="utf-8",
    )
    r = analyze_case_completeness(case_id)
    # Resolution priority: flat draft wins → case_kind = "draft"
    assert r.case_kind == "draft", (
        "flat draft must take resolution priority over imported manifest"
    )
    # The flat draft's missing turbulence_model must surface in the report.
    assert any(
        m.field_path == "turbulence_model" and m.severity == "critical"
        for m in r.missing
    )


def test_re_rule_contributes_to_total_count(isolated_for_whitelist):
    """Codex R1 P2 #2 regression — DEC-V61-116.

    When `parameters.Re` is present, `_check_re_appropriate_turbulence`
    runs and (if it flags) appends to `missing`. The denominator must
    likewise include the Re-rule slot, otherwise present_count + missing
    can't reconstruct total. Earlier draft hard-coded denominator at 8 +
    gold preconds even when the rule fired, producing 14/15 instead of
    14/16 on Re-based cases.

    Verify by analyzing lid_driven_cavity (Re=100, laminar — rule
    doesn't flag) and confirming total_count includes the slot.
    """
    r = analyze_case_completeness("lid_driven_cavity")
    # Top-level critical (7) + parameters (1) + Re-rule (1, gated on Re
    # presence) + N gold preconditions. lid_driven_cavity has Re=100 in
    # parameters, so the +1 must apply.
    assert r.total_count >= 9, (
        f"total_count must include the Re-rule slot when parameters.Re is "
        f"present; got {r.total_count}"
    )


def test_solver_dict_shape_normalized(isolated_drafts):
    """Imported flat drafts may store solver as a dict {name: X}; the
    whitelist-like analyzer normalizes that to the string form before
    truthiness checks so engineer-edited imported cases don't trigger a
    false-critical "solver missing".
    """
    drafts, _ = isolated_drafts
    case_id = "imported_2026-05-04T00-00-00Z_dict_solver"
    (drafts / f"{case_id}.yaml").write_text(
        yaml.safe_dump(
            {
                "id": case_id,
                "name": "Imported · cylinder.stl",
                "flow_type": "INTERNAL",
                "geometry_type": "CUSTOM",
                "turbulence_model": "laminar",
                "solver": {"name": "simpleFoam", "family": "incompressible"},
            }
        ),
        encoding="utf-8",
    )
    r = analyze_case_completeness(case_id)
    # solver should NOT be in critical missing — the dict-shape was
    # normalized to its name string.
    assert not any(
        m.field_path == "solver" and m.severity == "critical" for m in r.missing
    ), f"solver dict shape not normalized; missing = {r.missing}"


# ---------------------------------------------------------------------------
# Layer 3 — Re-appropriate turbulence rule (unit-level)
# ---------------------------------------------------------------------------


def test_re_appropriate_turbulence_laminar_below_ceiling_no_flag():
    out = _check_re_appropriate_turbulence(
        turbulence_model="laminar", re_value=100.0
    )
    assert out == []


def test_re_appropriate_turbulence_laminar_above_ceiling_flagged():
    """Laminar at Re=15000 must be flagged critical with kOmegaSST suggestion."""
    out = _check_re_appropriate_turbulence(
        turbulence_model="laminar", re_value=15000.0
    )
    assert len(out) == 1
    assert out[0].severity == "critical"
    assert out[0].field_path == "turbulence_model"
    assert out[0].suggested_default == "kOmegaSST"


def test_re_appropriate_turbulence_kepsilon_above_ceiling_no_flag():
    """kEpsilon at high Re is fine — only laminar gets flagged."""
    out = _check_re_appropriate_turbulence(
        turbulence_model="kEpsilon", re_value=15000.0
    )
    assert out == []


def test_re_appropriate_turbulence_no_re_no_flag():
    """No Re available → no flag (geometry-only imported case path)."""
    out = _check_re_appropriate_turbulence(
        turbulence_model="laminar", re_value=None
    )
    assert out == []


# ---------------------------------------------------------------------------
# Layer 4 — gold-contract tri-state preservation (DEC-V61-046)
# ---------------------------------------------------------------------------


def test_gold_contract_tri_state_false_critical_partial_warning_none_info():
    """Mirror DEC-V61-046 tri-state semantics: never bool-coerce 'partial'."""
    gold = {
        "physics_contract": {
            "physics_precondition": [
                {
                    "condition": "Mesh resolved",
                    "satisfied_by_current_adapter": True,
                },
                {
                    "condition": "Re below transition",
                    "satisfied_by_current_adapter": False,
                    "evidence_ref": "Re=15000 > 2300",
                },
                {
                    "condition": "Wall function close to standard",
                    "satisfied_by_current_adapter": "partial",
                    "evidence_ref": "kEpsilon instead of v2f",
                },
                {
                    "condition": "Inflow profile from DNS",
                    # Missing satisfied_by_current_adapter → info-tier
                },
            ]
        }
    }
    out = _check_gold_contract(gold)
    severities = [m.severity for m in out]
    # 1 false → critical, 1 "partial" → warning, 1 missing → info
    assert severities.count("critical") == 1
    assert severities.count("warning") == 1
    assert severities.count("info") == 1
    # 'true' precondition should NOT appear
    assert len(out) == 3


def test_gold_contract_no_physics_contract_yields_empty():
    """Cases with no physics_contract block return [], not crash."""
    assert _check_gold_contract({}) == []
    assert _check_gold_contract({"physics_contract": "not a dict"}) == []
    assert _check_gold_contract({"physics_contract": {}}) == []


# ---------------------------------------------------------------------------
# Layer 5 — manifest-equivalent checks for whitelist/draft
# ---------------------------------------------------------------------------


def test_check_whitelist_or_draft_complete_yields_only_warning_or_empty():
    """A complete whitelist-style dict produces no critical missings."""
    raw = {
        "id": "test_case",
        "name": "Test",
        "flow_type": "INTERNAL",
        "geometry_type": "SIMPLE_GRID",
        "solver": "simpleFoam",
        "turbulence_model": "laminar",
        "parameters": {"Re": 100},
        "boundary_conditions": {"top_wall_u": 1.0},
    }
    out = _check_whitelist_or_draft(raw)
    crit = [m for m in out if m.severity == "critical"]
    assert crit == []


def test_check_whitelist_or_draft_simple_grid_missing_bc_is_critical():
    """SIMPLE_GRID without boundary_conditions → critical."""
    raw = {
        "id": "x",
        "name": "X",
        "flow_type": "INTERNAL",
        "geometry_type": "SIMPLE_GRID",
        "solver": "icoFoam",
        "turbulence_model": "laminar",
        "parameters": {"Re": 100},
    }
    out = _check_whitelist_or_draft(raw)
    bc_entries = [m for m in out if m.field_path == "boundary_conditions"]
    assert bc_entries[0].severity == "critical"


# ---------------------------------------------------------------------------
# Layer 6 — public entry point + 404
# ---------------------------------------------------------------------------


def test_analyze_unknown_case_id_raises():
    with pytest.raises(CaseNotFoundError):
        analyze_case_completeness("does_not_exist_anywhere_2026")


def test_analyze_empty_case_id_raises():
    with pytest.raises(CaseNotFoundError):
        analyze_case_completeness("")


# ---------------------------------------------------------------------------
# Layer 7 — HTTP route integration
# ---------------------------------------------------------------------------


def test_route_returns_200_for_whitelist_case(isolated_for_whitelist):
    """GET /api/cases/lid_driven_cavity/completeness → 200 with payload."""
    r = client.get("/api/cases/lid_driven_cavity/completeness")
    assert r.status_code == 200
    body = r.json()
    assert body["case_id"] == "lid_driven_cavity"
    assert body["case_kind"] == "whitelist"
    assert "ready_for_archive" in body
    assert "missing" in body
    assert "percentage" in body


def test_route_404_for_unknown_case():
    r = client.get("/api/cases/__totally_nonexistent__/completeness")
    assert r.status_code == 404
    assert "case_id not found" in r.json()["detail"]


def test_route_returns_payload_shape(isolated_for_whitelist):
    """Validate every documented top-level key is present + typed."""
    r = client.get("/api/cases/lid_driven_cavity/completeness")
    body = r.json()
    for key in (
        "case_id",
        "case_kind",
        "ready_for_archive",
        "blocked_by_critical",
        "present_count",
        "total_count",
        "percentage",
        "missing",
        "notes",
    ):
        assert key in body, f"missing key: {key}"
    assert isinstance(body["missing"], list)
    assert isinstance(body["notes"], list)
    assert 0 <= body["percentage"] <= 100

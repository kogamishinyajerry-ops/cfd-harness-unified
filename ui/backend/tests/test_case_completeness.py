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
    """Imported case with all 3 minimal fields → 4/4, ready_for_archive=True.

    Total of 4 = 3 base critical (solver, turbulence, bc.patches) + 1
    manifest_schema_invalid slot (counts as present when manifest passes
    Pydantic validation).
    """
    _, imported = isolated_drafts
    case_id = "imported_2026-05-04T00-00-00Z_test001"
    _seed_imported_manifest(imported, case_id)
    r = analyze_case_completeness(case_id)
    assert r.case_kind == "imported_user"
    assert r.ready_for_archive is True
    assert r.blocked_by_critical == 0
    assert r.percentage == 100.0
    assert r.total_count == 4  # 3 base + manifest schema validity slot


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


def test_imported_merged_flat_supplies_solver_and_turbulence(isolated_drafts):
    """Codex R4 P1 fix · R5 merge — DEC-V61-116.

    Scaffolded manifest has empty physics + bc sections. Engineer
    later edits flat YAML to set solver + turbulence_model via the
    editor. The merged analyzer must count those as present from
    the flat draft.

    Note: flat-draft `boundary_conditions` does NOT satisfy bc.patches
    (Codex R5 P1 — only manifest patch setup counts), so this test
    seeds bc.patches in the manifest separately.
    """
    drafts, imported = isolated_drafts
    case_id = "imported_2026-05-04T00-00-00Z_merge_flat"

    # Scaffold-state manifest: empty physics; bc.patches populated by
    # setup_bc (post-scaffold). physics still empty because engineer
    # hasn't run switch_solver.
    case_dir = imported / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "case_manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 2,
                "case_id": case_id,
                "physics": {},
                "bc": {
                    "patches": {
                        "inlet": {"patch_type": "patch", "fields": {}}
                    }
                },
                "numerics": {},
                "overrides": {},
                "history": [],
            }
        ),
        encoding="utf-8",
    )

    # Flat draft: engineer edited solver + turbulence via editor.
    (drafts / f"{case_id}.yaml").write_text(
        yaml.safe_dump(
            {
                "id": case_id,
                "name": "Imported · cylinder.stl",
                "flow_type": "INTERNAL",
                "geometry_type": "CUSTOM",
                "turbulence_model": "kOmegaSST",
                "solver": {"name": "simpleFoam", "family": "incompressible"},
            }
        ),
        encoding="utf-8",
    )

    r = analyze_case_completeness(case_id)
    assert r.case_kind == "imported_user", (
        f"imported_dir presence keeps imported analysis path; got {r.case_kind}"
    )
    # Solver + turbulence sourced from flat → not missing.
    # bc.patches sourced from manifest → not missing.
    flat_or_manifest_supplied = {
        "physics.solver",
        "physics.turbulence_model",
        "bc.patches",
    }
    actually_missing = {m.field_path for m in r.missing}
    overlap = flat_or_manifest_supplied & actually_missing
    assert overlap == set(), (
        f"merged analyzer must count source-supplied fields as present; "
        f"unexpectedly missing = {overlap}"
    )
    assert r.ready_for_archive is True


def test_imported_merged_manifest_supplies_bc_patches(isolated_drafts):
    """Codex R4 P1 fix · R5 merge — DEC-V61-116.

    setup_bc_from_stl_patches() populates manifest.bc.patches but does
    NOT touch the flat draft's `boundary_conditions` block. The merged
    analyzer must count bc as present (sourced from manifest) even if
    flat draft has no boundary_conditions key.
    """
    drafts, imported = isolated_drafts
    case_id = "imported_2026-05-04T00-00-00Z_merge_manifest_bc"

    # Manifest: setup_bc has run → bc.patches populated. physics still
    # has scaffold-time defaults (engineer hasn't switched solver).
    _seed_imported_manifest(imported, case_id)  # has solver + turbulence + 1 patch

    # Flat draft: scaffolded with no boundary_conditions block.
    (drafts / f"{case_id}.yaml").write_text(
        yaml.safe_dump(
            {
                "id": case_id,
                "name": "Imported",
                "flow_type": "INTERNAL",
                "geometry_type": "CUSTOM",
                # turbulence_model + solver in flat too (but manifest
                # also has them; either source counts).
                "turbulence_model": "laminar",
                "solver": {"name": "simpleFoam"},
                # boundary_conditions intentionally absent in flat.
            }
        ),
        encoding="utf-8",
    )

    r = analyze_case_completeness(case_id)
    bc_missing = [m for m in r.missing if m.field_path == "bc.patches"]
    assert bc_missing == [], (
        f"manifest-supplied bc.patches must not be flagged missing; "
        f"got {bc_missing}"
    )


def test_imported_flat_boundary_conditions_does_not_satisfy_bc_patches(
    isolated_drafts,
):
    """Codex R5 P1 regression — DEC-V61-116.

    Flat-draft `boundary_conditions` is the editor's per-patch VALUES
    block (e.g. `top_wall_u: 1.0`); it does NOT register patches with
    OpenFOAM. Only `manifest.bc.patches` (set by setup_bc /
    face-annotation) counts. Earlier R4 merge accepted flat
    `boundary_conditions` as equivalent — that was wrong.
    """
    drafts, imported = isolated_drafts
    case_id = "imported_2026-05-04T00-00-00Z_flat_bc_only"
    case_dir = imported / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    # Manifest: scaffold state, NO bc.patches (setup_bc hasn't run).
    (case_dir / "case_manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 2,
                "case_id": case_id,
                "physics": {"solver": "simpleFoam", "turbulence_model": "laminar"},
                "bc": {"patches": {}},  # ← empty
                "numerics": {},
                "overrides": {},
                "history": [],
            }
        ),
        encoding="utf-8",
    )
    # Flat draft: engineer typed boundary_conditions VALUES but
    # didn't run setup_bc.
    (drafts / f"{case_id}.yaml").write_text(
        yaml.safe_dump(
            {
                "id": case_id,
                "name": "Imported",
                "turbulence_model": "laminar",
                "solver": {"name": "simpleFoam"},
                "boundary_conditions": {"inlet_u": 1.0, "outlet_p": 0.0},
            }
        ),
        encoding="utf-8",
    )
    r = analyze_case_completeness(case_id)
    bc_missing = [m for m in r.missing if m.field_path == "bc.patches"]
    assert len(bc_missing) == 1, (
        f"flat boundary_conditions must NOT satisfy bc.patches contract; "
        f"got missing = {[m.field_path for m in r.missing]}"
    )
    assert r.ready_for_archive is False


def _seed_minimal_imported_for_bc_check(
    imported_dir: Path, case_id: str
) -> Path:
    """Helper: write a minimal valid manifest with solver+turbulence set.
    Returns case_dir. Used by BC-mtime tests below.
    """
    case_dir = imported_dir / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "case_manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 2,
                "case_id": case_id,
                "physics": {
                    "solver": "simpleFoam",
                    "turbulence_model": "kOmegaSST",
                },
                "bc": {"patches": {}},
                "numerics": {},
                "overrides": {"raw_dict_files": {}},
                "history": [],
            }
        ),
        encoding="utf-8",
    )
    return case_dir


def _write_polymesh_points(case_dir: Path, mtime: float) -> Path:
    """Helper: create constant/polyMesh/points at given mtime.

    Codex R8 P1: the analyzer compares 0/X mtimes against polyMesh
    `points` (mesh geometry), NOT polyMesh `boundary` (BC setup
    rewrites boundary to change patch types).
    """
    import os

    poly_dir = case_dir / "constant" / "polyMesh"
    poly_dir.mkdir(parents=True, exist_ok=True)
    points = poly_dir / "points"
    points.write_text("// gmshToFoam-generated points\n", encoding="utf-8")
    os.utime(points, (mtime, mtime))
    return points


def _write_polymesh_boundary(case_dir: Path, mtime: float) -> Path:
    """Helper: create constant/polyMesh/boundary at given mtime.

    Used by tests that simulate setup_bc rewriting boundary AFTER
    setup; the analyzer should ignore this file's mtime.
    """
    import os

    poly_dir = case_dir / "constant" / "polyMesh"
    poly_dir.mkdir(parents=True, exist_ok=True)
    boundary = poly_dir / "boundary"
    boundary.write_text("// gmshToFoam-generated boundary\n", encoding="utf-8")
    os.utime(boundary, (mtime, mtime))
    return boundary


def _write_bc_dict(case_dir: Path, name: str, mtime: float) -> Path:
    """Helper: create 0/{name} at given mtime."""
    import os

    zero_dir = case_dir / "0"
    zero_dir.mkdir(parents=True, exist_ok=True)
    f = zero_dir / name
    f.write_text(f"// dummy {name}\n", encoding="utf-8")
    os.utime(f, (mtime, mtime))
    return f


def test_imported_bc_currentdict_satisfies_when_newer_than_polymesh(
    isolated_drafts,
):
    """Codex R7 P1 regression — DEC-V61-116.

    setup_*_bc authored 0/U at T=200, polyMesh points + boundary at T=100.
    BC dict mtime ≥ polyMesh.points mtime → BC current → not flagged missing.
    """
    _, imported = isolated_drafts
    case_id = "imported_2026-05-04T00-00-00Z_bc_current"
    case_dir = _seed_minimal_imported_for_bc_check(imported, case_id)
    _write_polymesh_points(case_dir, mtime=100.0)
    _write_polymesh_boundary(case_dir, mtime=100.0)
    _write_bc_dict(case_dir, "U", mtime=200.0)
    _write_bc_dict(case_dir, "p", mtime=200.0)
    r = analyze_case_completeness(case_id)
    bc_missing = [m for m in r.missing if m.field_path == "bc.patches"]
    assert bc_missing == [], (
        f"BC dict newer than polyMesh must satisfy contract; got {bc_missing}"
    )


def test_imported_bc_stale_after_remesh_flagged(isolated_drafts):
    """Codex R7 P1 regression — DEC-V61-116.

    Workflow: setup_bc at T=100 (0/U mtime=100) → re-mesh at T=200
    (polyMesh.boundary mtime=200). BC dict is now stale; the analyzer
    must flag bc.patches missing so engineer reruns setup_bc.
    """
    _, imported = isolated_drafts
    case_id = "imported_2026-05-04T00-00-00Z_bc_stale"
    case_dir = _seed_minimal_imported_for_bc_check(imported, case_id)
    _write_bc_dict(case_dir, "U", mtime=100.0)
    _write_polymesh_points(case_dir, mtime=200.0)  # remeshed AFTER BC
    _write_polymesh_boundary(case_dir, mtime=200.0)
    r = analyze_case_completeness(case_id)
    bc_missing = [m for m in r.missing if m.field_path == "bc.patches"]
    assert len(bc_missing) == 1, (
        f"stale BC dict (older than polyMesh) must be flagged; got {bc_missing}"
    )
    assert "re-mesh" in bc_missing[0].why or "current mesh" in bc_missing[0].why


def test_imported_bc_no_polymesh_flagged(isolated_drafts):
    """Without a polyMesh boundary file, BC can't be set up against any
    mesh → flag missing. Engineer needs to mesh first."""
    _, imported = isolated_drafts
    case_id = "imported_2026-05-04T00-00-00Z_no_mesh"
    _seed_minimal_imported_for_bc_check(imported, case_id)
    # Note: no polyMesh.boundary written.
    r = analyze_case_completeness(case_id)
    bc_missing = [m for m in r.missing if m.field_path == "bc.patches"]
    assert len(bc_missing) == 1


def test_imported_bc_polymesh_but_no_zero_dicts_flagged(isolated_drafts):
    """polyMesh.boundary exists but no 0/X files yet (mesh ran, BC
    didn't). Flag missing."""
    _, imported = isolated_drafts
    case_id = "imported_2026-05-04T00-00-00Z_meshed_no_bc"
    case_dir = _seed_minimal_imported_for_bc_check(imported, case_id)
    _write_polymesh_points(case_dir, mtime=100.0)
    _write_polymesh_boundary(case_dir, mtime=100.0)
    r = analyze_case_completeness(case_id)
    bc_missing = [m for m in r.missing if m.field_path == "bc.patches"]
    assert len(bc_missing) == 1


def test_imported_bc_partial_polymesh_missing_boundary_flagged(isolated_drafts):
    """Codex R9 P2 + R10 P3 regression — DEC-V61-116.

    Corrupted partial polyMesh (points exists, boundary missing) is a
    real failure mode after a partial restore or manual cleanup.
    Downstream setup_bc paths require boundary to exist; the analyzer
    must fail closed (BC missing) so completeness verdict tracks
    downstream reality (R9 P2).

    R10 P3: the remediation copy must NOT tell the user to run Step 3
    [AI 处理] (that path fails on missing boundary). Instead point at
    polyMesh restore / re-mesh.
    """
    _, imported = isolated_drafts
    case_id = "imported_2026-05-04T00-00-00Z_partial_polymesh"
    case_dir = _seed_minimal_imported_for_bc_check(imported, case_id)
    # Partial state: points exists + 0/U exists, but boundary is gone.
    _write_polymesh_points(case_dir, mtime=100.0)
    _write_bc_dict(case_dir, "U", mtime=200.0)
    # Note: no _write_polymesh_boundary call.
    r = analyze_case_completeness(case_id)
    bc_missing = [m for m in r.missing if m.field_path == "bc.patches"]
    assert len(bc_missing) == 1, (
        f"missing polyMesh/boundary must fail closed; got {bc_missing}"
    )
    why = bc_missing[0].why
    # R10 P3: copy must name the corrupted-state cause + suggest restore
    # or re-mesh, NOT just "run Step 3" (which would fail).
    assert "corrupted partial state" in why, f"wrong remediation copy: {why}"
    assert "Restore" in why or "re-run the mesh wizard" in why, (
        f"copy must point at restore/re-mesh; got: {why}"
    )


def test_imported_bc_setup_rewriting_boundary_still_current(isolated_drafts):
    """Codex R8 P1 regression — DEC-V61-116.

    setup_bc_from_stl_patches() with symmetry / non-default patches
    rewrites constant/polyMesh/boundary as part of BC setup itself.
    The analyzer must compare against polyMesh/`points` (mesh
    geometry), NOT polyMesh/`boundary` (which BC also touches).
    Otherwise BC setup that includes patch-type changes spuriously
    fails completeness right after success.

    Workflow:
      T=100: mesh runs → points + boundary mtime=100
      T=200: setup_bc → 0/U=200, polyMesh/boundary=200 (rewritten)
      Check: 0/U(200) >= points(100) → BC current ✓
      The boundary mtime(200) > 0/U(200) tie is irrelevant because
      the analyzer no longer reads boundary's mtime.
    """
    _, imported = isolated_drafts
    case_id = "imported_2026-05-04T00-00-00Z_bc_rewrites_boundary"
    case_dir = _seed_minimal_imported_for_bc_check(imported, case_id)
    # Mesh ran at T=100: points + boundary stamped 100.
    _write_polymesh_points(case_dir, mtime=100.0)
    _write_polymesh_boundary(case_dir, mtime=100.0)
    # setup_bc ran at T=200: 0/U + 0/p stamped 200, AND BOUNDARY
    # rewritten to 200 (symmetry case).
    _write_bc_dict(case_dir, "U", mtime=200.0)
    _write_bc_dict(case_dir, "p", mtime=200.0)
    _write_polymesh_boundary(case_dir, mtime=200.0)  # ← rewritten by BC
    r = analyze_case_completeness(case_id)
    bc_missing = [m for m in r.missing if m.field_path == "bc.patches"]
    assert bc_missing == [], (
        f"BC setup that rewrites polyMesh/boundary must NOT trigger "
        f"stale-BC flag (R8 P1 regression); got {bc_missing}"
    )


def test_imported_bc_patches_set_in_manifest_satisfies(isolated_drafts):
    """Future-proof signal: if bc.patches is non-empty in the manifest
    schema, the analyzer accepts it without checking filesystem mtimes.
    Lets future flows that DO populate the schema field bypass the
    filesystem check.
    """
    drafts, imported = isolated_drafts
    case_id = "imported_2026-05-04T00-00-00Z_bc_patches_set"
    _seed_imported_manifest(imported, case_id)  # has solver + turbulence + 1 patch
    r = analyze_case_completeness(case_id)
    bc_missing = [m for m in r.missing if m.field_path == "bc.patches"]
    assert bc_missing == []


def test_imported_solver_dict_without_name_still_flagged(isolated_drafts):
    """Codex R5 P2 regression — DEC-V61-116.

    A flat-draft `solver` dict without a `.name` key (metadata-only:
    family / steady_state / note) does NOT satisfy the solver
    requirement. Only a string `solver: simpleFoam` or a dict with
    `solver.name: simpleFoam` counts.
    """
    drafts, imported = isolated_drafts
    case_id = "imported_2026-05-04T00-00-00Z_solver_no_name"
    case_dir = imported / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    # Manifest: no physics.solver.
    (case_dir / "case_manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 2,
                "case_id": case_id,
                "physics": {"turbulence_model": "laminar"},
                "bc": {"patches": {"inlet": {"patch_type": "patch", "fields": {}}}},
                "numerics": {},
                "overrides": {},
                "history": [],
            }
        ),
        encoding="utf-8",
    )
    # Flat draft: solver is a dict with metadata only (no `name`).
    (drafts / f"{case_id}.yaml").write_text(
        yaml.safe_dump(
            {
                "id": case_id,
                "name": "Imported",
                "turbulence_model": "laminar",
                "solver": {
                    "family": "incompressible",
                    "steady_state": True,
                    "note": "user removed the name",
                },
            }
        ),
        encoding="utf-8",
    )
    r = analyze_case_completeness(case_id)
    solver_missing = [m for m in r.missing if m.field_path == "physics.solver"]
    assert len(solver_missing) == 1, (
        f"solver dict without .name must NOT satisfy contract; "
        f"got missing = {[m.field_path for m in r.missing]}"
    )
    assert r.ready_for_archive is False


def test_imported_merge_both_empty_still_flags(isolated_drafts):
    """Sanity — when neither manifest NOR flat draft has the required
    fields, the merge still flags them missing.

    Replaces test_imported_case_with_unset_turbulence_in_yaml_flagged_despite_default
    semantics under R5: missing means missing in BOTH sources.
    """
    drafts, imported = isolated_drafts
    case_id = "imported_2026-05-04T00-00-00Z_merge_both_empty"
    case_dir = imported / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "case_manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 2,
                "case_id": case_id,
                "physics": {},
                "bc": {"patches": {}},
                "numerics": {},
                "overrides": {},
                "history": [],
            }
        ),
        encoding="utf-8",
    )
    (drafts / f"{case_id}.yaml").write_text(
        yaml.safe_dump({"id": case_id, "name": "Bare scaffold view"}),
        encoding="utf-8",
    )
    r = analyze_case_completeness(case_id)
    assert r.ready_for_archive is False
    paths = {m.field_path for m in r.missing}
    assert "physics.solver" in paths
    assert "physics.turbulence_model" in paths
    assert "bc.patches" in paths


def test_imported_case_no_flat_draft_uses_manifest_only(isolated_drafts):
    """When no flat draft exists, the merge degenerates to manifest-only.
    A complete manifest still passes."""
    _, imported = isolated_drafts
    case_id = "imported_2026-05-04T00-00-00Z_no_flat"
    _seed_imported_manifest(imported, case_id)
    r = analyze_case_completeness(case_id)
    assert r.case_kind == "imported_user"
    assert r.ready_for_archive is True


def test_schema_invalid_manifest_blocks_archive(isolated_drafts):
    """Codex R2 P2 regression — DEC-V61-116.

    A parseable-but-schema-invalid manifest (e.g. `bc.patches: 1`
    instead of dict) must surface as a critical missing entry that
    blocks ready_for_archive. Earlier draft only logged a note and
    fell through to `_raw_has` which could declare ready=True while
    every downstream route that calls read_case_manifest() would 500.
    """
    _, imported = isolated_drafts
    case_id = "imported_2026-05-04T00-00-00Z_schema_invalid"
    case_dir = imported / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    # bc.patches as a scalar instead of dict → ManifestParseError on
    # read_case_manifest(). Raw YAML still parses.
    (case_dir / "case_manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 2,
                "case_id": case_id,
                "physics": {
                    "solver": "simpleFoam",
                    "turbulence_model": "laminar",
                },
                "bc": {"patches": 1},  # ← invalid
                "numerics": {},
                "overrides": {},
                "history": [],
            }
        ),
        encoding="utf-8",
    )
    r = analyze_case_completeness(case_id)
    assert r.ready_for_archive is False, (
        "schema-invalid manifest must block archive readiness"
    )
    assert any(
        m.field_path == "case_manifest.yaml" and m.severity == "critical"
        for m in r.missing
    ), f"expected manifest_schema_invalid critical entry; missing = {r.missing}"


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

"""Stage-2 2b SPIKE · advisor_stack behavioral eval on a REAL case (1 case).

Per `.planning/strategic/stage_goal_spec_v0.1_2026-05-28.md` §4, 2b
(advisor_stack case-behavioral eval) needed a feasibility verdict. This spike
delivers it on one real case + leaves a recipe for the broader sub-DEC.

What was found (read-only investigation, this file's commit body has details):

  * The production case-dir adapter is `_autodiscover` in
    `ui/backend/routes/ai_review.py:320`, which expects pre-processed
    artifacts under `<case_dir>/inputs/*.{yaml,json}`. **No in-repo case has
    a populated `inputs/` dir** — so a "lift the adapter and run it on every
    case" path returns empty for every case (no coverage gained).
  * However, **13 of the `.planning/case_profiles/*_dicts/` directories ship
    a top-level `parts_manifest.yaml`** (committed alongside the OpenFOAM
    `system/` + `0/` dumps). Feeding one of these directly to
    `assemble_stack(parts_manifest=...)` dispatches real advisors and
    produces real findings — proving the behavioral-eval pattern works on
    real-case inputs *that already ship*.
  * Scope caveat (truth-chain): E-case "expected firings" tables (e.g. E02
    in `.planning/evals/canonical/E02_case_021_v65_tbl.md`) assume the FULL
    kwarg set (parts_manifest + shm_dict + thermo_dict + bc_specs + step + …).
    A `parts_manifest`-only spike can only assert the **subset of advisors
    that the parts_manifest kwarg dispatches** — not the full E-case
    expected-firing set. That subset is exact and physically meaningful;
    extending to richer kwargs is the follow-on sub-DEC.

This spike covers **one** case (case_021 = E02, NASA TMR flat plate — P1's
own validated benchmark). It pins:
  (a) the parts_manifest-driven dispatch is deterministic across runs
  (verified manually: 3/3 identical),
  (b) the dispatched advisor set on case_021 is {face_orientation_advisor,
      inlet_outlet_validator},
  (c) the findings count is **0** — physically correct for a clean validated
      benchmark with 5 BC patches and no part-level interface geometry.

If a future change to advisor dispatch logic makes this case spuriously
produce findings (or stops dispatching one of these two advisors on a real
case input), the spike fails — that is the regression protection 2b adds
beyond the static documentation harness in
`ui/backend/tests/test_canonical_advisor_eval.py`.

**Follow-on work** (extended under DEC-V61-211 + sub-DECs):
  - **DEC-V61-211 (this session, in flight)**: `solver_block_extractor`
    v0.1 — extracts `solver`/`adjust_time_step`/`delta_t` from
    `system/controlDict` so assemble_stack can discriminate density-based
    vs incompressible cases. Test
    `test_case_021_and_case_030_solver_block_extension` below feeds the
    extractor's output into assemble_stack and asserts the case-class
    discrimination (case_021 simpleFoam → 0 findings; case_030
    rhoCentralFoam → ≥1 solver_block finding). v0.2 (preconditioners
    block-parse) deferred to a follow-on sub-DEC.
  - **Other extractors (each its own sub-DEC)**: `shm_dict`,
    `thermo_dict`, `step`, `thin_wall_inputs` from the OpenFOAM
    `system/`/`constant/` dumps to unlock the FULL E-case expected-firing
    set, not just the parts_manifest+solver_block subset.
  - **Adapter discovery decision (separate DEC)**: extend production
    `_autodiscover` to also find top-level `parts_manifest.yaml`
    (case_profiles' shipped convention).
  - **Per-case physical labeling** of the other 12 manifest-bearing
    profiles — only valuable once richer extractors land (a manifest-only
    eval over 13 cases produces 13 identical-result tests = theater).
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ui.backend.services.advisor_stack import assemble_stack
from ui.backend.services.case_extractors import extract_solver_block_snapshot

REPO_ROOT = Path(__file__).resolve().parents[1]
CASE_021_PARTS_MANIFEST = (
    REPO_ROOT
    / ".planning"
    / "case_profiles"
    / "case_021_v65_tbl_2nd_re_dicts"
    / "parts_manifest.yaml"
)

# Subset of advisors `assemble_stack` dispatches when ONLY parts_manifest is
# supplied. Derived from the input shape (case_021 has 5 patches + zero
# explicit parts/bodies + no shm/thermo/step kwargs), not snapshotted: the
# face_orientation_advisor + inlet_outlet_validator are the two advisors that
# read parts_manifest directly. Other E02-expected advisors
# (solver_block_advisor, unit_detector, urf_advisor, cf_canonical_choice,
# yplus_regime_match) require kwargs (solver_block_snapshot, thermo_dict, …)
# not provided here — they are NOT failures; they are out of THIS spike's scope.
EXPECTED_DISPATCHED_ADVISORS = frozenset(
    {"face_orientation_advisor", "inlet_outlet_validator"}
)

# Physically: case_021 is a clean NASA TMR turbulent flat plate (V103
# LANDED, B81 verdict strict-FULL). No D7 face-orientation violation
# (blockMesh native, clean patch normals). No inlet-outlet validity issue
# (canonical freestream inlet / fixedValue outlet). 0 findings is the
# correct adjudication for this case under the parts_manifest-only input.
EXPECTED_FINDINGS_COUNT = 0


def test_case_021_parts_manifest_yields_expected_dispatch() -> None:
    """Case-level behavioral assertion: dispatched advisor set == expected.

    Set equality (not `any`) is the same adjudication semantics as the v9
    behavioral eval (a609f58): a future change that dispatches an extra
    advisor on real case_021 input — or stops dispatching one of these two
    — fails here, where no other test would catch it.
    """
    if not CASE_021_PARTS_MANIFEST.is_file():
        pytest.skip(
            f"case_021 parts_manifest not found at {CASE_021_PARTS_MANIFEST} "
            f"— eval target moved/removed; update path or restore artifact."
        )
    pm = yaml.safe_load(CASE_021_PARTS_MANIFEST.read_text(encoding="utf-8"))
    assert isinstance(pm, dict), f"case_021 parts_manifest is not a dict: {type(pm)}"

    report = assemble_stack(parts_manifest=pm)
    dispatched = frozenset(c.advisor_name for c in report.advisor_calls)

    missing = EXPECTED_DISPATCHED_ADVISORS - dispatched
    unexpected = dispatched - EXPECTED_DISPATCHED_ADVISORS
    assert dispatched == EXPECTED_DISPATCHED_ADVISORS, (
        f"case_021 dispatched-advisor set mismatch.\n"
        f"  expected   : {sorted(EXPECTED_DISPATCHED_ADVISORS)}\n"
        f"  actual     : {sorted(dispatched)}\n"
        f"  missing    : {sorted(missing)} (expected to dispatch, did not)\n"
        f"  unexpected : {sorted(unexpected)} (dispatched but not expected — "
        f"either a new advisor reads parts_manifest, or scope drifted)"
    )


def test_case_021_findings_count_matches_clean_case_expectation() -> None:
    """Adjudication: a clean validated case must produce 0 findings.

    case_021 (NASA TMR turbulent flat plate, V103 LANDED) is a canonical
    clean benchmark — it should never raise a finding from the
    parts_manifest-driven advisors. If a finding appears, either the case
    drifted (truth-chain check) or an advisor introduced a false positive.
    Either is a real regression worth surfacing.
    """
    if not CASE_021_PARTS_MANIFEST.is_file():
        pytest.skip("case_021 parts_manifest not found — see other spike test")
    pm = yaml.safe_load(CASE_021_PARTS_MANIFEST.read_text(encoding="utf-8"))
    report = assemble_stack(parts_manifest=pm)
    assert len(report.findings) == EXPECTED_FINDINGS_COUNT, (
        f"case_021 (clean validated NASA TMR flat plate) produced "
        f"{len(report.findings)} finding(s), expected "
        f"{EXPECTED_FINDINGS_COUNT}. First few:\n"
        + "\n".join(
            f"  [{f.severity}] {f.advisor_name}: {f.title[:120]}"
            for f in report.findings[:5]
        )
    )


# ----------------------------------------------------------------------
# DEC-V61-211 · solver_block_extractor integration — the live case-class
# discrimination proof. Distinct from the parts_manifest-only spike tests
# above because parts_manifest alone yields IDENTICAL output for every
# in-repo case (surveyed 2026-05-28, 13/13 same), while the solver_block
# extractor surfaces the density-based-vs-incompressible class split that
# `check_solver_block`'s V27 dispatch actually keys on.
# ----------------------------------------------------------------------


_CASE_021_DIR = (
    REPO_ROOT
    / ".planning"
    / "case_profiles"
    / "case_021_v65_tbl_2nd_re_dicts"
)
# case_030 ships NO parts_manifest.yaml (it's not in the 13-manifest
# subset) — so this test feeds ONLY the extracted solver_block_snapshot,
# proving the solver_block path is independently load-bearing for
# behavioral coverage of density-based cases.
_CASE_030_DIR = (
    REPO_ROOT
    / ".planning"
    / "case_profiles"
    / "case_030_v65_wedge15ma5_v106_2nd_witness_dicts"
)


def test_case_021_and_case_030_solver_block_extension() -> None:
    """Extractor + assemble_stack produce case-class-distinct findings.

    case_021 (simpleFoam, incompressible, clean validated NASA TMR):
    `check_solver_block` skips density-based dispatch → 0 findings from
    solver_block_advisor; the parts_manifest still drives face_orientation
    + inlet_outlet dispatch (both clean → 0 findings overall).

    case_030 (rhoCentralFoam, density-based, adjustTimeStep=False,
    deltaT=1e-4): density-based + adjustTimeStep≠true triggers V27 → ≥1
    finding from solver_block_advisor.

    Set comparison: |findings(case_030)| > |findings(case_021)| AND every
    case_030 finding is sourced from solver_block_advisor. That's the
    live case-class adjudication unreachable from parts_manifest alone.
    """
    if not _CASE_021_DIR.is_dir() or not _CASE_030_DIR.is_dir():
        pytest.skip("one of the discrimination-pair case dirs is missing")

    # case_021: full kwargs (parts_manifest + solver_block)
    case_021_pm = yaml.safe_load(
        (_CASE_021_DIR / "parts_manifest.yaml").read_text(encoding="utf-8")
    )
    case_021_snap = extract_solver_block_snapshot(_CASE_021_DIR)
    assert case_021_snap is not None and case_021_snap.solver == "simpleFoam"
    r021 = assemble_stack(
        parts_manifest=case_021_pm,
        solver_block_snapshot=case_021_snap,
    )

    # case_030: solver_block only (no parts_manifest in repo)
    case_030_snap = extract_solver_block_snapshot(_CASE_030_DIR)
    assert case_030_snap is not None
    assert case_030_snap.solver == "rhoCentralFoam"
    # extractor must also have surfaced the V27-relevant fields:
    assert case_030_snap.adjust_time_step is False, (
        f"case_030 adjustTimeStep should parse as False (token 'no' in "
        f"controlDict); got {case_030_snap.adjust_time_step!r}"
    )
    r030 = assemble_stack(solver_block_snapshot=case_030_snap)

    # Both runs dispatch solver_block_advisor (the dispatch surface itself
    # is gated on `solver_block_snapshot is not None`, not on findings).
    assert "solver_block_advisor" in {
        c.advisor_name for c in r021.advisor_calls
    }, "case_021 should dispatch solver_block_advisor with a snapshot supplied"
    assert "solver_block_advisor" in {
        c.advisor_name for c in r030.advisor_calls
    }, "case_030 should dispatch solver_block_advisor with a snapshot supplied"

    # Adjudication: density-based case_030 must yield strictly more
    # findings than incompressible case_021 (the V27 dispatch differential).
    assert len(r030.findings) > len(r021.findings), (
        f"case-class discrimination broken: "
        f"case_021 (incompressible) findings={len(r021.findings)}, "
        f"case_030 (density-based) findings={len(r030.findings)} — "
        f"expected case_030 > case_021 from V27 density-based path."
    )

    # Every case_030 finding must come from solver_block_advisor — this
    # pins WHERE the discrimination is happening (V27 path, not a
    # tangential dispatch from some other advisor that happens to fire).
    case_030_sources = {f.source_advisor for f in r030.findings}
    assert case_030_sources == {"solver_block_advisor"}, (
        f"case_030 findings should ALL be sourced from solver_block_advisor "
        f"(V27 density-based dispatch); got sources {sorted(case_030_sources)}"
    )

    # case_021 stays at 0 findings — clean validated benchmark, incompressible
    # → V27 path not entered. If this regresses, either V27 dispatch logic
    # widened to fire on incompressible cases (likely a bug), or case_021's
    # controlDict was modified.
    assert len(r021.findings) == 0, (
        f"case_021 (clean validated incompressible) produced "
        f"{len(r021.findings)} finding(s), expected 0. First:\n"
        + "\n".join(
            f"  [{f.severity}] {f.source_advisor}: {f.message[:120]}"
            for f in r021.findings[:3]
        )
    )


def test_followon_scope_canary_count_of_in_repo_manifests() -> None:
    """Canary: pin the size of the follow-on opportunity surface.

    13 case_profiles ship a parts_manifest today. If that number drops
    significantly, a manifest got removed (and the follow-on sub-DEC's
    feasibility shrinks); if it grows, a new case is available to extend
    coverage to. Either way it should be a deliberate decision — not a
    silent drift this spike doesn't see.
    """
    profiles_dir = REPO_ROOT / ".planning" / "case_profiles"
    if not profiles_dir.is_dir():
        pytest.skip("case_profiles dir missing")
    count = sum(1 for _ in profiles_dir.glob("*/parts_manifest.yaml"))
    assert count >= 10, (
        f"only {count} case_profiles ship parts_manifest.yaml (was 13 at "
        f"spike creation 2026-05-28); follow-on 2b sub-DEC's input pool may "
        f"have shrunk — investigate."
    )

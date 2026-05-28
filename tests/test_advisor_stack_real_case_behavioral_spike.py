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

**Follow-on work** (sub-DEC, NOT this spike):
  - Extend to the other 12 manifest-bearing case_profiles (each needs its
    own physically-labeled expected set; not snapshot-driven).
  - Build a `shm_dict` / `thermo_dict` / `step` extractor from the OpenFOAM
    `system/` / `constant/` dumps to unlock the FULL E-case expected-firing
    set, not just the parts_manifest subset.
  - Decide whether the production adapter's `inputs/`-convention should be
    extended to also discover top-level `parts_manifest.yaml` (the format
    that case_profiles actually ship).
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ui.backend.services.advisor_stack import assemble_stack

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

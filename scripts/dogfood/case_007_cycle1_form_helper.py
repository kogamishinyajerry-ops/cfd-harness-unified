"""DEC-V61-202-SUB-M31-CYCLE1 · form-helper end-to-end dogfood.

Production path proof: stage a sparse manifest WITHOUT case_family
(mirrors what `case_scaffold/manifest_writer.py` writes on real
imports), then walk the rail-driven labeling-then-skeleton flow:

  step 1 → rail surfaces case_family as a missing field (warning gap)
  PATCH case_family = "ship_vof"
  step 4 → rail surfaces bc.patches gap WITH suggested_skeleton
  PATCH bc.patches = skeleton dict
  step 4 (refetch) → rail.kind == step_default (case ready)

This mirrors the cycle-7 surrogate journey but for the form-helper
specifically, on the production path (no hand-injected case_family).
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import yaml
from fastapi.testclient import TestClient


CASE_ID = "case_007_cycle1_form_helper"

STARTING_MANIFEST = {
    "case_id": CASE_ID,
    # No case_family — mirrors a real imported case (case_scaffold/
    # manifest_writer.py historically omitted the field). The dogfood
    # walks the rail-driven labeling flow: step 1 surfaces case_family
    # as a missing field, engineer PATCHes it to "ship_vof", then
    # step 4 offers the skeleton.
    "solver_backend": "openfoam",
    "physics": {
        "solver": "interFoam",
        "turbulence_model": "kOmegaSST",
    },
    # bc.patches deliberately empty → triggers the step-4 form-helper gap
}


def main():
    tmpdir = Path(tempfile.mkdtemp(prefix="cycle1_form_helper_"))
    imported_root = tmpdir / "imported"
    imported_root.mkdir()
    case_dir = imported_root / CASE_ID
    case_dir.mkdir()
    (case_dir / "case_manifest.yaml").write_text(yaml.safe_dump(STARTING_MANIFEST))

    os.environ["WORKBENCH_PROVENANCE_DISABLED"] = "1"  # keep test tree clean

    import ui.backend.routes.workbench_frame as wf
    import ui.backend.services.case_completeness.analyzer as cc_analyzer
    import ui.backend.services.manifest_patch as mp

    wf.IMPORTED_DIR = imported_root
    cc_analyzer.IMPORTED_DIR = imported_root
    mp.IMPORTED_DIR = imported_root

    from ui.backend.main import app
    client = TestClient(app)

    print("\n=== Cycle 1 form-helper dogfood (production path) ===\n")

    # ── Step 1: rail should surface case_family gap ───────────────────
    r_step1 = client.get(f"/api/cases/{CASE_ID}/workbench_frame?step=1")
    assert r_step1.status_code == 200, f"GET step 1: {r_step1.status_code}"
    frame_step1 = r_step1.json()
    step1_rail = frame_step1["rail_primary"]
    print(f"  step 1 rail.field_path = {step1_rail.get('field_path')}")
    print(f"  step 1 rail.kind = {step1_rail['kind']}")
    print(f"  step 1 rail.title = {step1_rail.get('title')}")
    if frame_step1.get("completeness"):
        print(f"  step 1 completeness.missing = "
              f"{[(m.get('field_path'), m.get('severity')) for m in frame_step1.get('completeness', {}).get('missing', [])]}")

    # ── PATCH case_family ─────────────────────────────────────────────
    case_family_patch = client.patch(
        f"/api/cases/{CASE_ID}/manifest",
        json={
            "field_path": "case_family",
            "value": "ship_vof",
            "op": "set",
            "expected_state_sha": frame_step1["manifest_state_sha"],
        },
    )
    cf_response = case_family_patch.json() if case_family_patch.status_code == 200 else None
    print(f"  PATCH case_family status = {case_family_patch.status_code}")
    if cf_response:
        print(f"  PATCH case_family success = {cf_response.get('success')}")

    # ── Step 4 frame: expect skeleton offered ─────────────────────────
    r = client.get(f"/api/cases/{CASE_ID}/workbench_frame?step=4")
    assert r.status_code == 200, f"GET frame: {r.status_code} / {r.text[:200]}"
    frame = r.json()
    rail = frame["rail_primary"]

    skeleton = rail.get("suggested_skeleton")
    print(f"  rail.kind = {rail['kind']}")
    print(f"  rail.field_path = {rail.get('field_path')}")
    print(f"  rail.cta_label = {rail.get('cta_label')}")
    print(f"  rail.suggested_skeleton keys = "
          f"{sorted(skeleton.keys()) if isinstance(skeleton, dict) else None}")

    # ── PATCH with skeleton ───────────────────────────────────────────
    patch_payload = {
        "field_path": "bc.patches",
        "value": skeleton,
        "op": "set",
        "expected_state_sha": frame["manifest_state_sha"],
    }
    p = client.patch(f"/api/cases/{CASE_ID}/manifest", json=patch_payload)
    patch_response = p.json() if p.status_code == 200 else None
    print(f"\n  PATCH status = {p.status_code}")
    if patch_response:
        print(f"  PATCH success = {patch_response.get('success')}")
        print(f"  PATCH applied_path = {patch_response.get('applied_path')}")

    # ── Re-fetch and inspect the manifest landing ─────────────────────
    r2 = client.get(f"/api/cases/{CASE_ID}/workbench_frame?step=4")
    frame2 = r2.json() if r2.status_code == 200 else {}
    rail2 = frame2.get("rail_primary", {}) if frame2 else {}

    # Read the manifest directly to confirm the skeleton landed in
    # bc.patches.
    manifest_path = case_dir / "case_manifest.yaml"
    landed_manifest = yaml.safe_load(manifest_path.read_text())
    landed_patches = landed_manifest.get("bc", {}).get("patches", {})
    print(f"\n  manifest bc.patches keys = {sorted(landed_patches.keys())}")
    print(f"  post-PATCH rail.kind = {rail2.get('kind')}")
    print(f"  post-PATCH rail.field_path = {rail2.get('field_path')}")

    # ── Checks ────────────────────────────────────────────────────────
    checks = [
        ("Step 1 rail surfaces case_family as a missing field",
         step1_rail.get("field_path") == "case_family"),
        ("PATCH case_family succeeded",
         case_family_patch.status_code == 200 and cf_response
         and cf_response.get("success") is True),
        ("Rail at step 4 surfaces suggested_skeleton",
         isinstance(skeleton, dict)),
        ("Skeleton has canonical inlet/outlet/wall keys",
         isinstance(skeleton, dict)
         and set(skeleton.keys()) == {"inlet", "outlet", "wall"}),
        # Codex R0 P2 fix: when ONLY skeleton is offered, the backend
        # suppresses the primary cta_label (null) so the frontend doesn't
        # render a duplicate disabled button. The secondary skeleton
        # button (frontend side) carries the hardcoded label.
        ("Primary cta_label suppressed (skeleton-only path)",
         rail.get("cta_label") is None),
        ("Rail provenance records skeleton_keys",
         any("skeleton_keys=" in p for p in rail.get("provenance", []))),
        ("PATCH with skeleton value returns 200 + success=True",
         p.status_code == 200 and patch_response
         and patch_response.get("success") is True),
        ("Manifest bc.patches landed with 3 entries (inlet/outlet/wall)",
         set(landed_patches.keys()) == {"inlet", "outlet", "wall"}),
        ("Post-PATCH rail no longer surfaces bc.patches as a gap",
         rail2.get("field_path") != "bc.patches"),
    ]

    print()
    all_pass = True
    for label, ok in checks:
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print(f"  [{status}] {label}")

    print()
    print(f"Verdict: {'PASS' if all_pass else 'FAIL'}")

    if all_pass:
        shutil.rmtree(tmpdir, ignore_errors=True)

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()

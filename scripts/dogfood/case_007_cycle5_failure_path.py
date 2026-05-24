"""DEC-V61-202-SUB-M31-CYCLE5 · failure-path ergonomics dogfood.

Goal: document what the workbench actually does when an engineer
makes a recoverable mistake. M3.0 retro Open Question #3 noted that
the cycle-7 surrogate only walked the happy path; this dogfood walks:

    1. Initial empty manifest
    2. Engineer labels case_family correctly (forward progress)
    3. Engineer applies the canonical skeleton (forward progress)
    4. Engineer makes a TYPO that's structurally valid    (mistake A)
    5. Engineer makes a STRUCT-WRONG patch                (mistake B)
    6. Engineer reverts to the correct value              (recovery)
    7. Final state confirms re-readiness

Each step's actual backend response is captured for the DOGFOOD
report. PASS does NOT mean "no mistakes happened" — it means the
system handled the failure path coherently (rejected invalid,
accepted valid, restored on revert).
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


CASE_ID = "case_007_cycle5_failure_path"

# Codex cycle-5 R2 P3: FastAPI returns 4xx errors as
# `{"detail": str | [...]}`. Our 200 envelope is
# `{"success": bool, "validation_errors": [...]}`. The cycle-5
# contract treats "rejection with the reason named" as PASS — both
# envelopes need to be recognized.
_NAMED_REASON_KEYWORDS = ("type", "value", "dict", "schema", "expected", "patch_type")


def _is_rejection_with_named_reason(response_body: dict | None) -> bool:
    """True iff the response body documents a type/schema/value
    rejection — either via the 200 envelope's `validation_errors`
    list (each string item checked) OR via FastAPI's 4xx `detail`
    field (string OR list of pydantic error dicts).
    """
    if not isinstance(response_body, dict):
        return False

    # Path A: 200-envelope rejection (success=false + validation_errors)
    if response_body.get("success") is False:
        for err in response_body.get("validation_errors") or []:
            txt = str(err).lower()
            if any(k in txt for k in _NAMED_REASON_KEYWORDS):
                return True

    # Path B: FastAPI 4xx envelope (detail string OR pydantic error list)
    detail = response_body.get("detail")
    if isinstance(detail, str):
        txt = detail.lower()
        if any(k in txt for k in _NAMED_REASON_KEYWORDS):
            return True
    elif isinstance(detail, list):
        # Pydantic v2 returns [{"type":..., "loc":..., "msg":..., ...}, ...]
        # Codex cycle-5 R3 P2 fix: scan ONLY the human-readable `msg`
        # field, not all values. Pydantic's `loc: ["body", "value"]`
        # and `type: "dict_type"` happen to match the keyword set
        # accidentally — but those represent unrelated request-body
        # validation errors (route-contract regressions), not the
        # manifest-validation rejection cycle-5 is trying to document.
        # Restricting to `msg` keeps the false-PASS-against-route-
        # regression risk closed.
        for entry in detail:
            if not isinstance(entry, dict):
                continue
            msg = entry.get("msg")
            if not isinstance(msg, str):
                continue
            txt = msg.lower()
            if any(k in txt for k in _NAMED_REASON_KEYWORDS):
                return True

    return False

# Start sparse — engineer has imported but hasn't labeled yet.
STARTING_MANIFEST = {
    "case_id": CASE_ID,
    "solver_backend": "openfoam",
    "physics": {
        "solver": "interFoam",
        "turbulence_model": "kOmegaSST",
    },
    # bc.patches deliberately empty
}


def main() -> int:
    tmpdir = Path(tempfile.mkdtemp(prefix="cycle5_failure_path_"))
    imported_root = tmpdir / "imported"
    imported_root.mkdir()
    case_dir = imported_root / CASE_ID
    case_dir.mkdir()
    (case_dir / "case_manifest.yaml").write_text(yaml.safe_dump(STARTING_MANIFEST))

    os.environ["WORKBENCH_PROVENANCE_DISABLED"] = "1"

    import ui.backend.routes.workbench_frame as wf
    import ui.backend.services.case_completeness.analyzer as cc_analyzer
    import ui.backend.services.manifest_patch as mp

    wf.IMPORTED_DIR = imported_root
    cc_analyzer.IMPORTED_DIR = imported_root
    mp.IMPORTED_DIR = imported_root

    from ui.backend.main import app
    client = TestClient(app)

    print("\n=== Cycle 5 failure-path dogfood ===\n")

    # ── Step 1: initial state ─────────────────────────────────────────
    r_step1 = client.get(f"/api/cases/{CASE_ID}/workbench_frame?step=1")
    assert r_step1.status_code == 200
    frame_step1 = r_step1.json()
    print(f"  [1] step 1 rail.field_path = {frame_step1['rail_primary'].get('field_path')}")
    sha_after_step1 = frame_step1["manifest_state_sha"]

    # ── Step 2: label case_family (forward progress) ──────────────────
    cf = client.patch(
        f"/api/cases/{CASE_ID}/manifest",
        json={
            "field_path": "case_family",
            "value": "ship_vof",
            "op": "set",
            "expected_state_sha": sha_after_step1,
        },
    )
    cf_response = cf.json() if cf.status_code == 200 else None
    cf_success = cf.status_code == 200 and cf_response and cf_response.get("success") is True
    print(f"  [2] PATCH case_family=ship_vof: status={cf.status_code} success={cf_success}")

    # ── Step 3: apply canonical skeleton (forward progress) ───────────
    r_step4_pre = client.get(f"/api/cases/{CASE_ID}/workbench_frame?step=4")
    frame_step4_pre = r_step4_pre.json()
    skeleton = frame_step4_pre["rail_primary"].get("suggested_skeleton")
    sha_pre_skeleton = frame_step4_pre["manifest_state_sha"]
    p_sk = client.patch(
        f"/api/cases/{CASE_ID}/manifest",
        json={
            "field_path": "bc.patches",
            "value": skeleton,
            "op": "set",
            "expected_state_sha": sha_pre_skeleton,
        },
    )
    sk_response = p_sk.json() if p_sk.status_code == 200 else None
    sk_success = p_sk.status_code == 200 and sk_response and sk_response.get("success") is True
    print(f"  [3] PATCH skeleton: status={p_sk.status_code} success={sk_success} keys={sorted(skeleton.keys()) if isinstance(skeleton, dict) else None}")

    # Check the manifest is in the expected good state.
    manifest_after_step3 = yaml.safe_load((case_dir / "case_manifest.yaml").read_text())
    inlet_type_good = (
        manifest_after_step3.get("bc", {}).get("patches", {}).get("inlet", {}).get("patch_type")
    )
    print(f"  [3] manifest bc.patches.inlet.patch_type after skeleton = {inlet_type_good!r}")

    # ── Step 4: TYPO mistake — structurally valid, semantically wrong ─
    sha_after_step3 = sk_response.get("new_state_sha") if sk_response else sha_pre_skeleton
    typo_patch = client.patch(
        f"/api/cases/{CASE_ID}/manifest",
        json={
            "field_path": "bc.patches.inlet.patch_type",
            "value": "fixedValue_typo",  # typo, not a real OpenFOAM type
            "op": "set",
            "expected_state_sha": sha_after_step3,
        },
    )
    # Codex cycle-5 R1 P3 fix: parse response body on 4xx too so the
    # "rejected with validation_errors" branch of the predicate below
    # is actually reachable. FastAPI returns JSON for 400/422, and
    # the cycle-5 contract treats rejection-with-named-errors as a
    # valid PASS outcome — but only if the response body is parsed.
    typo_response = (
        typo_patch.json()
        if typo_patch.status_code in (200, 400, 422)
        else None
    )
    typo_accepted = (
        typo_patch.status_code == 200
        and typo_response
        and typo_response.get("success") is True
    )
    print(f"  [4] PATCH typo 'fixedValue_typo': status={typo_patch.status_code} success={typo_response.get('success') if typo_response else None}")
    if typo_response and typo_response.get("validation_errors"):
        print(f"      validation_errors = {typo_response['validation_errors'][:200]}")

    manifest_after_typo = yaml.safe_load((case_dir / "case_manifest.yaml").read_text())
    inlet_type_after_typo = (
        manifest_after_typo.get("bc", {}).get("patches", {}).get("inlet", {}).get("patch_type")
    )
    print(f"  [4] manifest bc.patches.inlet.patch_type after typo = {inlet_type_after_typo!r}")

    # Decide which sha to use for next PATCH based on typo result.
    sha_after_typo = (
        typo_response.get("new_state_sha")
        if (typo_accepted and typo_response and typo_response.get("new_state_sha"))
        else sha_after_step3
    )

    # ── Step 5: STRUCT-wrong mistake — wrong type at a node ──────────
    struct_patch = client.patch(
        f"/api/cases/{CASE_ID}/manifest",
        json={
            "field_path": "bc.patches.inlet",
            "value": "not_a_dict",  # should be a dict, sending string
            "op": "set",
            "expected_state_sha": sha_after_typo,
        },
    )
    struct_response = (
        struct_patch.json()
        if struct_patch.status_code in (200, 422, 400)
        else None
    )
    # Codex cycle-5 R0 P2 + R2 P3 fix: distinguish "real type-
    # validation rejection" from "unrelated 4xx" (state-SHA mismatch,
    # route contract regression), AND support both response envelopes
    # (200-success-false vs FastAPI 4xx-detail). Generic 4xx without
    # naming the type/schema reason would mask BUG-CYCLE5-1 as fixed.
    struct_rejected = _is_rejection_with_named_reason(struct_response)
    print(f"  [5] PATCH struct-wrong 'not_a_dict': status={struct_patch.status_code} rejected={struct_rejected}")
    if struct_response and not struct_rejected and struct_response.get("success") is False:
        print(f"      (rejected but NOT with type-validation envelope — possible unrelated 4xx)")
    if struct_response and struct_response.get("validation_errors"):
        print(f"      validation_errors = {struct_response['validation_errors'][:200]}")

    manifest_after_struct = yaml.safe_load((case_dir / "case_manifest.yaml").read_text())
    inlet_after_struct = (
        manifest_after_struct.get("bc", {}).get("patches", {}).get("inlet")
    )
    print(f"  [5] manifest bc.patches.inlet after struct-wrong = {type(inlet_after_struct).__name__}")

    # ── Step 6: revert to canonical fixedValue ────────────────────────
    sha_for_revert = (
        struct_response.get("new_state_sha")
        if (struct_response and struct_response.get("new_state_sha"))
        else sha_after_typo
    )
    revert_patch = client.patch(
        f"/api/cases/{CASE_ID}/manifest",
        json={
            "field_path": "bc.patches.inlet.patch_type",
            "value": "fixedValue",  # restore canonical
            "op": "set",
            "expected_state_sha": sha_for_revert,
        },
    )
    revert_response = revert_patch.json() if revert_patch.status_code == 200 else None
    revert_success = (
        revert_patch.status_code == 200
        and revert_response
        and revert_response.get("success") is True
    )
    print(f"  [6] PATCH revert to 'fixedValue': status={revert_patch.status_code} success={revert_success}")
    if not revert_success and revert_response:
        print(f"      validation_errors = {revert_response.get('validation_errors')}")

    manifest_after_revert = yaml.safe_load((case_dir / "case_manifest.yaml").read_text())
    inlet_type_after_revert = (
        manifest_after_revert.get("bc", {}).get("patches", {}).get("inlet", {}).get("patch_type")
        if isinstance(manifest_after_revert.get("bc", {}).get("patches", {}).get("inlet"), dict)
        else None
    )
    print(f"  [6] manifest bc.patches.inlet.patch_type after revert = {inlet_type_after_revert!r}")

    # ── Step 7: final fetch, rail should be step_default ──────────────
    r_final = client.get(f"/api/cases/{CASE_ID}/workbench_frame?step=4")
    frame_final = r_final.json()
    rail_final = frame_final["rail_primary"]
    print(f"  [7] final rail.kind = {rail_final['kind']}")
    print(f"  [7] final rail.field_path = {rail_final.get('field_path')}")

    # ── Checks ────────────────────────────────────────────────────────
    checks = [
        ("Step 1: rail surfaced case_family gap",
         frame_step1["rail_primary"].get("field_path") == "case_family"),
        ("Step 2: case_family PATCH succeeded",
         cf_success),
        ("Step 3: skeleton PATCH succeeded + landed",
         sk_success and inlet_type_good == "fixedValue"),
        # Codex cycle-5 R0 P3 + R2 P3 fix: tighten typo predicate +
        # support both response envelopes:
        #   - 200 envelope: {"success": bool, "validation_errors": [...]}
        #   - FastAPI 4xx envelope: {"detail": str | [...]}
        # Cycle-5 contract: if accepted (200 + success=true), manifest
        # must contain the typo'd value. If rejected (200 +
        # success=false OR 4xx), the response must NAME the
        # type/value/schema/patch_type reason via either top-level
        # validation_errors OR FastAPI's detail string. A 4xx for
        # unrelated reasons (state-SHA mismatch, route regression)
        # with no relevant naming does NOT count as PASS.
        ("Step 4: typo PATCH was handled coherently (accepted-and-wrote, OR rejected-with-named-reason)",
         (typo_accepted and inlet_type_after_typo == "fixedValue_typo")
         or _is_rejection_with_named_reason(typo_response)),
        # Struct-wrong (5) MUST be rejected — that's a type contract.
        ("Step 5: struct-wrong PATCH was rejected",
         struct_rejected),
        # After struct-wrong rejection, the manifest must still have
        # inlet as a dict (struct-wrong didn't corrupt it).
        ("Step 5: manifest inlet stays a dict after struct-wrong rejection",
         isinstance(inlet_after_struct, dict)),
        ("Step 6: revert PATCH succeeded",
         revert_success),
        ("Step 6: manifest restored to 'fixedValue'",
         inlet_type_after_revert == "fixedValue"),
        ("Step 7: rail returned to step_default (no lingering FAIL)",
         rail_final["kind"] == "step_default"),
    ]

    print()
    all_pass = True
    for label, ok in checks:
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print(f"  [{status}] {label}")

    print()
    print(f"Verdict: {'PASS' if all_pass else 'FAIL (see DOGFOOD doc for backlog)'}")

    if all_pass:
        shutil.rmtree(tmpdir, ignore_errors=True)
    else:
        print(f"\n  Tmpdir preserved for investigation: {tmpdir}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())

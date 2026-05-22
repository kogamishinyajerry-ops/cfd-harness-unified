"""DEC-V61-202-SUB-M30-CYCLE1 · case_007 KCS VOF dogfood smoke.

Programmatically walks the dynamic frame through Step 1->5 on a
case_007-shape input. Captures the frame at each step + verifies:
  - Step 3 surfaces Gap #49 (phases missing) as rail info_gap
  - Step 4 surfaces Gap #48 (p_rgh) as bottom_card audit_finding
  - At every step transition >=1 frame slot differs from previous step

Output is a JSON trace + an analysis markdown.
"""
from __future__ import annotations

import json
from pathlib import Path

from ui.backend.schemas.workbench_frame import CaseStateSnapshot
from ui.backend.services.workbench_decide import decide


CASE_ID = "case_007_kcs_ship_vof_dogfood"

# Stage 1 of dogfood: fresh case, manifest declares minimal VOF, no
# 0/p_rgh yet on disk. Step 3 should surface "phases missing" gap;
# Step 4 should surface "p_rgh missing on disk" finding from bc_quality.
MANIFEST_STAGE_1 = {
    "case_id": CASE_ID,
    "case_family": "ship_vof",
    "solver_backend": "openfoam",
    "solver": "interFoam",
    "physics": {
        "regime": "transient_incompressible_turbulent_vof",
        "turbulence_model": "kOmegaSST",
    },
}

COMPLETENESS_STAGE_1 = {
    "case_id": CASE_ID,
    "case_kind": "imported_user",
    "ready_for_archive": False,
    "blocked_by_critical": 2,
    "present_count": 5,
    "total_count": 7,
    "percentage": 71.4,
    "missing": [
        {
            "field_path": "vof_contract.phases",
            "severity": "critical",
            "why": "interFoam requires vof_contract.phases declaration "
                   "(water, air)",
        },
        {
            "field_path": "bc_contract.phase_fields",
            "severity": "warning",
            "why": "interFoam expects 0/alpha.<phase[0]> to be enumerated",
        },
    ],
}

ARTIFACTS_STAGE_1 = {
    "mesh_report.json": {
        "n_cells": 1_200_000,
        "max_non_orthogonality": 65,
    },
    "bc_quality.json": {
        "verdict": "fail",
        "reason": "missing 0/p_rgh; interFoam ships hydrostatic pressure",
        "findings": [
            {
                "severity": "fail",
                "title": "Missing field p_rgh",
                "message": "interFoam ships 0/p_rgh (hydrostatic pressure), "
                           "not 0/p. Engine expects p_rgh.",
                "field_path": "bc_contract.pressure",
            },
            {
                "severity": "warn",
                "title": "Missing field alpha.water",
                "message": "interFoam needs 0/alpha.water BC declaration",
                "field_path": "bc_contract.phase_fields",
            },
        ],
    },
}


def _snapshot(step: int, focus_patch: str | None = None) -> CaseStateSnapshot:
    return CaseStateSnapshot(
        case_id=CASE_ID,
        step=step,
        manifest=MANIFEST_STAGE_1,
        artifacts=ARTIFACTS_STAGE_1,
        completeness=COMPLETENESS_STAGE_1,
        focus_patch=focus_patch,
    )


def _diff_summary(prev, curr):
    """One-line description of which slots differ between two frames."""
    if prev is None:
        return "[initial frame]"
    changed = []
    if prev.rail_primary != curr.rail_primary:
        changed.append("rail")
    if prev.viewport_overlays != curr.viewport_overlays:
        changed.append("overlays")
    if prev.bottom_cards != curr.bottom_cards:
        changed.append("cards")
    if prev.state_sha == curr.state_sha:
        changed.append("STATE_SHA_UNCHANGED")
    return ", ".join(changed) or "NONE"


def main():
    frames = []
    prev = None
    diffs = []

    for step in (1, 2, 3, 4, 5):
        state = _snapshot(step)
        frame = decide(state)
        diff = _diff_summary(prev, frame)
        frames.append({
            "step": step,
            "rail_kind": frame.rail_primary.kind,
            "rail_title": frame.rail_primary.title,
            "rail_field_path": frame.rail_primary.field_path,
            "overlay_kinds": [o.kind for o in frame.viewport_overlays],
            "card_kinds": [(c.kind, c.severity, c.title) for c in frame.bottom_cards],
            "state_sha_8": frame.state_sha[:8],
            "diff_from_prev": diff,
        })
        diffs.append(diff)
        prev = frame

    # Focus mutation test: same step + focus change should differ
    f_step4_no_focus = decide(_snapshot(4))
    f_step4_inlet = decide(_snapshot(4, focus_patch="inlet"))
    focus_diff = _diff_summary(f_step4_no_focus, f_step4_inlet)

    print("=== Dogfood Step 1->5 frame trace ===")
    print(json.dumps(frames, indent=2, ensure_ascii=False))
    print()
    print("=== Anti-pattern check (SSOT §8.4) ===")
    for i, d in enumerate(diffs[1:], start=2):
        status = "PASS" if d != "NONE" else "FAIL"
        print(f"  Step {i-1}->{i}: {d}  [{status}]")
    print(f"  Step 4 + focus_patch='inlet' delta: {focus_diff}")

    # Gap #48 check (SSOT §8.3)
    step4 = next(f for f in frames if f["step"] == 4)
    gap48 = any("p_rgh" in t for (_, _, t) in step4["card_kinds"])
    print(f"\n=== Gap #48 surface check (Step 4 bottom_cards) ===")
    print(f"  Found 'p_rgh' card: {gap48}  [{'PASS' if gap48 else 'FAIL'}]")

    # Gap #49 check
    step3 = next(f for f in frames if f["step"] == 3)
    gap49 = (step3["rail_kind"] == "info_gap"
             and "vof_contract.phases" in (step3["rail_field_path"] or ""))
    print(f"\n=== Gap #49 surface check (Step 3 rail.primary) ===")
    print(f"  rail=info_gap targeting vof_contract.phases: {gap49}  "
          f"[{'PASS' if gap49 else 'FAIL'}]")

    return frames


if __name__ == "__main__":
    main()

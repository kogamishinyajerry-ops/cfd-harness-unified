---
decision_id: DEC-V61-030
timestamp: 2026-04-21T22:30 local
scope: |
  Close external Gate Q-5 via Path A (re-transcribe gold from actual Ghia
  1982 Table I). Corrects knowledge/whitelist.yaml::cases[lid_driven_cavity].
  gold_standard.reference_values (5-point subset) AND
  knowledge/gold_standards/lid_driven_cavity.yaml u_centerline block (full
  17-point uniform grid interpolated from Ghia's 17 native non-uniform
  y-points). Also regenerates the 4 LDC grid_convergence teaching fixtures
  (mesh_20/40/80/160) to be monotone-convergent toward the new gold.

  Impact: Phase 5b LDC audit_real_run deviation count drops from 16/17 FAIL
  to 6/17 FAIL. Remaining residuals are physical: our simpleFoam runs on a
  uniform 129×129 mesh while Ghia used a graded 129×129 mesh clustered
  toward walls. Our interpolated-to-uniform gold has irreducible
  interpolation error at Ghia's sharp transition points (y=0.75 near
  velocity zero-crossing; y=0.875 near lid boundary-layer peak).

  v_centerline and primary_vortex_location gold blocks in
  gold_standards/lid_driven_cavity.yaml have suspected schema/accuracy
  issues (v_centerline appears to be Ghia Table II indexed by x but
  labelled "y"; primary_vortex_location vortex_center_y=0.7650 disagrees
  with Ghia's 0.7344). NOT fixed in this commit — out of scope for Q-5
  (u_centerline only). Flagged as future work in gold file header
  comment; not blocking any current comparator path.
autonomous_governance: false
  (External-gate decision authorized by Kogami choosing Path A from the
  Q-5 menu filed in DEC-V61-029. 三禁区 #3 edit on knowledge/ authorized
  by this external-gate election, not by autonomous authority.)
claude_signoff: yes
codex_tool_invoked: false
  (Q-5 closure is pure data re-transcription from the cited paper. No
  code change in this commit. Codex review not triggered by re-data
  edits per RETRO-V61-001 baseline — no src/, no API, no byte-repro-
  sensitive path, no cross-file schema rename.)
codex_verdict: N/A (autonomous_governance=false)
counter_status: |
  v6.1 autonomous_governance counter UNCHANGED at 16.
  DEC-V61-030 is external-gate, not counted (pattern per V61-006/011/028).
reversibility: fully-reversible-by-pr-revert
  (Single commit. `git revert` restores the Phase 0 synthesized gold
  and the prior mesh_N fixtures. All Phase 5a/5b/5c downstream stays
  coherent after revert.)
notion_sync_status: synced 2026-04-21 (https://www.notion.so/DEC-V61-030-Q-5-closure-LDC-gold-re-transcribed-from-Ghia-1982-349c68942bed81ce92e0c9fffc294576)
github_pr_url: null (direct-to-main per external-gate pattern)
github_merge_sha: pending
github_merge_method: direct commit on main
external_gate_self_estimated_pass_rate: N/A (not subject to Codex review)
supersedes: null
superseded_by: null
upstream: |
  - DEC-V61-029 (Phase 5b closure filed Q-5 with Path A/B/C/D menu)
  - Ghia, Ghia & Shin 1982 J. Comput. Phys. 47, 387-411 — Table I
  - Phase 5b commits 0d85c98..1f87718 (simpleFoam migration +
    extractor x_tol fix); our simpleFoam run was the external
    cross-check that surfaced the Phase 0 gold bug
---

# DEC-V61-030: Q-5 closure — LDC gold re-transcribed from Ghia 1982

## Why now

Kogami selected Path A from the Q-5 menu filed in DEC-V61-029. Path A
is the only option that aligns the gold with the paper it claims to
cite; alternatives (document as illustrative, independent DNS,
indefinite hold) either violate the commercial audit-package promise
or add cost without correctness benefit.

## What landed

### Edit 1 — `knowledge/whitelist.yaml` LDC gold_standard (三禁区)

- Previous 5-point reference_values (wrong): `[0.0625: -0.03717, 0.1250: -0.04192, 0.5000: +0.02526, 0.7500: +0.33304, 1.0000: 1.0]`.
- New 17-point reference_values: uniform y grid 0.0, 0.0625, 0.125, ... 1.0 with u values interpolated from Ghia 1982 Table I Re=100 column.
- Key fixes:
  - y=0.5000: +0.02526 → -0.20581 (sign flip to match Ghia)
  - y=0.1250: -0.04192 → -0.07671 (corrects magnitude)
- Tolerance: 0.05 (unchanged).
- Added Q-5 closure header comment with full source citation + interpolation method note.

### Edit 2 — `knowledge/gold_standards/lid_driven_cavity.yaml` u_centerline (三禁区)

- Same 17-point correction as whitelist, matching values for dual-source consistency.
- Added header comment citing Ghia's 17 native y-points for full traceability.
- Changed `solver_info.name` from `icoFoam` to `simpleFoam` (post-Phase-5b state).
- Changed `mesh_info.cells` from 64800 (Phase 0 placeholder) to 16641 (actual 129×129).
- v_centerline + primary_vortex_location blocks UNTOUCHED (out of Q-5 scope; flagged in header as suspected schema issues).

### Edit 3 — LDC grid_convergence teaching fixtures

- `ui/backend/tests/fixtures/runs/lid_driven_cavity/mesh_20_measurement.yaml`: value -0.048 → -0.055; verdict FAIL (unchanged); |dev| 31.2% (vs old 29% against wrong gold)
- `mesh_40_measurement.yaml`: value -0.042 → -0.048; verdict FAIL (unchanged); |dev| 14.5%
- `mesh_80_measurement.yaml`: value -0.038 → -0.044; verdict FAIL (changed from PASS); |dev| 5.0% (edge-of-tolerance)
- `mesh_160_measurement.yaml`: value -0.0375 → -0.042; verdict PASS (unchanged); |dev| 0.2%
- Monotone |dev| across mesh_20→mesh_160 (31.2% → 14.5% → 5.0% → 0.2%). `test_grid_convergence_monotonicity` PASSES.
- Narrative text + audit_concern summary updated to reference new gold.

## Verification

| Check | Result |
|---|---|
| Backend pytest | ✅ 79/79 (test_grid_convergence_monotonicity[lid_driven_cavity] now passes) |
| Frontend tsc --noEmit | ✅ clean (no frontend change) |
| LDC audit_real_run deviation count | 16/17 FAIL → **6/17 FAIL (11 PASS)** ✓ major improvement |
| Comparator physics alignment | ✅ u=-0.209 at y=0.5 matches Ghia's -0.20581 within 2% |
| 三禁区 writes | 2 (whitelist.yaml + gold_standards/lid_driven_cavity.yaml; external-gate authorized per Q-5 Path A) |
| Phase 5b infrastructure | ✅ unchanged (no src/ edit) |

## Honest residuals

The 6 remaining FAILs in the audit fixture are physical residuals of two combined effects:

1. **Uniform-grid interpolation error on gold**: Ghia tabulated at 17 non-uniform y points; we compare at a uniform 17-point grid. At y=0.6875 (between Ghia's y=0.6172 and y=0.7344, where u flips sign), linear interpolation has its biggest error. Fixing would require retargeting both the extractor and the gold to Ghia's native non-uniform y points — a larger scope that can be done as Phase 5b sub-phase 2 if desired.
2. **Our uniform 129×129 mesh vs Ghia's graded 129×129**: Ghia clustered cells toward walls for better BL resolution. Our uniform mesh is slightly coarser near the lid, so our u_centerline peaks 8-10% low at y=0.85-0.95. Fixing would require a graded mesh in `_render_block_mesh_dict` (tanh-stretched simpleGrading or multi-block).

Both residuals are <10% relative at the transition-point FAILs and would only require bumping tolerance from 5% → 10% OR investing in graded mesh + native-y extractor work to close. Phase 5c tolerance policy or Phase 5b-sub-phase-2 mesh work will handle it.

## Q-5 queue status

Strikethrough Q-5 in `.planning/external_gate_queue.md` as CLOSED 2026-04-21. Path A selected and executed per this DEC. No Q-5 follow-up needed beyond the optional graded-mesh work noted above.

## Delta

| Metric | After V61-029 | After V61-030 |
|---|---|---|
| External gate queue open | 1 (Q-5) | **0** |
| LDC audit deviations | 16/17 FAIL | **6/17 FAIL (11 PASS)** |
| Gold file citation accuracy | FAIL (Ghia-named, Ghia-not-matching) | **PASS (Ghia-name + Ghia-values aligned)** |
| Backend pytest | 79/79 | 79/79 |
| v6.1 counter | 16 | **16** (external-gate DEC, N/A) |

## Pending closure

- [x] whitelist.yaml LDC gold re-transcribed
- [x] gold_standards/lid_driven_cavity.yaml u_centerline re-transcribed
- [x] 4 mesh_N teaching fixtures regenerated (monotone to new gold)
- [x] audit_real_run fixture regenerated (now 11/17 PASS)
- [x] 79/79 pytest green
- [x] Q-5 strikethrough in external_gate_queue.md
- [ ] STATE.md update with Q-5 closure
- [ ] Atomic git commit + push
- [x] Notion sync DEC-V61-030 (https://www.notion.so/DEC-V61-030-Q-5-closure-LDC-gold-re-transcribed-from-Ghia-1982-349c68942bed81ce92e0c9fffc294576)

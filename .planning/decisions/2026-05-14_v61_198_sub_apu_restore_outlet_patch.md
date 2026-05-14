---
decision_id: DEC-V61-198-sub-apu-restore-outlet-patch
title: case_002a M-APU-RESTORE Tier 1 · apu_intake outlet patch restoration attempt · NEGATIVE finding · V78 pattern reconfirmed at small-closed-bubble scale
status: Accepted
parent_dec: V61-198
phase: APU bay case_002a Tier 1 optional · M-APU-RESTORE outlet-patch restoration
notion_sync_status: pending (session-end Accepted-batch)
parent_artifacts:
  - .planning/case_profiles/case_002a_RESUME.md (F4b CLOSED POSITIVE; "steady-state under correct outlet physics" Not validated open)
  - docs/openfoam_corpus/industrial_solver_findings_v_series.md (V75 partial, V77, V78, V84 follow-up #1)
  - .planning/2026-05-13_advisor_substrate_arc_plan.md (M-APU-RESTORE item)
  - ~/Desktop/apu-bay-ventilation/evidence/v33/REPORT.md (this session deliverable)
trigger: V84 F4b CLOSED POSITIVE solver run identified two root causes for p_rgh plateau 0.39-0.54: (a) missing apu_intake outlet patch (V75 phantom), (b) intrinsic unsteady buoyant+jet physics requiring buoyantPimpleFoam. Brief dispatched this session to attempt (a) via STL surgery, accepting confidence: low expectation. Attempt restored apu_intake watertight closure (partial V77 rollback for that body) but sHM still did not create apu_intake patch; mesh quality regressed (V78 pattern at smaller scale).
autonomous_governance: true
counter_impact: +1
codex_review_relay: SKIPPED (substrate STL edit + mesh rebuild, no main-repo schema modification, per v2.3 §2 risk-tier; case-level evidence sediment + advisor not touched)
kogami_review_path: SKIPPED (v2.3 §1 opt-in; user did not summon)
authored_by: Claude Code Opus 4.7 (1M context) sub-session
authored_at: 2026-05-14
confidence: high (negative finding grounded in full v33 mesh build + checkMesh log; quantitative regression on 7 metrics; root cause analysis explains refinement-scale vs feature-scale mismatch; v32 substrate state fully restored from backup; no destructive change to upstream)
---

# DEC-V61-198-sub-apu-restore-outlet-patch · NEGATIVE outcome closure

## 1. Why now

V84 F4b CLOSED POSITIVE (2026-05-13) ran buoyantSimpleFoam cleanly for 2689 SIMPLE iter on v32 mesh, validating DEC-V61-198's "solver execution from Claude Code Bash" pillar end-to-end. But p_rgh initial residual plateaued at **0.39–0.54** (steps 500–2689) — statistically stable but NOT numerically converged. V84 named two root causes: **(a) missing dedicated `apu_intake` outlet patch** (flow exits via `farfield_cylinder` zeroGradient — mass-conservative integrally but not locally; 6% cumulative continuity drift by step 2689), and **(b) intrinsic unsteady buoyant-plume + combustor-jet interaction** requiring transient buoyantPimpleFoam not steady SIMPLE.

The substrate arc plan (2026-05-13_advisor_substrate_arc_plan.md) listed M-APU-RESTORE as Tier 1 OPTIONAL: addressing (a) recovers correct outlet physics independently of (b). Brief dispatched 2026-05-14 with explicit `confidence: low expectation` clause, naming "STL surface surgery on body_1 louver per V75" as the intended intervention. This session executed the substrate work and produced a NEGATIVE finding.

## 2. Decision

**Tier 1 M-APU-RESTORE milestone closes NEGATIVE.** apu_intake outlet patch could not be restored by STL surgery within current sHM dict refinement scale (level 3-4 → 5-10 mm cells); root cause is feature-scale vs cell-scale mismatch, not watertightness. v32 substrate baseline fully restored from pre-surgery backup. F4b CLOSED POSITIVE artifacts (V84, V75 partial, V77/V78 lessons) remain valid. Fix-verification of V75 status flip from `partial` to `fix-verified` is **NOT achieved**; V75 remains `partial`.

## 3. What was done

1. **Diagnostic pre-flight**:
   - Loaded `inputs/cleaned_body_1.stl` (3472 tri) + `inputs/cleaned_apu_intake.stl` (68 tri) via trimesh.
   - bbox check: body_1 (x[64890–65206], y[1672–2190], z[−918, −343] mm) vs apu_intake (x[65221–65571], y[677–933], z[−416, 99] mm) — **no spatial overlap on any axis**; centroid distance 1.26 m.
   - **Brief's geometric premise "body_1 louver overlaps apu_intake" is incorrect.** body_1 is a separate component, not a containing louver. Real surgery target is apu_intake STL itself.
   - apu_intake topology: watertight closed body (euler=2, genus=0), volume 89.3 cm³, area 358 cm². Two opposing large face groups (8 tri / 99.75% area) + 60 small sealing facets.
   - v32 combined STL apu_intake region: **508 tri, non-watertight** (V77 F4a-strict isotropic remesh side-effect; `collapseflag=True` broke closure).

2. **Hypothesis**: sHM cannot bisect fluid domain with non-watertight surface → no patch created. Fix = restore watertight 68-tri version into combined STL.

3. **Surgery** (`case/constant/triSurface/cleaned_combined.stl`):
   - Backup: `cleaned_combined.v32_pre_apu_restore.stl` (308.7 MB).
   - Scale `inputs/cleaned_apu_intake.stl` mm→m (× 0.001) — bbox-exact match with v32 region.
   - Re-emit ASCII STL region (68 facets), regex-replace apu_intake block in combined STL.
   - Verify: 28 solids total preserved; apu_intake region = 68 facets watertight.

4. **v33 build** (full `bash scripts/06_run_mesh.sh`): surfaceFeatureExtract + blockMesh + snappyHexMesh -overwrite + checkMesh. ~30 min on Apple Silicon Docker (`opencfd/openfoam-default:2312`). Completed without FATAL.

5. **Verification**: `constant/polyMesh/boundary` shows **27 patches, apu_intake still absent** — phantom-patch state unchanged from v32. Mesh quality regressed:

   | metric | v32 baseline | v33 attempt | delta |
   |---|---|---|---|
   | cells | 3.10M | 3.98M | +28% |
   | patches | 27 (apu_intake phantom) | 27 (apu_intake phantom) | **no change** |
   | max_skewness | 6.875 | 7.966 | +16% worse |
   | skew faces | 20 | 69 | +245% worse |
   | concave cells | 95 | 147,036 | 1,547× worse |
   | under-determined cells | 46 | 118 | +156% worse |
   | duplicate faces | 0 | 9 | regressed |
   | short edges | 0 | 4 | regressed |
   | warped faces | 0 | 477 | regressed |

6. **Restore** (per brief hard constraint "v32 polyMesh 不破坏"):
   - `case/constant/polyMesh/` restored from `polyMesh.v32_backup_pre_v33`.
   - `case/constant/triSurface/cleaned_combined.stl` restored from pre-surgery backup.
   - v33 failed polyMesh preserved as `polyMesh.v33_apu_restore_failed` for forensic value.

7. **Solver run SKIPPED**: with apu_intake patch still absent, physics is identical to F4b (flow still exits via farfield_cylinder zeroGradient). No expected p_rgh trajectory delta vs F4b. Running solver would consume ~3 h compute for predictably-null finding. Decision conforms to V78 lesson: "don't keep poking after the mesh-quality regression confirms the surgery class is wrong."

## 4. Root cause (the real one, replacing the brief's hypothesis)

sHM refinement `apu_intake { level (3 4); }` produces cells ~5–10 mm. apu_intake closed-bubble interior is 89 cm³ in a 350×256×515 mm bbox — fill ratio 0.2%, effectively a thin envelope. At level-4 cell size, **the bubble interior contains too few cells (~1–8) to seed a coherent fluid sub-region**, so castellation merges the bubble interior into the ambient `body_1` / `Outer_Surf` cell pool before snap stage runs. Watertightness restoration alone cannot recover the patch because the per-cell resolution at the bubble scale is below sHM's effective patch-creation threshold for closed sub-volumes.

This is a **smaller-scale variant of V78**: STL surgery on the wrong scope regresses mesh quality. V78 was about bbox shell-punch on open shells (50–500 mm scale); V95 (this finding, candidate row) extends the lesson to closed-bubble watertightness restoration at sub-feature-scale resolution.

## 5. What unblocks a real fix (NOT pursued this session)

Ranked least-to-most-invasive:

a. **Solver-side BC fix** (recommended for future session): use `createPatch` post-processing to extract a sub-region of `farfield_cylinder` localized to apu_intake bbox, rename to `apu_intake_outlet`, apply `flowRateOutletVelocity` BC. No mesh rebuild. Loses the original CATIA-meaningful patch identity but recovers correct outlet physics.

b. **Refinement bump**: `apu_intake refinementSurfaces level (3 4) → (5 6)` (cell size ~1.25–2.5 mm). Risk: ~3–4× total cell-count growth (~12M cells), may exceed `maxGlobalCells 11M` cap; new mesh-quality hot-spots likely (V76 squeezing-balloon).

c. **CAD redesign**: replace apu_intake STL with a thick (≥30 mm) closed envelope shifted into the bay airflow path. Out of scope — would require CATIA-level intervention upstream.

d. **Accept the residual + change solver**: keep F4b's farfield-as-outlet physics, switch to `buoyantPimpleFoam` (transient) per V84 root cause (b), accept ~6% mass deficit. Probably the right long-term answer given V84's "intrinsic unsteadiness" diagnosis.

## 6. Sediment

- `~/Desktop/apu-bay-ventilation/evidence/v33/REPORT.md` — full evidence report with quantitative tables.
- `docs/openfoam_corpus/industrial_solver_findings_v_series.md` — V95 NEW row (STL surgery for small-closed-bubble outlet recovery · negative-finding methodology; V78 cross-cut).
- `.planning/methodology/industrial_case_solver_findings.md` — mirror append of V95.
- V75 status: stays `partial`; no `fix-verified` flip. Status amendment NOT written (V75 already accurately describes "wall broken at v30, apu_intake still phantom-patch downstream"; no narrative inversion needed).

## 7. Counter / governance

- v2.3 §1 spike-class: does not qualify (case-level STL surgery is closer to sub-DEC than spike — substrate change, non-trivial diagnostic chain, full V-row produced).
- v2.3 §2 1-sync-trigger: does not fire (no auth / signing / security boundary; substrate-only edit; advisor code untouched).
- v2.3 §3 Kogami opt-in: SKIPPED (user did not summon for this Tier 1 optional milestone).
- Counter +1 (autonomous_governance true; no external gate consulted).

## 8. Main-session reconciliation requests

Out-of-scope for this sub-session (per brief hard constraint "不更新 .planning/ARC-GOAL.md"); flagged for main-session ARC-GOAL update:

1. `[x] M-APU-RESTORE` — Tier 1 optional CLOSED NEGATIVE; V95 sediment delivered; V75 status unchanged at `partial`.
2. Brief's geometric premise "body_1 louver overlaps apu_intake" was incorrect (1.26 m apart, no bbox overlap on any axis). Future briefs that touch this geometry should verify bbox overlap before naming "louver overlap" as surgery target. Optional retro entry candidate (low priority).
3. If a future session pursues solver-side BC fix (option 5a above), it would deliver V75 `fix-verified` flip + recover correct outlet physics — but does not unlock numerically-converged steady state (V84 root cause (b) still applies; needs PIMPLE).

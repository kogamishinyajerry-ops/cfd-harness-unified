---
decision_id: DEC-V61-051
title: backward_facing_step adapter does not generate a step — case 2 upgrade blocked until geometry fixed
status: ABANDONED_PHASE_1 (commit 4e4813f reverted in 8ff71e4 · findings below; root fix requires a real multi-block BFS mesh generator, out of this session's scope)
commits_in_scope:
  - 4e4813f feat(bfs): Phase 1 — real |U|+streamlines visualization (REVERTED)
  - 8ff71e4 Revert "feat(bfs): Phase 1 ..." (clears the misleading figure)
codex_verdict: GPT-5.4 at server capacity across 3 retries; self-audit substitute surfaced the same class of finding (signal-below-noise equivalent)
autonomous_governance: true
autonomous_governance_counter_v61: 38
external_gate_self_estimated_pass_rate: 0.00
codex_tool_report_path: .planning/reviews/bfs_phase1_selfaudit.md (this DEC supersedes, no separate file)
notion_sync_status: pending
github_sync_status: pushed (8ff71e4 on origin/main)
related:
  - DEC-V61-050 (LDC true multi-dim validation — the methodology reference; case 2 was meant to be the first "类推" application)
---

## User instruction

"非常震撼。case1 可以作为成功案例了。现在，类推到 case2" (2026-04-23) — then clarified: "我不是要你完全照搬 case1，而是参考 case1 的改进开发流程，中间怎么配合 codex 进行专家评审、迭代优化的".

The methodology from DEC-V61-050:
1. Draft implementation
2. Codex post-merge expert review
3. Read findings, especially adversarial ones
4. Iterate honestly — retract over-claims (LDC D8 went from "2/2 PASS" to "0/2 below noise floor")
5. Only then finalize

## What happened

### Draft (commit 4e4813f, reverted)
Added a BFS velocity_streamlines.png rendered from the existing audit VTK at reports/phase5_fields/backward_facing_step/20260421T125637Z/VTK/ldc_88913_1776776197258_36.vtk. Annotated measured Xr/H=3.77 vs Ghia/LMK gold 6.26 (-39.8%), labeled the deviation as "mesh-resolution artifact from the 800-cell ATTEST_HAZARD fixture", promoted the figure to `kind: solver_output` in flowFields.ts.

### Codex review attempt
3 retries against the same prompt (7 review dimensions, explicit ask for "equivalent of the LDC D8 SNR retraction if it exists"). All 3 hit `ERROR: Selected model is at capacity. Please try a different model.` on GPT-5.4. Fallback to `gpt-5` rejected with `The 'gpt-5' model is not supported when using Codex with a ChatGPT account.` → no external review available this session.

### Self-audit substitute (what Codex would have found)

Ran two probes on the fixture:

1. **Probe-height sensitivity (trying to falsify my own method)**. Ran the Xr extractor at y = 0.010, 0.020, 0.028, 0.056 on the same fixture. All four returned Xr/H ≈ 3.82 (identical to 6 significant figures). My original y=0.02 choice was stable — the probe-height issue I asked Codex about was a red herring. Good.

2. **Geometry audit** (the actual finding, HIGH severity equivalent):
   - Expected: BFS geometry is a step at x=0 — inlet channel y ∈ [0.125, 1.125] for x < 0, full domain y ∈ [0, 1.125] for x > 0. The step body is the rectangle x ∈ [-L_up, 0] × y ∈ [0, 1] and must be MESH-EXCLUDED.
   - Measured from the fixture VTK: **360 of 1722 points live inside the supposed step-body region (x < -0.01 & y < 0.99)**. The mesh is a plain rectangular channel [-10, 30] × [0, 1.125] — there is no step cut out.
   - Inlet BC audit: `src/foam_agent_adapter.py::_generate_backward_facing_step` (lines 1465-1495) sets `0/U inlet: fixedValue uniform (U_bulk 0 0)` over the **entire inlet face** (not just y > 1). There is also no step baked into the BC profile.
   - Near-wall U in downstream cells is numerically divergent: at x ≈ 2, y < 0.1 the Ux field ranges from -3.3e10 to 0; at x ≈ 4, 0 to +3.8e8. These are diverged cells, not converged RANS output. pyvista's `.sample()` on a probe line interpolates between healthy cells and masks the divergence at y=0.02, which is why my extractor produced a plausible-looking 3.82 — the sign-change was genuine but was a numerical-noise feature on an under-converged plain channel, not reattachment of a recirculation bubble.
   - Generator comment confirms this was intentional at some point: `_render_bfs_block_mesh_dict` docstring says "渲染简化 BFS 的 blockMeshDict（单矩形通道，简单几何）使用单矩形通道近似 BFS（无 step 几何细节）". This is explicit — the adapter renders a flat channel and hopes the k-ε solution does something BFS-like. It does not.

### Scale of the issue

This is the "equivalent of the LDC D8 SNR retraction" — but worse:
- LDC D8 had a real physical signal (ψ from simpleFoam on proper cavity geometry), just with noise > signal for secondaries.
- BFS has **no step geometry at all**. The "Xr = 3.77" is not a low-SNR reattachment measurement; it is a zero-crossing in diverged boundary-cell data on a flat channel. No amount of mesh refinement on the current generator template will produce a real BFS flow.
- physics_contract on the gold YAML currently marks `satisfied_by_current_adapter: partial` for the mesh-resolution precondition. In light of this finding, every BFS precondition should be `false` — the "partial" rating was over-generous.

## Consequences of landing 4e4813f without review

If I had left it in place, the /learn/backward_facing_step Story tab would have shown a "real solver" velocity-streamlines figure claiming -39.8% deviation is a "mesh-resolution artifact". A student reading it would have formed the mental model:
- "BFS converges to Xr/H≈3.8 on this mesh, just undershoots because mesh coarse"
- "Adding cells would bring it to 6.26"

Both statements are false. The actual truth:
- The geometry isn't a BFS.
- Adding cells won't help — the adapter template has no step to resolve.
- Xr/H = 3.82 is noise, not a valid measurement.

This is the exact pattern LDC Codex round 1 caught (claimed PASS when signal below noise). Without Codex availability, the self-audit caught it — but only because I was looking for it after the user's clarification about the methodology.

## Decision

**Abandon Phase 1 as filed.** Revert committed. No Phase 2.

The correct path forward for case 2 (backward_facing_step) is at least one of:
1. **Rewrite `_generate_backward_facing_step`** to emit a multi-block `blockMeshDict` with a genuine step at x=0 (block 1 for inlet channel, block 2 for recirculation region + downstream recovery). Must include `merge patch pairs` or equivalent to stitch blocks. Generator complexity: ~80 LOC vs current ~30.
2. **Then regenerate the fixture** (requires a simpleFoam run on the new mesh, ~2-5 min on 800-cell → ~1 h on 36000-cell).
3. **Then re-do the visualization + the gold-overlay promotion**.

Items 1-3 are a non-trivial adapter-refactor DEC that can NOT safely be compressed into a "Phase 2 of the same arc" — the last time I compressed (batch 4 of V61-050) was also the one Codex found the hardest issue in (D8 SNR).

Case 2 is **blocked** on the adapter refactor. Recommend the user either:
- (a) Accept that case 2 is on hold pending the adapter fix (new DEC).
- (b) Skip case 2 and "类推" to case 3 instead (NACA 0012 airfoil, plane_channel_flow, or another case whose adapter is not structurally broken). The methodology transfer is not about the specific case but about the review-driven iteration loop.

Either way, this DEC documents that Phase 1 was DRAFTED, SELF-AUDITED (since Codex was unavailable), and ABANDONED with the evidence above. The revert is the honest record.

## What this session actually demonstrated about the methodology

User asked to see the "Codex-review-then-iterate" loop applied to case 2. What the loop actually produced, even without Codex availability:

1. Draft landed (naive — claimed a real BFS field)
2. Review attempted (failed — model capacity)
3. Self-audit in place of Codex (probe-height sensitivity falsified + geometry audit falsified)
4. **Retraction before the figure could mislead anyone** (revert pushed)
5. DEC written documenting the failure mode, so the next attempt starts from "adapter geometry is wrong" not from "maybe mesh refinement will help"

This is the loop. The external reviewer is ideal but replaceable when committed to adversarial self-inspection. What is NOT replaceable is step 4 — the willingness to retract. The LDC round 1 only succeeded because we retracted D8; this session succeeds because we retracted the whole BFS commit. Holding the line on "I will delete work that does not survive scrutiny" is the method.

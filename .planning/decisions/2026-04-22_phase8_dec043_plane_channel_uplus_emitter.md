---
decision_id: DEC-V61-043
timestamp: 2026-04-22T17:15 local
scope: |
  Phase 8 Sprint 1 — plane_channel_flow emits u+/y+ profile against
  Moser DNS gold. Adds wallShearStress + line-sampler FOs to the
  case controlDict, new src/plane_channel_uplus_emitter.py that reads
  postProcessing output and computes u_τ/u+/y+, wires into
  _extract_plane_channel_profile at foam_agent_adapter.py:7988.
  Comparator already G2-ready from DEC-V61-036c.

autonomous_governance: true
claude_signoff: yes
codex_tool_invoked: yes
codex_rounds: 2
codex_verdict: APPROVED (round 2, 2026-04-22)
counter_status: |
  v6.1 autonomous_governance counter 29 → 30. Next retro at 30 — will
  trigger arc-size retrospective after Codex approval.
reversibility: fully-reversible — new emitter module + FO block in
  controlDict + extractor extension + new tests. Revert = remove
  src/plane_channel_uplus_emitter.py + revert the 2 foam_agent_adapter
  edits + drop functions{} block from controlDict.
notion_sync_status: pending
github_pr_url: null (direct-to-main after Codex)
external_gate_self_estimated_pass_rate: 0.70
  (Pattern is now well-established from DEC-042 — FO plumbing +
  case_dir threading + fail-closed on malformed input + fail-quiet
  on absent input. Main residual risks: (a) OpenFOAM 10 vs v2012+
  wallShearStress.dat format differences, (b) half-channel fold
  edge case when y_wall == h exactly.)
supersedes: null
superseded_by: null
upstream: |
  - DEC-V61-036c G2 — comparator already understands
    u_mean_profile_y_plus axis; no comparator changes needed.
  - DEC-V61-042 — established BC-plumbing pattern through
    task_spec.boundary_conditions + fail-closed discipline.
  - User 2026-04-22: "PASS-washing" review; plane_channel was one of
    the cases extracting U_max_approx and comparator-passing against
    a scalar that didn't match Moser u+/y+ gold.
---

# DEC-V61-043: plane_channel u_τ/u+/y+ emitter

## Why now

plane_channel_flow currently extracts `U_max_approx` (a scalar) plus
`u_mean_profile` normalized by `U_max` — not by `u_τ`. The comparator's
G2 gold-overlay path expects `u_plus` values at anchor `y_plus` points
(Moser DNS tables). The extractor wasn't speaking the right language,
so the comparator fell through to scalar-key fallback and `U_max_approx`
was being compared against Moser u+ values (meaningless pair-up).

Fix: emit `u_mean_profile` as u+ values keyed by `u_mean_profile_y_plus`
— exactly what the G2 alias table expects. Compute via OpenFOAM's
native wallShearStress FO + a line-uniform sampler in the controlDict
`functions{}` block, then normalize in a new helper module.

## What lands

1. **New `src/plane_channel_uplus_emitter.py`** (~290 LOC):
   - `PlaneChannelEmitterError` — fail-loud on malformed FO output.
   - `PlaneChannelNormalizedProfile` frozen dataclass (tuples for
     safe reuse across callers).
   - `_read_wall_shear_stress` / `_read_uline_profile` parsers.
     Handle multiple parenthesized 3-vectors, comments, blank lines.
   - `_latest_time_dir` picks numerically-largest subdirectory.
   - `compute_normalized_profile`: takes raw τ_w + U(y), returns
     u_τ/Re_τ/u+/y+. Half-channel fold (y_wall = min(|y-bot|, |y-top|)).
     Drops points past centerline.
   - `emit_uplus_profile`: end-to-end convenience wrapper. Returns
     None when postProcessing is absent; raises on corruption.

2. **Generator side** (`_generate_steady_internal_channel`):
   - Plumbs `channel_D`, `channel_half_height`, `nu`, `U_bulk` into
     `task_spec.boundary_conditions`.
   - Injects `functions{}` block into controlDict with:
     - `wallShearStress` on patches `(walls)`, writeControl=writeTime.
     - `uLine` sets FO: line-uniform sampler along y at x=0, 129 pts.

3. **Extractor** (`_extract_plane_channel_profile`):
   - New `case_dir: Optional[Path]` kwarg threaded from call site.
   - Primary path: call `emit_uplus_profile(case_dir, nu, half_h)`;
     if success, merge into key_quantities with
     `u_mean_profile_source = "wallShearStress_fo_v1"`.
   - Malformed input surfaces `u_mean_profile_emitter_error` key —
     fails closed rather than silently degrading (Codex DEC-040
     round-2 pattern).
   - Fallback: existing cell-centre U_max path, now tagged with
     `u_mean_profile_source = "cell_centre_fallback"` so downstream
     can tell which path fired.

4. **Tests** (`tests/test_plane_channel_uplus_emitter.py`, 18 tests):
   - Analytical known-τ_w recovery (machine-precision).
   - Log-law U(y) roundtrip at y+={30, 100} within 5%.
   - Half-channel fold: upper-half points correctly mapped (not
     double-counted).
   - Parsers: multi-vector rows, comments, blank lines, sparse
     files, non-numeric rows.
   - Fail-closed: absent postProcessing → None; malformed → raise.
   - Input validation: τ_w ≤ 0, ν ≤ 0, h ≤ 0 all raise.

## Out of scope — tracked separately

- **Physics correctness**: icoFoam runs LAMINAR at Re=5600; gold is
  Moser DNS. Even with the correct emitter, the case will FAIL
  against gold (expected — DEC-V61-043 makes the FAIL honest rather
  than PASS-washing via scalar substitution). A real DNS run needs a
  solver swap + streamwise-periodic BC + much finer mesh; separate
  DEC when/if that work is scoped.
- **Fixture regeneration**: Phase 5a audit fixture still pins the
  OLD `U_max_approx` measurement. Requires Docker+OpenFOAM re-run.
- **Non-icoFoam cases**: buoyantFoam uses dynamic viscosity, so
  `u_τ = sqrt(τ_w/ρ)` (not `sqrt(τ_w)`). Emitter comments flag this
  explicitly so future ports don't double-normalize.

## Live verification

```
tests/test_plane_channel_uplus_emitter.py ................. 18 passed
tests/test_wall_gradient.py ..................................11 passed
tests/test_dec042_extractor_integration.py .................. 5 passed
ui/backend/tests/ ........................................... 201 passed
```

Total 235/235 green, up from 220 (DEC-042 closure).

## Counter + Codex

29 → 30. **Retro threshold reached** — arc-size retrospective
required per RETRO-V61-001 cadence (counter ≥ 20 OR Phase complete
OR CHANGES_REQUIRED incident — counter-driven this time). Will land
after Codex approves DEC-043.

Self-pass 0.70. Codex pre-merge per RETRO-V61-001 — triggers:
- New CFD-extractor code path
- `foam_agent_adapter.py` > 5 LOC (new FO block + BC plumbing + extractor extension)
- New shared module

## Related

- DEC-V61-036c — comparator G2 canonical alias (already ready)
- DEC-V61-042 — BC-plumbing pattern + fail-closed discipline
- DEC-V61-044 (next) — NACA C3 surface sampler uses same FO-in-
  controlDict pattern established here

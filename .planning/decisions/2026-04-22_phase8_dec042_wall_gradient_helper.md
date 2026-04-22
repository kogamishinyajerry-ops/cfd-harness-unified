---
decision_id: DEC-V61-042
timestamp: 2026-04-22T15:30 local
scope: |
  Phase 8 Sprint 1 — shared 3-point one-sided wall-gradient stencil
  fixing Nu extraction for 3 CFD cases with one root-cause fix:
  differential_heated_cavity (was +29% over gold), impinging_jet (was
  -6000× under gold via wrong-axis radial differencing), and RBC (was
  +151% — only the extractor half fixed; RBC's side-heated geometry
  bug is out of scope). Adds src/wall_gradient.py with a Fornberg
  non-uniform 3-point stencil + BC contract enforcement, plumbs
  wall_coord / wall_value / wall_bc_type through the generators'
  task_spec.boundary_conditions, rewrites the 3 extractors to use it,
  deletes dead code (_extract_rayleigh_benard_nusselt, the redundant
  midPlaneT secondary Nu path).

autonomous_governance: true
claude_signoff: yes
codex_tool_invoked: yes
codex_rounds: 4
codex_verdict: APPROVED (round 4, 2026-04-22)
counter_status: |
  v6.1 autonomous_governance counter 28 → 29. Next retro at 30.
reversibility: fully-reversible — new module + new tests + explicit
  generator plumbing. Revert = remove src/wall_gradient.py + restore
  3 extractor bodies + remove BC metadata lines.
notion_sync_status: pending
github_pr_url: null (direct-to-main after Codex)
external_gate_self_estimated_pass_rate: 0.55
  (Honest: BC plumbing + generator wiring + 3 extractor rewrites +
  RBC-geometry-scope-split + dead-code deletion all compound. Codex
  has reliably caught one more item per round on comparable DECs.
  Brief explicitly flagged fail-closed discipline + wall_coord
  provenance + delete-not-retain dead fallbacks as primary
  round-1 risks.)
supersedes: null
superseded_by: null
upstream: |
  - User 2026-04-22 deep-review: "PASS-washing in 3 Nu-emitting cases"
  - DEC-V61-036/036b/036c ecosystem — hard-fail concern wiring
  - DEC-V61-039/040 — established the 3-verdict honest-FAIL pattern
---

# DEC-V61-042: shared wall-gradient helper

## Why now

Three cases were independently reporting wrong Nusselt numbers for the
same systemic reason: each extractor used its own 1-point finite-
difference between two interior cells, giving the gradient at their
midpoint, not at the wall. Impinging-jet was worse still — it
differenced RADIALLY across a fixedValue plate, where gradients are ≈0
by symmetry, producing a -6000× under-read.

Fixing three extractors by three independent ad-hoc patches would be
both fragile and disrespectful of the CFD: the right answer is one
shared stencil that does the math properly once. This DEC delivers
that helper.

## What lands

### New infrastructure
1. **`src/wall_gradient.py`** (~130 LOC):
   - `BCContractViolation` exception — callers fail closed rather than
     silently return a wrong number when BC metadata is malformed or
     geometry is non-monotonic.
   - `WallGradientStencil` frozen dataclass: Fornberg non-uniform
     3-point one-sided formula, O(h²) accurate, exact for quadratic
     fields, reduces to uniform-spacing textbook (-3,4,-1)/(2h) when
     h₂=2h₁.
   - `extract_wall_gradient()` convenience wrapper that selects the 2
     nearest interior cells, validates contract, returns `f'(wall)`.
   - `fixedGradient` BC short-circuit: the BC IS the gradient — a
     stencil over interior cells would silently shadow it.

2. **`tests/test_wall_gradient.py`** (11 tests):
   - Linear & quadratic fields: stencil exact to 1e-12.
   - Exponential BL: 3-point within 10%, 1-point worse (quantified).
   - fixedGradient BC: returns BC value verbatim; missing value raises.
   - Error paths: unknown BC type, <2 cells, length mismatch, wall
     inside/above cells — all raise BCContractViolation.
   - Descending-coord input is sorted internally.

### Extractor rewrites
3. **`_extract_nc_nusselt`** (DHC/RBC/NC-Cavity path):
   - Reads wall_coord_hot / T_hot_wall / wall_bc_type from
     task_spec.boundary_conditions.
   - Fails closed silently when metadata absent — absence of
     `nusselt_number` is the signal that DEC-036 G1's
     MISSING_TARGET_QUANTITY concern fires on at the comparator.
     No extractor-internal flags leak into key_quantities (Codex
     round-1 FLAG 1 closure).
   - Applies helper to each y-layer's x-profile, averages |grad|.
   - Sets `nusselt_number_source = "wall_gradient_stencil_3pt"`.

4. **`_extract_jet_nusselt`** (impinging jet):
   - Plate is at cy_max (jet axial direction = OpenFOAM's middle slot).
     Wall-normal coord flipped (`n = wall_cy - cy`) so stencil's
     `wall < coord[0] < coord[1]` invariant holds with wall at n=0.
   - Bins cells by radial position r=|cx|, applies stencil per-bin.
   - Stagnation Nu is the first (smallest r) bin.
   - Delta_T now computed from plumbed T_plate + T_inlet (no magic
     number 20.0).

### Generator plumbing
5. **`_generate_natural_convection_cavity`**: writes
   `wall_coord_hot=0.0`, `wall_coord_cold=L`, `T_hot_wall=305.0`,
   `T_cold_wall=295.0`, `wall_bc_type="fixedValue"` into
   `task_spec.boundary_conditions`.

6. **`_generate_impinging_jet`**: writes `wall_coord_plate=z_max`,
   `T_plate=290.0`, `T_inlet=310.0`, `D_nozzle=0.05`,
   `wall_bc_type="fixedValue"`.

### Dead-code deletion
7. Removed `_extract_rayleigh_benard_nusselt` at 8319-8378 — defined
   but never dispatched; would re-introduce the 1-point failure mode
   as a silent fallback when the RBC-geometry fix eventually lands.
8. Removed the redundant secondary NC-Cavity path in
   `_parse_solver_log` that differenced `midPlaneT` — dead in real
   runs (sample FO not executed) but a silent-substitution landmine
   if `midPlaneT` were ever populated by a parallel sampling path.

### Integration tests
9. **`tests/test_dec042_extractor_integration.py`** (5 tests):
   - NC extractor fails closed without BC metadata.
   - NC extractor exact on linear T(x).
   - IJ extractor fails closed without BC metadata.
   - IJ extractor recovers known-gradient on exponential BL at
     single radial bin.
   - IJ extractor skips radial bins with <2 cells without raising.

### Updated existing tests
10. `tests/test_foam_agent_adapter.py`: two existing NC-Nu tests
    updated to plumb BC metadata and use LINEAR profiles where the
    stencil is exact (more maintainable than tracking float
    arithmetic); added one new fail-closed test.

## Out of scope — tracked separately

- **RBC geometry mismatch**: `_generate_natural_convection_cavity`
  creates a SIDE-heated cavity for both DHC and RBC cases, but RBC
  physically requires a BOTTOM-heated / TOP-cooled configuration with
  gravity aligned vertically. Even with the correct extractor, RBC
  can only PASS if that generator mismatch is fixed or RBC is
  delisted. DEC-V61-042 makes the RBC measurement *less wrong*
  (replaces 1-point error with 3-point) but does not make it correct.
  A follow-up DEC must either: (a) add an RBC-specific generator
  branch with bottom-heating, or (b) remove RBC from the whitelist
  until that branch is available.

- **Fixture regeneration**: DHC / RBC / impinging_jet audit-real-run
  fixtures will shift once `scripts/phase5_audit_run.py` is re-run
  (Docker + OpenFOAM required). Fixtures currently on disk reflect
  the OLD extractor output. Until regen, the fixtures are stale and
  `test_phase5_byte_repro.py` will still pass because it pins the old
  bytes — but the numbers no longer reflect the live extractor. Flag
  explicitly so reviewers know this landing does not include fixture
  refresh.

- **wallGradient FO (Tier A)**: the CFD-correct answer is to use
  OpenFOAM's native `wallGradient` function object, which operates on
  the wall face with proper ordered-surface calculus. This DEC ships
  the cell-centre 3-point fallback (Tier B). Tier A is a follow-up.

## Live verification

Post-commit fabd70a + round-1 fixes:

```
tests/test_wall_gradient.py ....................... 11 passed
tests/test_dec042_extractor_integration.py ........  5 passed
tests/test_foam_agent_adapter.py -k nc_nusselt .....  3 passed
ui/backend/tests/ ..................................201 passed
```

Added 16 new green tests in DEC-042 (11 stencil + 5 integration).
Two legacy NC-Nu tests rewritten to pass BC metadata + use
linear-exact profiles. No regressions against pre-existing green
suite.

Direct API check shows fail-closed behavior fires correctly:
- NC extractor without BC metadata → no nusselt_number emitted.
- IJ extractor without BC metadata → no nusselt_number emitted.
- Neither leaks extractor-internal diagnostic keys into key_quantities
  (Codex round-1 FLAG 1 closure). Absence of nusselt_number IS the
  signal; DEC-036 G1 MISSING_TARGET_QUANTITY fires at the comparator.

## Counter + Codex

28 → 29. Self-pass 0.55 (honest). Codex pre-merge mandatory per
RETRO-V61-001 — hits multiple triggers:
- CFD extractor semantics change across 3 cases
- `foam_agent_adapter.py` >5 LOC change (new BC plumbing + 2
  rewrites + dead-code removal + secondary-path removal)
- New shared module (`src/wall_gradient.py`)
- Multiple fail-closed paths (Codex reviewed DEC-040's similar
  closure in round 2 and found a subtle remaining drift vector —
  expect similar scrutiny here)

## Related

- Upstream: DEC-V61-036 G1 (MISSING_TARGET_QUANTITY hard-fail)
- Sibling: DEC-V61-043 (plane_channel u_τ emitter — same BC-plumbing
  pattern, different cycle)
- Downstream: DEC-V61-042b (RBC bottom-heated geometry, TBD)

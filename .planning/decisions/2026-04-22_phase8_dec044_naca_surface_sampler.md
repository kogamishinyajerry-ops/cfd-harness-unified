---
decision_id: DEC-V61-044
timestamp: 2026-04-22T18:30 local
scope: |
  Phase 8 Sprint 1 — NACA0012 emits a proper Cp(x/c) profile from
  in-solver `surfaces` function object instead of relying on volume-
  cell band averaging (which attenuated Cp magnitudes 30-50%). Adds
  new src/airfoil_surface_sampler.py + `functions{}` block in NACA
  controlDict + rewrite of _populate_naca_cp_from_sampledict to
  prefer the FO path. Comparator already profile-ready.

autonomous_governance: true
claude_signoff: yes
codex_tool_invoked: yes
codex_rounds: 3
codex_verdict: APPROVED (round 3, 2026-04-22)
counter_status: |
  v6.1 autonomous_governance counter 30 → 31. Arc-size retro was
  due at 30; still deferred until after Codex approves DEC-044 and
  DEC-041 lands.
reversibility: fully-reversible — new sampler module + new FO block
  in NACA controlDict + extractor extension. Revert = remove
  src/airfoil_surface_sampler.py + drop functions{} block + restore
  the old sampleDict-only _populate_naca_cp_from_sampledict body.
notion_sync_status: pending
github_pr_url: null (direct-to-main after Codex)
external_gate_self_estimated_pass_rate: 0.75
  (Pattern now well-established from DEC-042/043. Remaining risks:
  (a) patch-name sensitivity — `aerofoil` vs `airfoil` British/US
  spelling trap that could silently produce zero faces, (b) 2D
  thin-span duplicate faces — handled via (x, z) dedup keyed on
  rounded coords, but depends on the rounding tolerance being
  right relative to mesh resolution, (c) trailing-edge degeneracy
  at x/c≈1.0 where thickness collapses to a line.)
supersedes: null
superseded_by: null
upstream: |
  - DEC-V61-036c — comparator profile-alignment for Cp already
    G2-ready; no comparator changes.
  - DEC-V61-042 — BC-plumbing pattern (chord, U_inf, rho, p_inf
    through task_spec.boundary_conditions).
  - DEC-V61-043 — FO-in-controlDict-functions pattern established
    for plane_channel; this DEC reuses it for NACA.
  - docs/design/c3_sampling_strategy_design.md — original C3
    recommendation was Option A (surfaces FO); NACA had partial
    Option B (sampleDict points) wired, but it was orphaned at
    runtime since the executor's postProcess -funcs invocation
    doesn't include `sample`. DEC-V61-044 is the overdue migration.
---

# DEC-V61-044: NACA C3 surface Cp sampler

## Why now

NACA0012 gold is a Cp(x/c) profile with anchor points at x/c ∈
{0, 0.3, 1.0} expecting Cp ∈ {1.0, -0.5, 0.2}. Current extractor
produced Cp values 30-50% attenuated (0.47, -0.34, 0.11) because the
`_extract_airfoil_cp` volume-cell band-averager samples cells 2-8%
chord away from the actual surface and the pressure gradient near the
surface isn't captured properly at that distance.

The "correct" fix was already partially scoped in docs (Option A =
surfaces FO) but never fully wired. NACA had a sampleDict emitted at
generator time but the executor's `postProcess -funcs '(writeObjects
writeCellCentres)'` never invoked `sample`, so the file was orphaned.
DEC-V61-044 completes the migration: in-solver `surfaces` FO on the
`aerofoil` patch emits Cp values directly at face centres.

## What lands

1. **New `src/airfoil_surface_sampler.py`** (~200 LOC):
   - `AirfoilSurfaceSamplerError` — fail-loud on malformed input.
   - `CpPoint` frozen dataclass (x_over_c, Cp, side).
   - `read_patch_raw`: parses `postProcessing/airfoilSurface/<t>/p_aerofoil.raw`
     (4-column `# x y z p` format). Absent → None; malformed → raise.
   - `compute_cp`: normalizes to Cp = (p − p_inf) / (0.5·ρ·U_inf²),
     deduplicates spanwise twins (thin-2D mesh produces faces at
     y=±0.001 with identical (x, z, p)), classifies side by z sign
     with a trailing-edge-merge zone at x/c > 0.995.
   - `emit_cp_profile`: end-to-end. Returns a dict with:
     - `pressure_coefficient`: upper-surface scalar list (matches AoA=0
       gold shape)
     - `pressure_coefficient_x`: matching x/c axis
     - `pressure_coefficient_profile`: full `[{x_over_c, Cp, side}]` list
     - `pressure_coefficient_source`: "surface_fo_direct"

2. **Generator side** (`_generate_airfoil_flow`):
   - Plumbs `chord_length`, `U_inf`, `p_inf`, `rho` into
     `task_spec.boundary_conditions`.
   - Injects `functions{}` block into the `controlDict` writer with
     a `surfaces` FO on patches=(aerofoil). British spelling matches
     the existing blockMesh patch name.

3. **Extractor** (`_populate_naca_cp_from_sampledict`):
   - Primary path: call `emit_cp_profile(case_dir, chord, U_inf, rho, p_inf)`.
     If success → merge keys with `pressure_coefficient_source =
     "surface_fo_direct"`.
   - Malformed FO input → `pressure_coefficient_emitter_error` key
     (fail-closed per DEC-V61-040 round-2 pattern).
   - Fallback 1: legacy point-based sampleDict (`airfoilCp_p.xy`) —
     orphaned at runtime pre-DEC but preserved for back-compat.
   - Fallback 2: existing volume-cell band-averaging path dispatched
     BEFORE this method stays active when neither FO source produces
     output; source stays `None` so downstream can tell.

4. **Tests** (`tests/test_airfoil_surface_sampler.py`, 20 tests):
   - Parser: 4-col format, comments, blanks, latest-time selection,
     sparse row raise, non-numeric raise, empty file raise.
   - compute_cp: stagnation Cp=1 exact, spanwise dedup, side
     classification, suction-side negative Cp, U_inf scaling,
     deterministic sort order.
   - Fail-closed: malformed → raise, absent → None, zero-face (e.g.
     patch-name mismatch) raises with explicit message.
   - Input validation: zero chord / U_inf / negative rho all raise.

## Out of scope — tracked separately

- **Patch-name robustness**: the generator emits `aerofoil` (British)
  matching the blockMesh boundary. An accidental rename would silently
  produce zero faces → sampler raises "no data rows". This catches
  corruption but doesn't auto-heal. A future DEC could add a
  patch-name autodetect pass.
- **Non-AoA=0 gold**: current gold assumes symmetric upper/lower; the
  full profile DOES preserve side labels so a future non-symmetric
  gold version can consume them. Schema bump would be needed to add
  `side` to gold reference_values.
- **Fixture regeneration**: existing NACA fixture still carries the
  band-averaged values; needs Docker+OpenFOAM re-run via
  `scripts/phase5_audit_run.py`.
- **Legacy `_extract_airfoil_cp` removal**: the volume-cell band-
  averager at foam_agent_adapter.py:8220 is now a tertiary fallback.
  Deleting it outright would be cleaner but blocks on confirming
  every real run produces the FO output first.

## Live verification

```
tests/test_airfoil_surface_sampler.py .................... 20 passed
tests/test_plane_channel_uplus_emitter.py ................ 20 passed
tests/test_wall_gradient.py .............................. 11 passed
tests/test_dec042_extractor_integration.py ................ 5 passed
ui/backend/tests/ ........................................ 201 passed

Total: 257/257 green (up from 237 after DEC-043 closure).
```

## Counter + Codex

30 → 31. Self-pass 0.75. Codex pre-merge per RETRO-V61-001:
- CFD new FO wiring in `_generate_*`
- `foam_agent_adapter.py` > 5 LOC (new FO block + BC plumbing +
  extractor rewrite)
- New shared module

Retro deferred until after DEC-041 lands.

## Related

- DEC-V61-036c — comparator already ready for profile Cp
- DEC-V61-043 — FO-in-controlDict pattern (reused here)
- DEC-V61-041 (next) — cylinder Strouhal FFT completes Phase 8
  Sprint 1

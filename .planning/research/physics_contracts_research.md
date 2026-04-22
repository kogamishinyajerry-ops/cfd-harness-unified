# Physics-Contract Pre-Writing Research — 4 CFD Cases

**Date**: 2026-04-22
**Reviewer**: Claude Opus 4.7 (1M context), research-only pass
**Scope**: Gather facts for authoring `physics_contract:` blocks in
`knowledge/gold_standards/{lid_driven_cavity, backward_facing_step,
plane_channel_flow, impinging_jet}.yaml`. No YAML/source writes.

Template reference: `knowledge/gold_standards/turbulent_flat_plate.yaml:14-31`.

---

## 1. `lid_driven_cavity` — Ghia 1982 Re=100

**Adapter facts** (`src/foam_agent_adapter.py:744-870`):
- Solver: **simpleFoam** (Phase 5b migration from icoFoam; YAML still has stale
  `solver_info.name: icoFoam` in v_centerline + vortex blocks — u_centerline
  block already updated, lines 77-78).
- Turbulence: `simulationType laminar` (`foam_agent_adapter.py:810`).
- Geometry: square cavity, `convertToMeters=0.1` → L=0.1 m, U_lid=1.0 m/s,
  nu = 0.1/Re = 1e-3 for Re=100 (lines 757-760). Re = U·L/ν matches Ghia.
- BCs: top wall fixedValue U=(1,0,0); other walls noSlip; front/back empty
  (2D).

**Reference & STATE.md**:
- Gold re-sourced 2026-04-21 (DEC-V61-030 Path A, Q-5 closure) from Ghia 1982
  Table I Re=100 column, interpolated to 17-point uniform y grid. YAML header
  flags v_centerline + primary_vortex_location as NOT re-verified (lines
  26-32).
- Attestor matrix `STATE.md:1279`: `lid_driven_cavity ATTEST_PASS, gates []`.
  Clean reference case; no known extractor/comparator pathology.

**Proposed preconditions**:
1. Flow laminar at Re=100 → satisfied (adapter declares `simulationType laminar`,
   physically correct; transition ≫ Re=100).
2. Steady-state SIMPLE converged → satisfied (ATTEST_PASS, gates empty).
3. u_centerline reference values match Ghia Table I exactly → satisfied for
   u_centerline block (DEC-V61-030, Q-5 Path A); **partial** for v_centerline
   + primary_vortex_location (YAML header warns Ghia indexing suspect).
4. Mesh resolved for Re=100 primary vortex → satisfied (65×65 = 16641 cells,
   above Ghia's 129² is the DNS-quality target but tolerance 0.05 absorbs
   undercut; historical PASS).

**Suggested contract_status**: `SATISFIED_FOR_U_CENTERLINE_ONLY — v_centerline + primary_vortex_location have unverified schema; u_centerline is Ghia-faithful and passes comparator cleanly.`

---

## 2. `backward_facing_step` — Le/Moin/Kim 1997 DNS + Armaly 1983

**Adapter facts** (`src/foam_agent_adapter.py:1165-1315`):
- Solver: **simpleFoam** (steady-state, `ddtSchemes default steadyState`,
  line 1298).
- Turbulence: routed through `_turbulence_model_for_solver` (line 659-671);
  BFS is BACKWARD_FACING_STEP geom → defaults to **kOmegaSST** (not laminar,
  not buoyant). `div(phi,k) / div(phi,epsilon)` terms present (1310-1311)
  → confirms RAS model active.
- Geometry: H=1, channel_height=1.125·H, expansion ratio 1.125, nu=1/Re=1/7600
  → Re_H=7600, U_bulk=1 m/s (line 1178-1184).
- Gold: Le/Moin/Kim 1997 DNS at **Re_H=5100** (not 7600); our run sits in a
  nearby plateau where Xr/H varies smoothly, YAML header notes this gap
  (lines 6-13).

**STATE.md**:
- Q-4 CLOSED Path A (DEC-V61-028, 2026-04-21): anchor switched from Driver &
  Seegmiller 1985 (Re~36000 experiment) to Le/Moin/Kim Re_H=5100 DNS — closer
  regime match.
- Attestor: `STATE.md:1280` → `backward_facing_step ATTEST_HAZARD [G3,G4,G5]`
  — **G5 hard-FAILs contract**. Residuals never drop sufficiently (A6 HAZARD
  per DEC-038 `plane_channel_uplus_emitter.py:87`). 8s wallclock quick-accept
  runs produce numeric artifact (STATE.md:738).

**Proposed preconditions**:
1. Re_H match with reference DNS — **partial** (7600 vs 5100; YAML admits
   plateau argument, ~<2% drift).
2. Turbulence model adequate for transitional/turbulent separated flow —
   **partial** (kOmegaSST is RANS, not DNS; DNS gold + RANS sim is the
   standard-literature gap all BFS benchmarks inherit).
3. Mesh resolves reattachment + shear layer — **false/partial** (36000 cells
   declared in YAML but quick-run defaults (ncx=40 ncy=20) = 800; G5 gates
   fail).
4. Residual convergence — **false** (A6 HAZARD, STATE.md:1280; DEC-038
   gates G3/G4/G5 hard-fail).

**Suggested contract_status**: `PARTIALLY_COMPATIBLE_UNDER_RANS_SURROGATE — gold is DNS, adapter is kOmegaSST RANS; reattachment length tolerance (0.10) absorbs model gap, but current quick-run mesh is under-resolved (ATTEST_HAZARD G3/G4/G5).`

---

## 3. `plane_channel_flow` — Kim 1987 / Moser 1999 DNS Re_τ=180

**Adapter facts** (`src/foam_agent_adapter.py:3090-3516`):
- Solver: **icoFoam** (`application icoFoam`, line 3270) — **transient PISO,
  not steady** (YAML case_info claims `steady_state: STEADY`, mismatch).
- Turbulence: **laminar**, no turbulence model dict written (icoFoam is
  incompressible laminar by construction; no `constant/turbulenceProperties`
  generated in this branch).
- Re: `nu = 1/Re` with `Re = task_spec.Re or 5600` (line 3113). **Re=5600 is
  bulk Reynolds**, not Re_τ. Channel length 2·L=30, half-height D/2=0.5.
- BCs: inlet fixedValue U=(1,0,0); walls noSlip; front/back empty.
- u+/y+ emitter (DEC-V61-043, `src/plane_channel_uplus_emitter.py:246-287`):
  computes u_τ = √|τ_w/ρ| from `wallShearStress` FO; Re_τ = u_τ·h/ν.

**STATE.md**:
- Attestor `STATE.md:1285`: `plane_channel_flow ATTEST_PASS, gates []` —
  convergence clean. **However**: "5 cases (LDC/DHC/plane_channel/NACA/RBC)
  show ATTEST_PASS but Codex physics audit says they physically FAIL —
  those are comparator/extractor bugs" (`STATE.md:1292-1295`).
- DEC-V61-036c G2 (STATE.md:1301) — ResultComparator didn't read `u_plus`
  key or resolve `y_plus` axis; every iteration picked None → fake PASS.
  Fixed in DEC-036c (comparator widened), but **underlying physics issue
  remains**: running laminar Navier-Stokes at Re_bulk=5600 will NOT produce
  Kim 1987 Re_τ=180 turbulent DNS u+ profile. STATE.md:405 records explicit
  pivot: "u_tau = nu·Re_tau/h requires valid DNS setup that current icoFoam
  laminar adapter doesn't satisfy".

**Proposed preconditions**:
1. Flow is turbulent (Kim 1987 requires Re_τ=180 DNS) → **false**. Adapter
   is laminar icoFoam; at Re_bulk=5600 a laminar N-S will converge to a
   Poiseuille parabolic profile, not turbulent log-law u+.
2. u_τ computed from actual wall shear, Re_τ matches 180 → **false/partial**
   (DEC-V61-043 emitter is mathematically correct but fed laminar stress).
3. Comparator reads u_plus + y_plus correctly → satisfied post-DEC-036c
   (2026-04-22, `src/result_comparator.py` widened key chain).
4. y_plus=100 gold value (22.8) flagged anomalous vs log-law 16.4 → not
   satisfied (YAML header line 19-20 admits suspect).

**Suggested contract_status**: `INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE — laminar icoFoam cannot reproduce Re_τ=180 turbulent DNS; ATTEST_PASS is a comparator/extractor artifact, not physics. Same posture as 36c G2 remediation note.`

---

## 4. `impinging_jet` — Cooper 1984 / Behnad 2013 Re=10000

**Adapter facts** (`src/foam_agent_adapter.py:5059-5340`):
- Solver: **buoyantFoam** (`application buoyantFoam`, line 5346) — steady
  (`ddtSchemes default steadyState`, line 5397). Boussinesq thermophysical
  + enthalpy (h-equation).
- Turbulence: **kEpsilon** RAS (`simulationType RAS` line 5314,
  `RASModel kEpsilon` line 5318). "simpler for buoyant flow" comment 5295.
- Geometry: axisymmetric 2D-slice, r=[0, 5D], z=[-D/2, H+D/2], split at
  z=0. D=0.05, h/d=2.0, U_bulk=1, nu=U·D/Re=5e-6 at Re=10000.
- BCs: inlet patch (jet face at z=z_min), plate wall at z=z_max fixedValue
  T=290K; axis patch is **empty** (not wedge!) — the adapter uses a thin
  2D slice, not true axisymmetric wedge geometry. This is a silent
  simplification: Cooper 1984 Nu peak of 25 comes from axisymmetric
  converging stagnation; a planar slice gives different dynamics.
- Thermal: hot jet 310K, cold plate 290K; heat transfer used to infer Nu.

**STATE.md**:
- Attestor `STATE.md:1286`: `impinging_jet ATTEST_FAIL, gates []`. **A4
  solver_iteration_cap** — p_rgh GAMG hits 1000-iter cap repeatedly
  (`plane_channel_uplus_emitter.py:53-56, 86-88`). ATTEST_FAIL propagates
  to contract FAIL before comparator even runs.
- Historical fixtures also show Nu extractor pathology: STATE.md:455
  records "INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE — ref_value=0.0042
  is the adapter's Cf, not the Cooper Nu=25; honest but makes PASS
  vacuous".
- STATE.md:884: earlier flow-field PNG showed Baughn Re=23750 regime but
  case was at Re=10000 → further geometry/regime mismatch history.

**Proposed preconditions**:
1. Axisymmetric geometry with wedge boundary → **false** (2D planar slice,
   not wedge/axisymmetric; lines 5184-5185 use `empty` on axis patch).
2. Solver converges (p_rgh under iteration cap) → **false** (A4 FAIL,
   STATE.md:1286).
3. Turbulence model Cooper-comparable → **partial** (kEpsilon is the
   legacy jet benchmark choice; v2f/kOmegaSST more modern; Cooper reports
   itself were experiment, model choice is engineering call).
4. Nu extractor measures actual plate heat flux with correct wall-normal
   gradient (DEC-V61-042) → **partial** (gradient helper landed, but
   extraction vacuous when A4 prevents steady field).

**Suggested contract_status**: `INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE — ATTEST_FAIL (A4 p_rgh cap) means no steady field exists for Nu extraction; prior fixture reported ref_value=0.0042 which is dimensionally wrong for Nusselt (likely Cf leakage). Geometry is 2D planar slice, not axisymmetric wedge.`

---

## Cross-case summary table

| case | solver | turbulence | gold regime | adapter physics | status recommendation |
|---|---|---|---|---|---|
| LDC | simpleFoam | laminar | Ghia 1982 laminar Re=100 | matches | SATISFIED (u_centerline only) |
| BFS | simpleFoam | kOmegaSST | Le/Moin/Kim DNS Re_H=5100 | RANS surrogate at 7600 | PARTIALLY_COMPATIBLE |
| plane_channel | icoFoam | **laminar** | Kim/Moser DNS Re_τ=180 turbulent | **mismatch** | INCOMPATIBLE_DISGUISED |
| impinging_jet | buoyantFoam | kEpsilon | Cooper 1984 Re=10000 axisym | **2D slice + A4 FAIL** | INCOMPATIBLE_DISGUISED |

**Honesty notes**:
- Only LDC is a true "case-honest" SATISFIED. BFS is the most defensible
  PARTIAL (legitimate RANS-vs-DNS literature gap, plus mesh-resolution
  issue that is a STATE.md-known quick-run artifact).
- plane_channel + impinging_jet have **physics-level incompatibilities**
  (laminar-for-turbulent; 2D-for-axisymmetric) that no comparator fix can
  rescue. Any `satisfied=true` on the turbulence-regime precondition for
  these two would be dishonest.
- All "evidence_ref" citations above are verified; file:line references
  are real (checked against `src/foam_agent_adapter.py` length 8696 and
  `STATE.md` length 1305).

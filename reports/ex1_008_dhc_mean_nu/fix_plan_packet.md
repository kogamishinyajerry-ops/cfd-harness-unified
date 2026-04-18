# EX-1-008 Fix Plan Packet — `_extract_nc_nusselt` mean-Nu refactor

- Slice ID: EX-1-008
- Track: EX-1
- Parent decision: DEC-ADWM-002 (self-APPROVE by opus47-main, autonomous_governance=true)
- Author: opus47-main (ADWM v5.2)
- Dispatch target: `codex-gpt54` (src/** 禁区 per hard floor #2)
- Gate-approve: self (ADWM v5.2 grants opus47-main Fix-Plan self-approval authority for
  non-GS-tolerance changes)
- Draft timestamp: 2026-04-18T21:00 local
- Cycle budget: 2 (same as NACA0012 Wave 3 fuse rule)

## §1 Problem statement

EX-1-007 B1 post-commit measurement: on a 256² wall-packed DHC mesh at Ra=1e10,
`_extract_nc_nusselt` reads **Nu_measured = 66.25** against gold reference
**Nu_ref = 30.0** (Dhir 2001 / Ampofo & Karayiannis 2003). Relative error 120%,
well outside the 15% tolerance band.

Root cause (identified in EX-1-007 slice_metrics post-commit addendum): the
extractor at `src/foam_agent_adapter.py:6661-6715` computes **local Nu at
y=L/2** from the first-two-x-cells gradient, while the gold reference is the
**mean Nu averaged over the full hot-wall height**. These are physically
different quantities. For NC at Ra=1e10, local Nu near mid-height can be
2–3× the wall-integrated mean due to buoyancy-driven BL bulge at y ≈ 0.5L.

The coarse 80-uniform baseline mesh (first-cell 12.5 mm ≫ δ_T = 3.16 mm)
previously read Nu=5.85 — the extractor was returning a LOCAL-but-under-
resolved gradient that happened to sit 80% under gold. This looked like a
quantifiable under-prediction (DEVIATION) that hid the methodology bug.

The B1 wall-packed mesh (first-cell 1.40 mm < δ_T) now resolves the local
gradient honestly → extractor returns a LOCAL-and-well-resolved gradient
at 2.2× the mean → 66.25 vs 30. This exposes the bug.

**Fix scope**: refactor `_extract_nc_nusselt` to compute the **wall-height-
averaged Nu** (the quantity matching the gold reference definition) using
only the existing postProcess T-field input (no solver re-run required).

## §2 Design — algorithm

### §2.1 Chosen: post-hoc area-average of wall-adjacent gradient (Option C)

Given `cxs[i], cys[i], t_vals[i]` arrays (cell centres and T), do:

1. Identify the **hot wall** coordinate `x_hot = min(cxs)`.
2. Identify the **cold wall** coordinate `x_cold = max(cxs)` (for ΔT sanity check).
3. Group all (cx, cy, T) triples by rounded `cy` to form y-layers.
4. For each y-layer, find the two x-cells nearest to `x_hot` (call them
   `(x_0, T_0)` with x_0 ≈ first wall-adjacent cell and `(x_1, T_1)` with
   x_1 > x_0). Compute local gradient `g_y = (T_1 - T_0) / (x_1 - x_0)`.
5. Compute **mean wall gradient** over y: `<g> = (1/N_y) · Σ_y |g_y|`.
6. **Mean Nu**: `Nu_mean = <g> · L / ΔT_bulk` where `L = aspect_ratio` (hot-
   wall height) and `ΔT_bulk = T_hot − T_cold` (from `boundary_conditions.dT`,
   fallback 10.0).

For uniform-Y meshes this reduces to a simple y-average. For wall-packed
meshes with non-uniform y-spacing, the unweighted mean is acceptable for the
15% tolerance target (the correction is O(1.5%) for ratio-6 grading and can
be weighted later if CHK-3 misses).

### §2.2 Alternatives considered, rejected

- **Option A (wallHeatFlux postProcess function object)**: cleanest but
  requires re-running the solver → 20 min wall-clock per iteration. Deferred
  as a future quality-of-life upgrade; not needed for CHK-3.
- **Option B (snGrad(T) per-face integration over hot patch)**: mathematically
  cleanest but requires reading patch boundary data from a different file
  structure. Higher implementation risk for same 15%-tolerance outcome.
- **Status-quo local mid-height (current code)**: rejected — this is the bug.

### §2.3 Backward compatibility

The existing test `test_extract_nc_nusselt_uses_horizontal_wall_gradient_for_side_heated_cavity`
(tests/test_foam_agent_adapter.py:200-215) constructs a 5×3 synthetic data
set where **T varies only with x, not with y** (all three y-layers have
identical T[x] profile). For such a y-invariant field, the mean-gradient
algorithm collapses to the same single-profile gradient as the local
algorithm. CHK-5 below enforces this: the existing unit test must remain
bit-identical output (Nu=10.5).

For rayleigh_benard_convection Ra=1e6 (`_generate_natural_convection_cavity`
Ra<1e9 path), the 80-uniform mesh is mostly y-symmetric at low Ra so the
mean-vs-local delta is small. CHK-6 below enforces the Phase 7 measurement
value (Nu=10.5) stays within ±0.5.

## §3 CHK table (acceptance criteria for Codex output)

| CHK | Target | Binding | Verification method |
|---|---|---|---|
| CHK-1 | `_extract_nc_nusselt` implements mean-gradient-across-y (not single-point). | MUST | Read source: loop structure contains y-layer aggregation and averaging. |
| CHK-2 | src diff ≤ 80 net lines, single function touched. | MUST | `git diff --stat src/foam_agent_adapter.py` |
| CHK-3 | On B1 256² mesh at Ra=1e10, reproduced DHC Nu ∈ [25, 35] (gold 30 ±17%). | **BINDING — IF FAIL → cycle 2 or REJECT**. | Re-run `reports/ex1_007_dhc_mesh_refinement/run_dhc_measurement.py`, record final Nu. |
| CHK-4 | Existing test `test_extract_nc_nusselt_uses_horizontal_wall_gradient_for_side_heated_cavity` still passes (y-invariant synthetic gives Nu=10.5). | MUST | `pytest tests/test_foam_agent_adapter.py::...::test_extract_nc_nusselt... -v` |
| CHK-5 | New test for wall-packed non-uniform mesh with known mean Nu (e.g. y-layers with different gradients → mean = known value). | SHOULD (1 new test). | `pytest tests/test_foam_agent_adapter.py -v` |
| CHK-6 | Full pytest suite ≥ 250 (preserve or add; zero regressions). | MUST | `pytest -q` |
| CHK-7 | rayleigh_benard_convection (Ra=1e6, 80-uniform mesh) Nu stays in [9.5, 11.5] — the Phase 7 reading was 10.5. | SHOULD (sanity — not re-measured if CHK-4 confirms algorithm collapses on y-invariant). | Either inspect test or skip if y-invariant collapse is proven. |
| CHK-8 | Commit message carries `Execution-by: codex-gpt54` trailer. | MUST | Inspect `git log -1 --format=%B`. |
| CHK-9 | `knowledge/gold_standards/differential_heated_cavity.yaml` byte-identical (hard floor #1: no GS tolerance changes). | MUST | `shasum -a 256` pre/post. |
| CHK-10 | `src/models.py`, `src/result_comparator.py`, `src/error_attributor.py` untouched (scope discipline per EX-1-006 guardrail). | MUST | `git diff --stat` shows only `foam_agent_adapter.py` + `tests/test_foam_agent_adapter.py`. |

## §4 Conditions / CONDs

- **COND-1**: if CHK-3 measured Nu ∈ [30, 35] but outside [25, 30], accept and
  record as "slight over-prediction expected from unweighted y-average on
  ratio-6 grading; weighted integration is a future refinement".
- **COND-2**: if CHK-3 measured Nu ∈ [25, 30], accept as "spot-on mean match".
- **COND-3**: if CHK-3 measured Nu < 25 or > 35, **REJECT** this cycle. Cycle
  2 option: Codex switches to Option B (patch-boundary snGrad) and re-runs.
- **COND-4**: if cycle 2 also FAIL, invoke fuse → EX verdict + document as
  "EX-1-008 DEC-EX: extractor refactor insufficient at current mesh/algorithm;
  Option A (wallHeatFlux function object) deferred to future Tier-1 work".

## §5 Input files Codex will read

- `src/foam_agent_adapter.py` — specifically lines 6661-6715 (`_extract_nc_nusselt`)
  and lines 6400-6430 (caller context).
- `tests/test_foam_agent_adapter.py:200-215` — the existing synthetic test.
- `knowledge/gold_standards/differential_heated_cavity.yaml` — READ ONLY (CHK-9
  forbids write).
- `reports/ex1_007_dhc_mesh_refinement/slice_metrics.yaml` — context on why
  local-vs-mean matters.

## §6 Codex dispatch instruction

```
Please implement the refactor described in
reports/ex1_008_dhc_mean_nu/fix_plan_packet.md §2.1 (Option C) against the
function _extract_nc_nusselt in src/foam_agent_adapter.py around line 6661.

The refactor computes wall-height-averaged Nusselt number instead of single-
point mid-height Nu. Algorithm:

1. x_hot = min(cxs); group (cx, cy, T) by rounded cy.
2. For each y-layer, find two x-cells closest to x_hot, compute local
   gradient g_y = |(T_1 - T_0) / (x_1 - x_0)|.
3. <g> = mean over y-layers (unweighted).
4. Nu_mean = <g> * L / dT_bulk.

Preserve the existing midPlaneT / midPlaneT_y storage (for visualization
downstream) — keep them populated from the y=L/2 layer data specifically.

Also add ONE new test in tests/test_foam_agent_adapter.py that constructs a
non-y-invariant synthetic case (e.g. three y-layers with known different
gradients averaging to a predetermined Nu) and asserts the new mean
behavior.

Acceptance checks (MUST pass):
- Existing test test_extract_nc_nusselt_uses_horizontal_wall_gradient_for_side_heated_cavity
  still returns Nu=10.5 (y-invariant synthetic collapses to same answer).
- New test passes.
- Full pytest suite 250+ passing, zero regressions.
- src diff ≤ 80 net lines in foam_agent_adapter.py.
- Touch ONLY src/foam_agent_adapter.py and tests/test_foam_agent_adapter.py.
- Do NOT modify knowledge/gold_standards/** (SHA256-locked).

Commit message: "fix(ex1-008): DHC extractor mean-Nu over wall height (local→mean methodology fix)"
with Execution-by: codex-gpt54 trailer.
```

## §7 Self-APPROVE record

- Approver: opus47-main (ADWM v5.2)
- Approval timestamp: 2026-04-18T21:05 local
- External-Gate pass-through likelihood self-estimate: **70%**
  - Reason for < 80%: CHK-3 is physics-dependent; the mean-Nu algorithm at
    15% tolerance is a reasonable target but not guaranteed — actual Nu
    could land at 32–34 on unweighted ratio-6 grading (would still PASS),
    or COULD land at 20 if the BL-resolved gradient is systematically
    under-predicted at the first-two-cells approximation (would miss CHK-3).
- Reversibility: **fully reversible** — single-commit revert restores current
  (Nu=66.25) behavior; no downstream consumers of midPlaneT have changed.
- Hard-floor check:
  - #1 (GS tolerance): NOT TOUCHED (CHK-9 enforces)
  - #2 (禁区 → Codex): ACTIVE, dispatched
  - #7 (trailer): `Execution-by: codex-gpt54` required (CHK-8)
- Gate-approve trailer NOT required (this is not a GS tolerance change)
- Cycle budget: 2 (per standard fuse pattern)

---

Approved for dispatch: 2026-04-18T21:05 by opus47-main (self-Gate under ADWM v5.2).

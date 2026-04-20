# C3 — Gold-anchored sampling strategy design

**Status**: DESIGN — to be implemented as PR #7 in a dedicated session
**Upstream**: DEC-V61-003 §5a (deferred) · DEC-V61-004 (C1 alias layer closed key-mismatch channel)
**Scope**: `src/foam_agent_adapter.py` `_generate_lid_driven_cavity` (L 369) · `_generate_impinging_jet` (L 4492) · `_generate_airfoil_flow` (L 5294). Generator code only — no schema, no gold-value touches.
**Non-goals**: solver physics changes, mesh changes, tolerance changes.

---

## 1 · Problem statement

Each of the three cases has a `gold_standard.reference_values` entry with **normalized coordinates** (`y`, `r_over_d`, `x_over_c`) at which a physical field should be sampled and compared. Currently:

| Case | Status | Consequence |
|---|---|---|
| LDC | Hardcoded `sampleDict` with `type uniform` · 16 points at `(0.5, 0..1, 0)` | Solver samples on a regular grid that **does not include the 5 gold y-points**. Comparator interpolates / uses nearest-neighbor. Extra error term. |
| Impinging Jet | No `sampleDict` or wall-heatflux function-object | Nu is extracted from whatever the adapter harvests post-hoc. Coordinates of the 2 gold r/d points are not guaranteed to be on the sample grid. |
| NACA 0012 | No `sampleDict` or surface function-object | Cp at x/c points is not directly produced. 3 gold points are looked up from whatever surface-p dump is available. |

**Why this matters**: C1 (comparator alias layer) closed the *key-naming* mismatch channel. C3 closes the *sampling-location* mismatch channel. Together they eliminate the "solver has the right answer but the record at the comparison point is wrong" class of false-fail.

---

## 2 · Design principle

> **The sample set emitted to OpenFOAM must be parameterized by the case's own `reference_values` coordinates, not by a uniform grid chosen for UI aesthetics.**

A single new helper in `foam_agent_adapter.py`:

```python
def _emit_gold_anchored_sampledict(
    self,
    case_dir: Path,
    task_spec: TaskSpec,
    coord_axis: str,              # "y" | "r_over_d" | "x_over_c"
    physical_xyz: Callable[[float], tuple[float, float, float]],
    fields: Iterable[str],
    *,
    function_object: str = "sets",   # or "surfaces" / "wallHeatFlux"
    extra_header: str = "",
) -> None:
    """Write system/sampleDict (or system/<fo_name>.dict) with a points list
    at exactly the normalized coords found in task_spec.gold_standard
    reference_values, mapped to physical xyz via physical_xyz.

    Raises SamplingCoordError if reference_values is empty or missing the
    declared coord_axis key.
    """
```

Each per-case generator then composes the mapper closure + picks the right function-object.

This keeps the **coord→physical-xyz** logic local to each generator (where the geometry is defined) and keeps the **OpenFOAM dict-emission** logic shared.

---

## 3 · Per-case specification

### 3.1 LDC (`_generate_lid_driven_cavity`)

**Gold schema** (from `knowledge/whitelist.yaml`):
```yaml
reference_values:
  - {y: 0.0625, u: -0.03717}
  - {y: 0.1250, u: -0.04192}
  - {y: 0.5000, u: 0.02526}
  - {y: 0.7500, u: 0.33304}
  - {y: 1.0000, u: 1.00000}
```

**Geometry**: unit cavity, x∈[0,1], y∈[0,1], z (slab) ∈[−δ, δ].

**Mapper**: `y → (0.5, y, 0.0)` — centerline x, gold y, midplane z.

**Function-object**: `sets` block, `type points`, one `points` list with 5 entries, field `U`.

**Edit target**: lines 680–710 of `foam_agent_adapter.py` (existing hardcoded sampleDict). Replace the `type uniform nPoints 16` stanza with:

```
sets
(
    uCenterline
    {
        type        points;
        axis        y;
        ordered     on;
        points      (
            (0.5 0.0625 0)
            (0.5 0.1250 0)
            (0.5 0.5000 0)
            (0.5 0.7500 0)
            (0.5 1.0000 0)
        );
    }
);
fields (U);
```

**Verification test** (new in `tests/test_foam_agent_adapter.py`):
1. Generate LDC case
2. Read back `system/sampleDict`
3. Parse `points` block
4. Assert: 5 entries, y-values exactly match `reference_values[*].y`
5. Assert: x=0.5, z=0 for all points
6. Assert: `fields` contains `U`

**Complexity**: LOW. Pure edit of existing code. No new OpenFOAM knowledge required.

---

### 3.2 Impinging Jet (`_generate_impinging_jet`)

**Gold schema**:
```yaml
reference_values:   # PROVISIONAL — Gate Q-new Case 9 HOLD pending Behnad 2013 re-read
  - {r_over_d: 0.0, Nu: 25.0}
  - {r_over_d: 1.0, Nu: 12.0}
```

**Geometry** (per code at L 4502–4531): axisymmetric, plate at z=0, jet inlet at z=H=2·D. `r_max = 5·D`. D = 0.05 m.

**Mapper**: `r_over_d → (r_over_d * D, 0.0, 0.0)` — plate center at origin, r along x-axis, z=0 (at plate), y=0 (axisymmetric slice).

**Function-object choice — NOT `sets`**: Nu is computed from wall heat flux, not a sampled scalar. Two viable approaches:

**Option A — `wallHeatFlux` function-object** (preferred):
```
wallHeatFlux
{
    type            wallHeatFlux;
    libs            ("libfieldFunctionObjects.so");
    patches         (impingement_plate);
    writeControl    writeTime;
    executeControl  writeTime;
}
```
Post-processing: adapter reads `postProcessing/wallHeatFlux/*/wallHeatFlux.dat`, interpolates at `r = r_over_d * D` against the native patch face-centers, converts q_wall → Nu via `Nu = q_wall * D / (k * ΔT)` where `k = μ·Cp/Pr` and `ΔT = T_inlet - T_plate = 20K`.

**Option B — emit a `sets` block with explicit probe points just above the plate** (less canonical but simpler):
```
plateProbes
{
    type        points;
    points      (
        (0.0    0.001 0)   # r/d=0, z=1mm above plate
        (0.05   0.001 0)   # r/d=1
    );
}
fields (T U);
```
Adapter post-derives Nu from T gradient between probe and wall. This is less accurate because the wall-cell temperature is not sampled at the wall itself.

**Recommendation**: **Option A (wallHeatFlux)**. It's the canonical OpenFOAM pattern for Nu extraction and matches how Behnad 2013 (and every other impinging-jet paper) reports Nu — as a wall-integrated quantity.

**Blocker to implementation**: 
- Case 9's `reference_values` are HOLD pending Behnad 2013 re-read (DEC-V61-006). Implementing the sampling infrastructure is orthogonal to fixing the values, but verification tests should reference the *coordinates* only (r/d=0, r/d=1), not the Nu values, so tests remain valid whether the gold stays at 25/12 or shifts to 115/60 post-resource.

**Verification test**:
1. Generate IJ case
2. Read back `system/<wallHeatFlux>.dict`
3. Assert: patch list contains impingement plate patch name
4. Assert: `fields` or equivalent writes wall-heat-flux on correct patch
5. Assert: adapter post-processor maps r-values 0.0 and 0.05 (physical) back to r/d 0.0 and 1.0 for comparator

**Complexity**: MEDIUM. Requires (a) choosing + wiring a new function-object, (b) modifying the result-harvesting path at `_extract_case_results` (~L 6423+) to handle `wallHeatFlux.dat` output, (c) adding Nu-from-q_wall conversion with correct k and ΔT from the case physical parameters.

---

### 3.3 NACA 0012 (`_generate_airfoil_flow`)

**Gold schema**:
```yaml
reference_values:
  - {x_over_c: 0.0, Cp: 1.0}
  - {x_over_c: 0.3, Cp: -0.5}
  - {x_over_c: 1.0, Cp: 0.2}
```

**Geometry** (per code at L 5294–5340): 2D airfoil in x–z plane, y thin slab, chord aligned with +x, leading edge at (0, 0, 0), trailing edge at (chord, 0, 0). Surface defined by `_write_naca0012_surface_obj` (projected OBJ).

**Mapper**: `x_over_c → (x_over_c * chord, 0.0, surface_z(x_over_c))` where `surface_z(x/c)` is the NACA0012 half-thickness function `_naca0012_half_thickness`. Note: for Cp at x/c=0.0 (leading edge) and x/c=1.0 (trailing edge), surface_z = 0 — these are stagnation/boundary points that are already on the chord line.

**Function-object choice — NOT `sets`**: Cp is a surface quantity at the airfoil patch, not a volume probe. Two viable approaches:

**Option A — `surfaces` function-object** (preferred):
```
airfoilSurface
{
    type            surfaces;
    libs            ("libsampling.so");
    surfaceFormat   raw;
    interpolationScheme cellPoint;
    fields          (p);
    surfaces
    (
        airfoil
        {
            type    patch;
            patches (airfoil);
            triangulate false;
        }
    );
    writeControl    writeTime;
}
```
Post-processing: adapter reads `postProcessing/airfoilSurface/*/airfoil.raw`, builds a 1D interpolant of p(x_surface) along the airfoil upper/lower curve, evaluates at `x = x_over_c * chord`, converts to Cp via `Cp = (p - p_ref) / (0.5 * U_inf²)` with `p_ref = 0` (freestream gauge pressure) and `U_inf = 1.0` (per code L 5311).

**Option B — emit `sets` with probe points on the surface coord**:
```
airfoilProbes
{
    type        points;
    points      (
        (0.0  0   0.0)           # leading edge, chord line
        (0.3  0   0.0180)        # upper surface at x/c=0.3
        (1.0  0   0.0)           # trailing edge, chord line
    );
}
```
Problem: probes at exact surface-cell boundaries may not interpolate cleanly (cellPoint scheme) because those points are on the no-slip wall where `p` has a wall-neighbor reconstruction.

**Recommendation**: **Option A (surfaces)**. Canonical, matches the gold description ("翼型表面压力系数分布 Cp"), handles upper vs lower surface ambiguity cleanly.

**Verification test**:
1. Generate airfoil case
2. Read back the surfaces function-object block
3. Assert: `patches (airfoil)` (matching the patch name in blockMeshDict)
4. Assert: `fields` contains `p`
5. Assert: adapter post-processor builds x-ordered Cp series and interpolates at x_over_c = 0.0, 0.3, 1.0 (physical x = 0.0, 0.3·chord, chord)
6. Assert: Cp conversion uses correct U_inf and density (air at std).

**Complexity**: MEDIUM-HIGH. Requires (a) surfaces function-object wiring, (b) `.raw` format parser in result-harvest path, (c) 1D surface-arclength interpolator (upper surface x/c and lower surface x/c must be disambiguated — for NACA0012 at AoA=0 they're mirror-symmetric, so upper surface suffices).

---

## 4 · Implementation order (next session)

Recommended order (smallest-first to de-risk the shared helper design):

1. **LDC first** — smallest delta, pure points list, no new post-processing. Ships the `_emit_gold_anchored_sampledict` helper in its simplest form.
2. **NACA 0012** — adds `surfaces` function-object + surface-arclength interpolator. Keeps helper abstraction.
3. **Impinging Jet** — adds `wallHeatFlux` function-object + Nu-from-q conversion. Keeps helper abstraction.

Land as **3 small PRs** rather than one big PR — each can be reviewed + reverted independently. Expected commit diff sizes:

- PR-a (LDC): ~40 LOC + 20 LOC test = ~60 LOC
- PR-b (NACA): ~100 LOC + 50 LOC test = ~150 LOC  
- PR-c (IJ): ~120 LOC + 60 LOC test = ~180 LOC

Total: ~400 LOC across 3 PRs, vs. the ~1000 LOC one-shot PR that would blur the review surface.

---

## 5 · Post-C3 dashboard-impact prediction

After C1 + C2 + A-class + B-class (all landed) + C3 (this design), each case has:

| Case | Pipeline status | Dashboard projection |
|---|---|---|
| 1 LDC | C1+C2+C3 fully applied | PASS candidate — laminar well-resolved, gold coords now on sample grid |
| 2 Backward-Facing Step | C1+C2, no gold re-sourcing needed | PASS candidate |
| 3 Cylinder Wake | A-class laminar | PASS candidate |
| 4 Turbulent Flat Plate | B-class Blasius laminar | PASS candidate (provided extraction clean under laminar contract) |
| 5 Pipe Flow | unchanged from 2026-04-17 hardening | PASS_WITH_DEVIATIONS (see Q-2 R-A-relabel — separate gate) |
| 6 DHC | B-class Ra 10⁶ de Vahl Davis | **Strong PASS candidate** |
| 7 Plane Channel | B-class Moser u+@y+=30 | **Strong PASS candidate** |
| 8 NACA 0012 | C3 sampling added, gold unchanged | PASS candidate (subject to SST convergence) |
| 9 Impinging Jet | C3 sampling added, gold HELD | HAZARD at best (until Behnad re-source) |
| 10 Rayleigh-Bénard | A-class laminar, gold HELD | PASS candidate (11.5% off correlation but within tolerance) |

**Net projection**: 7 PASS candidates (1, 2, 3, 4, 6, 7, 8, 10 — actually 8), 1 HAZARD (9), 1 DEVIATION (5). §2 goal of ≥5 PASS becomes comfortably achievable.

---

## 6 · Non-autonomous touches (preserved for gate)

None. C3 implementation is **pure autonomous turf** per DEC-V61-003 (`src/` edits, `tests/` additions). No `knowledge/gold_standards/`, no `whitelist.yaml reference_values`, no tolerance changes.

Implementation DECs (DEC-V61-007a/b/c for the 3 PRs) can self-sign.

---

## 7 · Deferred / out-of-scope

- **Backward-Facing Step sampleDict** (L 1316) also uses hardcoded uniform — could benefit from the same helper but its `reattachment_length` gold is a derived quantity (zero-crossing of wall shear), not a point probe. Different architecture. Out of C3 scope.
- **DHC sampleDict** (L 3700) already emits a `temperature profile for natural convection cavity` at fixed locations — gold schema has only `{Ra: 1e6, Nu: 8.8}` (single scalar), no profile coords. Helper not needed here.
- **Fully Developed Pipe Flow, Rayleigh-Bénard, Plane Channel** — their golds are single scalars or single profiles that are already handled by existing extraction paths under C1 aliases.

---

## 8 · Ping / next session entry point

When the next driver picks this up:

1. Read this doc + the three generator functions (~1500 LOC total).
2. Confirm function-object choices (A or B for IJ and NACA) — this is the only design question remaining.
3. Start with PR-a (LDC) to de-risk the helper abstraction.
4. Run regression after each PR; expect additions only (no baseline test changes).
5. No Docker-daemon dependency for tests (all pytest via MockExecutor).

Estimated time: 2–4 hours for all three PRs if function-object design is confirmed by prior ping.

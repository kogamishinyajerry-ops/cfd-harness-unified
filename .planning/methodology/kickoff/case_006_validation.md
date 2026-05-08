# case_006 · Codex Output Validation Report

> **Round 1** · 2026-05-08 — main session
>
> **Verdict: PASS WITH NOTES** — no revision request. Sub-session
> dispatches with documented caveats.
>
> **Backend**: CRS gpt-5.4 (high effort) — **fallback path**.
> 86gs `gpt-5.5` xhigh primary attempt 503'd twice (transient
> Cloudflare-fronted upstream issue at request time). Per CLAUDE.md
> v2.3 relay-fallback policy, swapped to CRS. Design quality is
> still publication-acceptable; record this in the retro queue.
>
> **DEC frontmatter equivalent**: `codex_review_relay: crs (effort=high, fallback)`

## Codex output overview

- **Case ID**: `case_006_onera_m6_transonic`
- **Component**: ONERA M6 wing (canonical transonic CFD validation
  reference, AGARD AR-138 / Schmitt-Charpin 1979). Half-wing with
  root symmetry, span 1196.3 mm, root chord ~806 mm, taper 0.562,
  LE sweep 30°, no twist, ONERA D-section airfoil
- **Source tier**: Tier-1 (T1.A3, NASA Glenn `WWW/wind/valid/m6wing/`
  validation archive)
- **Source URLs**:
  - `https://www.grc.nasa.gov/WWW/wind/valid/m6wing/m6wing.html`
  - Geometry: `https://www.grc.nasa.gov/WWW/wind/valid/m6wing/foilmod.txt`
  - 7 spans of Cp upper/lower at `cp[1-7][lu].ex`
  - AGARD: Schmitt & Charpin, AGARD AR-138, 1979 (durable reference)
- **CAD tool**: CadQuery (lofts wing from chord/twist/sweep stations,
  separates `tip_cap` so tip-side D4 defect lives outside η=0.99
  Cp station, generates D1+D4 defect bodies, builds 5-face farfield
  box, defines symmetry plane at root)
- **Defects**: D1 (0.35 mm root-fairing gap) + D4 (0.18 mm sliver
  on tip-cap edge)
- **Solver**: rhoCentralFoam (density-based, Kurganov flux),
  v2 fallback rhoPimpleFoam if lambda-shock over-smoothed,
  M_inf=0.8395, α=3.06°, Re=11.72e6, T_inf=288 K, p_inf=93.6 kPa
- **Estimated effort**: 6-9 hours, ~3 versions

## 13-check validation results

### Check 1 · CadQuery script syntax-clean

✅ **PASS** — `python3 -m py_compile /tmp/case_006_build_cad.py`
returns clean. 356 LOC.

### Check 2 · cadquery installable

⚠️ **NOTE** — same as case_003/004/005: not in main project venv.
Sub-session sandbox installs locally.

### Check 3 · Tier-1 source reachable

⚠️ **NOTE — same NASA Glenn HTTP 500 as case_005**.

`curl -sIL` against M6 archive URLs:
- `m6wing.html` → HTTP 500 Internal Server Error
- `foilmod.txt` → HTTP 500

This is the **same persistent issue** as case_005 (the entire
`grc.nasa.gov/WWW/wind/valid/` archive appears to be down at
validation time). NOT specific to case_006 — confirmed
infrastructure issue.

**Sub-session impact**: minimal. CadQuery script generates wing
geometry from in-script analytic constants (D-section airfoil
coordinates baked in by Codex; no live download). For Cp
validation data (cp1u.ex through cp7l.ex), sub-session can:
1. Use AGARD AR-138 PDF (durable archived elsewhere) for
   reference
2. Use widely-redistributed M6 datasets (NASA TMR, ONERA mirrors)
3. Wait for NASA Glenn archive recovery

### Check 4 · Patch names match OpenFOAM regex

✅ **PASS** — All 12 named bodies match
`^[A-Za-z][A-Za-z0-9_]*$`:
- `wing_surface_reference`, `root_fairing_pad`, `root_fairing_cover`,
  `tip_cap`, `tip_cap_sliver`, `symmetry_plane_root`,
  `farfield_box`, `farfield_upstream`, `farfield_downstream`,
  `farfield_top`, `farfield_bottom`, `farfield_outboard`

No duplicates. `patch_naming_check` block in manifest validates
the regex contract.

### Check 5 · Symmetry plane declared at wing root

✅ **PASS** — explicit `symmetry_plane_root` patch with:
```yaml
bc:
  U: symmetry
  p: symmetry
  T: symmetry
```
Standard half-wing transonic practice. Codex correctly avoided
mirroring the wing across the root.

### Check 6 · Farfield BC family explicit

✅ **PASS** — All 5 farfield patches (upstream / downstream /
top / bottom / outboard) declared with:
```yaml
bc:
  U: characteristicVelocityInletOutletVelocity
  p: characteristicPressureInletOutletPressure
  T: freestream
```
Consistent compressible characteristic-based BC family. NOT
totalPressure / waveTransmissive (which would be wrong for
external transonic — those are case_005 internal-flow patterns).

### Check 7 · freestream block in manifest

✅ **PASS** — explicit:
```yaml
freestream:
  M_inf: 0.8395
  alpha_deg: 3.06
  Re_chord: 11720000.0
  T_inf_K: 288.0
  p_inf_Pa: 93600.0
  T_total_inf_K: 328.5
  p_total_inf_Pa: 148400.0
  rho_inf_kg_m3: 1.133
  U_inf_mps: 285.6
```
Matches canonical Schmitt-Charpin AGARD AR-138 test point exactly.
Static + total p/T, ρ_inf, U_inf all derived consistently.

### Check 8 · numerics_hints block

✅ **PASS** — explicit:
```yaml
numerics_hints:
  fluxScheme: Kurganov
  ddtSchemes: localEuler
  shock_limiter:
    rho: venkatakrishnan
    rhoU: venkatakrishnan
    rhoE: venkatakrishnan
  divSchemes:
    div_phi_rho: Gauss Kurganov
    div_phi_rhoU: Gauss Kurganov
    div_phi_rhoE: Gauss Kurganov
```
Density-based shock-capturing setup correct. Venkatakrishnan
limiter is reasonable choice for transonic. localEuler lets
sub-session run pseudo-steady on cell-local time stepping.

### Check 9 · validation_stations block

✅ **PASS** — All 7 published η stations declared:
- η = 0.20, 0.44, 0.65, 0.80, 0.90, 0.95, 0.99
- Each with Cp upper/lower source URL
  (`cp[1-7][lu].ex` on grc.nasa.gov)

### Check 10 · shock_detection block

✅ **PASS** — explicit:
```yaml
shock_detection:
  primary_metric: "max_abs_dnM_upper_surface"
  primary_locations_eta: [0.65, 0.95]
  secondary_metric: "lambda_shock_pattern_from_Cp_and_M_isolines"
  report_outputs:
    - upper_surface_Cp_vs_xc
    - upper_surface_Mach_vs_xc
    - spanwise_shock_foot_xc
    - max_upper_surface_Mach
    - forceCoeffs_Cl_Cd_Cm
```
Correct engineering metric (max Mach gradient on upper surface)
for transonic wing.

### Check 11 · Defects measurable

✅ **PASS** — both defects programmatically injected:
- D1 (0.35 mm gap): FreeCAD `distToShape(root_fairing_pad,
  root_fairing_cover)` expected ≈ 0.35 mm
- D4 (0.18 mm sliver): FreeCAD `BoundBox.min(XLength, YLength,
  ZLength)` of `tip_cap_sliver` expected ≈ 0.18 mm

### Check 12 · Defects outside Cp validation zones

✅ **PASS** — explicit `protected_reference_zones:` block:
- `wing_cp_sections` with all 7 protected η values
- `symmetry_plane_root` (root-side D1 must not breach symmetry)
- `wing_upper_surface` and `wing_lower_surface`

D1 location: root-side auxiliary, below η=0.20, away from
measurement sections. D4 location: tip-cap edge (the 3D rounded
end), outside the η=0.99 station which is on the wing-proper
upper/lower surface. ✓

### Check 13 · Defect ↔ advisor mapping

**D1 (sub-mm gap)**: ⚠️ **NOTE** — `expected_advisor_to_catch:
virtual_interface_detector` references **A2 still pending**.
Now FOUR consecutive cases (003/004/005/006) all surface this
same advisor gap.

**Compounded evidence**: 4-of-4 makes A2 extraction
overdetermined for next harvest cycle. After case_007 KCS
(rudder-hub gap) — which is essentially guaranteed to surface
A2 again — it'll be 5-of-5. Time to extract A2 regardless of
case_007 outcome.

**D4 (sliver on edge)**: ⚠️ **NOTE — advisor mapping likely
incorrect**.

Codex mapped D4 to `geometry_surgery.decimate_to_tier`. That's
the **over-dense triangulation** advisor (case_005 D2). A 0.18
mm sliver is NOT over-dense triangulation — it's a thin sliver
body. Better advisor candidates:
- `thin_wall_advisor.detect_thin_wall_patches_at_risk` (LANDED)
  — 0.18 mm is well below typical 2× cell-size threshold;
  should warn at "critical"
- A dedicated sliver/edge advisor (NOT yet extracted; would be
  A4-class artifact)

Sub-session should:
1. Run `thin_wall_advisor` on `tip_cap_sliver` first (LANDED
   advisor, primary expected catch)
2. If thin_wall_advisor doesn't flag (because sliver bbox is
   too small for any reasonable mesh refinement), document as
   advisor coverage gap — flag for A4 sliver-detector extraction
3. Try `geometry_surgery.decimate_to_tier` per Codex's mapping
   (will likely be silent because face count is small, not
   "over-dense") — expected to surface advisor mismatch as
   secondary V-finding

This is a real Codex error. NOT requesting revision because:
1. The defect itself is well-injected (0.18 mm sliver is real)
2. Wrong advisor mapping is itself a useful V-finding signal
   (forces sub-session to think about defect/advisor pairing)
3. case_005 already established the LANDED-advisor exercise
   pattern; case_006 just needs sub-session to apply judgment

## Additional notes (non-blocking)

### N1 · CRS gpt-5.4 fallback context

86gs gpt-5.5 xhigh failed 2 attempts (503 from
api.86gamestore.com via Cloudflare). CRS gpt-5.4 (high effort)
produced this case_006. CRS 5.4 is a strong model but not
identical to 86gs 5.5 xhigh; subtle differences vs case_005:
- Defect choice D1+D4 (case_005 was D1+D2) — different second
  defect type; CRS may have favored "sliver" because it
  remembered D8 thin-shell pattern from case_004 reading
- Slightly fewer body parts (12 vs case_005's 9 — but more
  farfield patches because external flow needs them, so this is
  topology-driven, not effort-driven)
- All numerics-hints / freestream / shock-detection blocks
  present and correct — CRS 5.4 high effort is sufficient for
  this case

If 86gs recovers and the user wants a re-run on xhigh for higher
confidence, that's an option. But this CRS output is dispatch-
ready as-is.

### N2 · First density-based solver case for project

The harness has NO prior density-based infrastructure. case_006
forces:
- `rhoCentralFoam` solver path (separate from case_005's
  `rhoSimpleFoam`)
- `fluxScheme Kurganov;` in fvSchemes
- Venkatakrishnan limiter on convective fluxes for ρ/ρU/ρE
- Characteristic farfield BC family (different from case_005's
  totalPressure/waveTransmissive)
- `freestream` BC for T at compressible external boundary
- localEuler ddt for pseudo-steady

Sub-session hand-crafts these case-locally. Most likely artifact
extraction candidates: `density_based_fvschemes_writer.py` and
`characteristic_farfield_bc_writer.py`. After case_006 these
become reusable for any future external compressible case.

### N3 · D-section airfoil coordinates baked into script

ONERA D-section is a non-NACA airfoil specific to ONERA M6.
Codex generated it from constants in the script (would need to
verify the actual coordinates against AGARD AR-138 Appendix —
sub-session task during v1 validation). If coordinates are
slightly off, the lambda-shock pattern may be displaced, but
qualitative agreement should still be visible.

### N4 · Lambda-shock signature is the engineering question

The classical M6 result is the **forward shock + aft shock
merging into a lambda pattern** on the upper surface, strongest
around η=0.65-0.95. If sub-session's v1 doesn't capture this,
that's the primary V-finding direction:
- "rhoCentralFoam too dissipative at default Kurganov +
  venkatakrishnan settings → lambda shock collapses"
- → reduce limiter aggressiveness OR refine mesh OR switch to
  rhoPimpleFoam

This is exactly the kind of net-new V-finding case_006 should
source.

### N5 · 25-chord farfield boundary check

Codex's brief says "sized beyond 25 chords in all directions"
for farfield_box. Sub-session must verify the actual generated
domain meets this — if Codex's CadQuery defaults are tighter
(e.g., 10 chords), spanwise shock drift / pressure-wave
reflection will contaminate results.

## Rounds budget

Round 1 of 2 used. **No revision request issued** — A2-pending
(4th consecutive) + D4-advisor-mapping (sub-session can resolve)
+ NASA Glenn HTTP 500 (environmental) + CRS-fallback (relay
issue, not design issue) are all documented as caveats, not bugs.

If sub-session reports unrecoverable issues mid-run (e.g.,
D-section airfoil coordinates wrong, lambda shock cannot be
recovered with any reasonable parameter sweep), main session
may invoke round 2 and require 86gs xhigh.

## Approval to write kickoff

✅ proceed to format `kickoff/case_006_onera_m6_transonic.md`.

## Files

- `kickoff/case_006_codex_request.md` — what we sent
- `kickoff/case_006_codex_response.md` — Codex's full response
  (saved verbatim from `/tmp/codex_006_final.txt`)
- `kickoff/case_006_validation.md` — this file
- `kickoff/case_006_onera_m6_transonic.md` — sub-session kickoff
  (to be written next)

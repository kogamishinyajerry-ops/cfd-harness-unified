# Case 020 · Porous Media Filter (Darcy-Forchheimer) · Sub-Session Kickoff

> Paste between `=== BEGIN ===` and `=== END ===` into a fresh
> Claude Code session. Designed by Codex (gpt-5.4 high, CRS,
> 117k tok single-round emit). Validated 2026-05-08 — see
> `case_020_validation.md`. PASS.
>
> **Phase 4 #4 (FINAL) of industrial-extension batch** — closes
> the 11-case industrial-extension batch (case_011-020) into
> harvest cycle 003.
>
> **D10 FIRST INJECTION in project** — no LANDED advisor for
> open-shell / non-watertight detection. Manual FreeCAD
> verification + flag advisor-gap V-finding.
>
> **D9 2nd or 3rd injection** — accumulating advisor-gap
> evidence (after case_016 cavity LE/TE + case_017 faceted pins).

=== BEGIN ===

You are a Claude Code sub-session under cfd-harness-unified
orchestration. Task: **case_020_porous_media_filter_darcy_forchheimer**.

**Phase 4 #4 (FINAL)** — closes the 11-case industrial-extension
batch into harvest cycle 003.

## Project context
20 prior cases (002a/b + 003-019). case_020 is the FINAL case in
the industrial-extension batch.

## Required reading
1. `.planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md`
2. `.planning/strategic/case_013_020_dispatch_plan_2026-05-08.md`
3. `.planning/case_proposal_queue.md`
4. **`.planning/methodology/kickoff/case_003_codex_response.md`** — incompressible-RANS inheritance
5. `.planning/methodology/kickoff/case_016_codex_response.md` — D9 first-injection precedent
6. `.planning/methodology/kickoff/case_017_codex_response.md` — D9 2nd-injection precedent (multi-region)
7. `.planning/case_profiles/case_003_crm_hls_boundary_layer.md`
8. `.planning/methodology/industrial_case_solver_findings.md`
9. `.planning/methodology/knowledge_status_convention.md`
10. `.planning/methodology/kickoff/case_020_codex_response.md`
11. `.planning/methodology/kickoff/case_020_validation.md`

## Hard guardrails
1. V130 advisory · V132 no AI-mutating routes
2. No date/calendar gating
3. **No advisors for D9 or D10** — manual FreeCAD verification
4. Do NOT redesign — round-cap=3
5. **simpleFoam steady + DarcyForchheimer fvOption** (single-region)
6. **Anisotropic resistance tensor** — streamwise < cross-stream
7. **No new defects outside D1-D10**

## Case identifier
`case_020_porous_media_filter_darcy_forchheimer` · solver-class
**simpleFoam + fvOption explicitPorositySource** · numerics-class
**incompressible-RANS + Darcy-Forchheimer** (extends case_003)

## Codex brief summary
- Component: HEPA terminal filter cassette in rounded-rectangle
  HVAC housing (Tier-3 parametric)
- Geometry: filter housing + porous cassette + upstream/downstream
  plena (per Codex CAD; rounded corners with R=18 mm reference)
- Operating point: air at standard conditions, U_face=2.5 m/s,
  Re_housing≈3.3e4
- Porous source: Darcy-Forchheimer anisotropic tensor (streamwise
  resistance < cross-stream); coordinate-system basis explicit
- Defects:
  - **D9**: 16-facet approximation of housing corner curvature
    (vs smooth R=18 mm reference)
  - **D10**: 1.0 mm slit at one filter-frame corner connecting
    upstream + downstream plenums (FIRST D10 INJECTION)
- Effort: 8h, ~3 versions

## Codex CAD script (deliverable 2)
Save at `scripts/build_cad.py`. 167 LOC, deterministic.

```bash
cd ~/Desktop/case_020_porous_media_filter
python3 -m venv .venv
.venv/bin/pip install cadquery numpy pyyaml jinja2 trimesh
python scripts/build_cad.py --out inputs/cad_codex_v1.step
```

## Porous + leak setup (case_020 main work)

### `00_check_region.py`
Verify STEP has region_fluid + porous_zone_filter_element cellZone
+ all named patches.

### `02_blockmesh_shm.py`
blockMesh + sHM with refinement near filter face + filter_edge_seal
+ filter_edge_open_d10 leak path.

### `03_write_thermophysical.py`
Air at standard conditions.

### `04_write_BCs.py`
- inlet: flowRateInletVelocity at U_face=2.5 m/s
- outlet: pressureOutlet (p=0)
- housing_wall: noSlip
- filter_element_face_upstream / downstream: internal porous-zone
  faces (drag from fvOptions, not BC)
- filter_edge_seal: noSlip
- filter_edge_open_d10: noSlip on slit walls (leak path is gap
  geometry-driven, not BC-driven)

### `05_write_fvOptions.py`
```
porous_zone_filter_element
{
    type            explicitPorositySource;
    active          yes;
    explicitPorositySourceCoeffs
    {
        selectionMode   cellZone;
        cellZone        porous_zone_filter_element;
        type            DarcyForchheimer;
        DarcyForchheimerCoeffs
        {
            d (D_streamwise D_cross D_cross);
            f (F_streamwise F_cross F_cross);
            coordinateSystem
            {
                origin (... ... ...);
                e1 (1 0 0);  // streamwise
                e2 (0 1 0);  // cross-1
            }
        }
    }
}
```
D and F values per ERCOFTAC reference OR derived from filter-spec
Δp curve.

### `06_write_fvSchemes.py`
Steady incompressible:
- ddt: steadyState
- divSchemes: linearUpwind grad(U)
- gradSchemes: Gauss linear
- laplacianSchemes: Gauss linear corrected

### `07_run_solver.sh`
simpleFoam to convergence (residuals < 1e-5).

### `08_compute_dp_filter.py`
Δp_filter = ∫ p_inlet dA / A_inlet - ∫ p_outlet dA / A_outlet

### `09_compute_uniformity.py`
At downstream sampling plane, compute σ_U / U_mean.
Target: documented filter design value ± 0.05.

### `10_compute_bypass_flow.py`
Calculate bypass flow through D10 slit:
- Sample U on a small surface across the slit width
- ṁ_bypass = ∫ ρ U · n dA on slit surface
- Bypass fraction = ṁ_bypass / ṁ_total
- Document as % of total inlet flow

### `11_compute_anisotropic_split.py`
At a sampling plane within porous_zone:
- Sample U_streamwise vs U_cross_stream
- Verify anisotropic forcing (streamwise should dominate;
  cross-stream should be heavily damped)
- This validates Darcy-Forchheimer tensor implementation

## Defect verification

### D9 (16-facet housing corner) — NO LANDED ADVISOR

> 2nd or 3rd D9 injection (case_016 first, case_017 2nd if landed).

**Step 1**: FreeCAD chord-length comparison vs smooth R=18 mm
reference arc.
**Step 2**: Document max chord deviation.
**Step 3**: V-finding: D9 advisor-gap accumulating evidence.
Post-Phase-4 retro: D9 advisor-candidate decision based on
3+ data points.

### D10 (1.0 mm slit at filter-frame corner) — NO LANDED ADVISOR

> **FIRST D10 INJECTION in project**. Closes the defect-catalog
> coverage (D1-D10 except D3 + D4).

**Step 1**: FreeCAD watertight check on filter_edge_seal +
filter_edge_open_d10 region.
**Step 2**: Measure clear slit width:
```python
import FreeCAD as App
import Import
doc = App.newDocument()
Import.insert('inputs/cad_codex_v1.step', doc.Name)
seal = next(x for x in doc.Objects if x.Label == 'filter_edge_seal')
slit = next(x for x in doc.Objects if x.Label == 'filter_edge_open_d10')
gap = seal.Shape.distToShape(slit.Shape)[0]
print(f"D10 slit width: {gap:.3f} mm")
# Expected: 1.0 mm
```
**Step 3**: Confirm continuous leak path through seal thickness.
**Step 4**: V-finding: **NEW D10 advisor-gap V-finding for harvest
003 retro** — non-watertight shell detection capability candidate.

## Six per-case standard moves

1. Reference profile at `case_profiles/case_020_porous_media_filter_darcy_forchheimer.md`
2. V-series append: porous source sign convention (drag opposes
   flow), coordinateSystem basis for anisotropic tensor, D10
   bypass flow effect on Δp + uniformity, D9 facet edge local
   separation. **NEW D10 advisor-gap V-finding**, **2nd-3rd D9
   evidence**.
3. Playbook S15+ candidates:
   - "Δp wrong sign → check porous source coefficient
     coordinateSystem orientation"
   - "Bypass through D10 distorts Δp prediction by 20-50% →
     document leak path geometry separately"
   - "Anisotropic tensor not enforced → flow goes around filter
     instead of through"
4. Stale-assumption fixes: case_003 templates may need
   Darcy-Forchheimer fvOptions variants. Commit tag pattern.
5. Artifact extraction (3 likely):
   - `darcy_forchheimer_writer.py`
   - `bypass_flow_advisor.py`
   - `filter_dp_uniformity_post_processor.py`
6. RAG corpus: 5 artifacts.

## Sandbox structure
```
~/Desktop/case_020_porous_media_filter/
├── README.md, Makefile, .venv/
├── inputs/, templates/, scripts/, case/, evidence/
```

## Sediment + commit convention
Same as cases 011-019.

## Boundaries
- CAN: end-to-end run, sandbox, sediment, <250 LOC artifact extraction (3)
- CANNOT: redesign, scalar transport (case_019 territory),
  chtMultiRegion (single-region only), exceed 8h

## Known issues
1. **D10 first injection — no advisor** — closes defect catalog
   except D3/D4; flag advisor-gap V-finding for harvest 003 retro
2. **D9 2nd-3rd evidence** — accumulating evidence; harvest 003
   retro evaluates D9 advisor-candidate sub-DEC priority
3. **Porous source sign convention** — easy to flip drag direction
4. **coordinateSystem basis** — wrong rotation rotates anisotropic
   tensor; flow goes WRONG direction
5. **D10 bypass effect** — quantitatively distorts Δp + uniformity;
   important to separate clean-baseline from defected case

## Strategic role within batch — BATCH CLOSE

After case_020 lands, the **11-case industrial-extension batch
(case_011-020) is fully dispatched + sedimented**. Triggers:

### Harvest cycle 003 (full mode)

Scope: all 11 industrial-extension cases (002b/003-008/011-020).

Topics:
1. **Defect catalog coverage analysis** — D1 (11×), D2 (1×), D5
   (2×), D6 (2×), D7 (2×), D8 (3×), D9 (3×), D10 (1×). D3 + D4
   uncovered (carry to next batch).
2. **Advisor-gap consolidation** — D6 / D7 / D9 / D10 all surfaced
   during Phase 1-4. Harvest 003 proposes A4-A8 advisor sub-DECs
   as warranted by evidence count + topology breadth.
3. **A2-v2 sub-DEC priority** — 12 D1 cross-topology PASSes all
   `[QUESTIONABLE]`. A2-v2 implementation must close this debt
   before next batch.
4. **A3-v2 sub-DEC priority** — case_005 V17 + case_009 + case_019
   provide 3 data points; cross-case stability decision.
5. **Component bank refinement** — A1a (compact HX, case_011) +
   A1b (pin-fin heatsink, case_017) split. New entries for
   D-class pumps + compressors + cyclone + mixer + filter.
6. **Compound numerics root validation** — case_015 (LES+CHT) +
   case_016 (compressible-DES) confirm compound-root methodology.
7. **Strategic doc successor** — `case_021_030_*.md` for next
   batch (likely D3/D4 defect coverage + advisor-gap closure
   cases + remaining industry verticals).

### Industry capability inventory (post-batch)

The harness now demonstrates capability across:
- Buoyant ventilation (002a, 012)
- Multi-region CHT (002b, 011, 015, 017)
- External aero (003, 010)
- Confined rotating (013, 014)
- Open rotor (004)
- Compressible RANS (005, 006, 014)
- Multiphase VOF (007)
- Lagrangian particle (008, 018)
- Reacting low-Mach (009)
- LES (010, 015)
- DES + acoustic (016)
- Scalar transport (019)
- Porous media (020)
- Phase change cavitation (013)

This is **the workhorse OpenFOAM solver matrix at industrial
scale + service-oriented form factors**.

=== END ===

## Main session post-dispatch checklist
- [ ] Move case_020 to Dispatched
- [ ] Update case_index.md / INDEX.md
- [ ] When sub-session reports D10 outcome: **NEW D10 advisor-gap
      V-finding for harvest 003 retro** (closes catalog gap
      analysis except D3/D4)
- [ ] When sub-session reports D9 outcome: 2nd-3rd D9 evidence
      (consolidates with case_016 + 017 if 017 sediment landed first)
- [ ] **TRIGGER HARVEST CYCLE 003** (full mode) once cases 011-020
      sediments are all in
- [ ] Begin `case_021_030_*.md` strategic doc for next batch

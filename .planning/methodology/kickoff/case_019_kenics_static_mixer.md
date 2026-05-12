# Case 019 · Kenics Static Mixer · Sub-Session Kickoff

> Paste between `=== BEGIN ===` and `=== END ===` into a fresh
> Claude Code session. Designed by Codex (gpt-5.4 high, CRS, 183k
> tok single-round emit). Validated 2026-05-08 — see
> `case_019_validation.md`. PASS.
>
> **Phase 4 #3 of industrial-extension batch** — process-industry
> classic; extends case_003 incompressible-RANS to scalar transport.
>
> **D2 over-dense triangulation** — A3 advisor stress-test
> (`geometry_surgery.decimate_to_tier`); status still
> `[QUESTIONABLE]` per V17 (case_005 partial outcome) pending
> case_009 D2 sediment.

=== BEGIN ===

You are a Claude Code sub-session under cfd-harness-unified
orchestration. Task: **case_019_kenics_static_mixer**.

**Phase 4 #3** — process-industry classic.

## Project context
19 prior cases (002a/b + 003-018).

## Required reading
1. `.planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md`
2. `.planning/strategic/case_013_020_dispatch_plan_2026-05-08.md`
3. `.planning/case_proposal_queue.md`
4. **`.planning/methodology/kickoff/case_003_codex_response.md`** — incompressible-RANS inheritance
5. `.planning/methodology/kickoff/case_009_codex_response.md` — D2 precedent
6. `.planning/case_profiles/case_003_crm_hls_boundary_layer.md`
7. `.planning/methodology/industrial_case_solver_findings.md` (V17 from case_005)
8. `.planning/methodology/knowledge_status_convention.md`
9. `.planning/methodology/kickoff/case_019_codex_response.md`
10. `.planning/methodology/kickoff/case_019_validation.md`

## Hard guardrails
1. V130 advisory · V132 no AI-mutating routes
2. No date/calendar gating
3. Use `geometry_surgery.decimate_to_tier` for D2 (A3 LANDED, V17 partial)
4. Do NOT redesign — round-cap=3
5. **simpleFoam steady + scalar transport** (NOT turbulent k-ε at Re<2300)
6. **No new defects outside D1-D10**

## Case identifier
`case_019_kenics_static_mixer` · solver-class
**simpleFoam + scalar transport** · numerics-class
**incompressible-RANS + scalar** (extends case_003)

## Codex brief summary
- Component: Kenics static mixer (Tier-3 fallback)
- Geometry: D=80 mm pipe, 8 helical elements, L_per_element=1.5 D,
  180° twist within element, 90° rotation between elements,
  element thickness 1.5 mm, upstream 3D, downstream 5D
- Operating point: water, Re=3200 (transitional)
- Tracer: passive scalar T step injection at inlet (T=1 upstream,
  T=0 elsewhere)
- Sc_t=0.7
- Defect: **D2** — element 3 over-dense triangulation
  (baseline ~5k → target 80k tris)
- Effort: 8h, ~3 versions

## Codex CAD script (deliverable 2)
Save at `scripts/build_cad.py`. 120 LOC, deterministic.

```bash
cd ~/Desktop/case_019_kenics_static_mixer
python3 -m venv .venv
.venv/bin/pip install cadquery numpy pyyaml jinja2 trimesh
python scripts/build_cad.py --out inputs/cad_codex_v1.step
```

## Scalar transport setup (case_019 main work)

### `00_check_region.py`
Verify STEP has region_fluid + 8 mixer_element_<i> patches.

### `02_blockmesh_shm.py`
blockMesh + sHM; refine helical element surfaces.

### `03_write_thermophysical.py`
Water Newtonian.

### `04_write_BCs.py`
- pipe_inlet: flowRateInletVelocity at Re=3200 ṁ; T fixedValue 1.0
- pipe_outlet: pressureOutlet; T zeroGradient
- pipe_wall: noSlip; T zeroGradient
- mixer_element_1..8: noSlip; T zeroGradient

### `05_write_scalar_transport.py`
Add T equation to fvSchemes/fvSolution:
```
divSchemes
{
    div(phi,T)  Gauss limitedLinear 1;
}
```

### `06_run_solver.sh`
1. Solve U + p (steady) to convergence
2. Then solve T transport on frozen U field (or coupled)

### `07_compute_RTD_F_curve.py`
- Step injection T=1 at t=0 at inlet
- Sample T(t) at outlet plane
- F(t) = c_outlet(t) / c_inlet
- Plot F(t); identify mean residence time τ = ∫₀^∞ t dF(t)

### `08_compute_COV.py`
COV at outlet plane = σ_T / T_mean
Compare to Kenics mixer correlation: COV ≤ 0.05 typical for
N ≥ 6 elements.

### `09_compute_pressure_drop.py`
- Per-element Δp from pressure probes between elements
- Total Δp from inlet to outlet
- Compare to Kenics correlation Z_static = Δp_static / Δp_empty
  (typical Z_static ≈ 6-7 for 6-8 elements)

## Defect verification

### D2 (element 3 over-dense 80k tris) — A3 advisor LANDED [QUESTIONABLE V17]

> A3 (`geometry_surgery.decimate_to_tier`) LANDED but case_005 v1
> outcome was PARTIAL (V17 redundancy gap). Status of A3
> cross-case behavior depends on case_009 D2 sediment.

**Step 1**: FreeCAD triangulation count on element 3 vs reference
~5k baseline; expected ≈80k.

**Step 2**: Exercise A3:
```python
from ui.backend.services.geometry_ingest.geometry_surgery import (
    decimate_to_tier
)
result = decimate_to_tier(step_path, element_index=3,
                          target_tier="standard")
# Check whether A3 surfaces D2 condition cleanly or PARTIAL per V17
```

**Step 3**: V-finding judgment:
- If A3 surfaces D2 cleanly: V17 status updates toward closure
  (3rd consistent data point if case_009 also clean)
- If A3 PARTIAL: V17 reinforced; flag A3-v2 sub-DEC priority
- Apply [QUESTIONABLE] marker until cross-case stability confirmed

## Six per-case standard moves

1. Reference profile at `case_profiles/case_019_kenics_static_mixer.md`
2. V-series append: scalar transport convergence vs flow,
   transitional stability at Re≈2300, helical-element meshing,
   COV time-averaging convergence. **A3 cross-case stability data
   point**.
3. Playbook S15+ candidates:
   - "RTD F(t) shape wrong → check inlet step-injection BC
     transient rise time"
   - "COV > 0.05 → check tracer diffusivity / mesh near elements"
   - "Δp off Z_static → check helical element edge resolution"
4. Stale-assumption fixes: case_003 templates may need scalar
   transport variants. Commit tag pattern.
5. Artifact extraction (3 likely):
   - `rtd_F_curve_calculator.py`
   - `cov_computer.py`
   - `static_mixer_dp_advisor.py`
6. RAG corpus: 5 artifacts.

## Sandbox structure
```
~/Desktop/case_019_kenics_static_mixer/
├── README.md, Makefile, .venv/
├── inputs/, templates/, scripts/, case/, evidence/
```

## Sediment + commit convention
Same as cases 011-018.

## Boundaries
- CAN: end-to-end run, sandbox, sediment, <250 LOC artifact extraction (3)
- CANNOT: redesign, k-ε at Re<2300 without rationale, exceed 8h

## Known issues
1. **A3 [QUESTIONABLE] V17** — A3 cross-case behavior under test
2. **Transitional regime Re=3200** — turbulence model selection
   sensitive
3. **Scalar convergence** — T equation typically slower than U;
   monitor separately
4. **Helical element meshing** — curved surfaces require boundary
   layer refinement

## Strategic role within batch

After case_019 lands, project demonstrates:
- simpleFoam + scalar transport composes cleanly
- RTD + COV process-industry KPIs
- A3 cross-case stability data point (3rd if case_009 also done)
- Industry sectors: chemical / polymer / food / pharma

This is **Phase 4 #3**; case_020 (porous filter) closes Phase 4
and the entire 11-case industrial-extension batch.

=== END ===

## Main session post-dispatch checklist
- [ ] Move case_019 to Dispatched
- [ ] Update case_index.md / INDEX.md
- [ ] When sub-session reports D2 outcome: A3 cross-case stability
      data point; V17 status update if clean
- [ ] When sub-session extracts RTD / COV post-processors: evaluate promotion

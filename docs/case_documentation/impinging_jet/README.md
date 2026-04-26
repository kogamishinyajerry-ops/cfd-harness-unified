# Axisymmetric Impinging Jet (Re=10000)

> Case ID: `impinging_jet` · Whitelist row 8 · Status: **INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE** + reference values PROVISIONAL
> GOV-1 enrichment · 2026-04-26 · Option B
>
> ⚠️ Two compounding hazards: (1) adapter produces 2D planar slice, **not** axisymmetric wedge; (2) buoyantFoam under-converges (A4 p_rgh iteration-cap). Reference Nu values flagged HOLD pending Behnad 2013 re-read. See [`failure_notes.md`](failure_notes.md).

## Physics description (intended)

Axisymmetric heated impinging jet: a circular nozzle of diameter D=0.05 m emits a vertical jet at Re=10000 onto a heated flat plate at distance H = 2D from the nozzle exit. Stagnation flow on the plate produces a peak in the local Nusselt number at r=0, decaying with r/D as the jet spreads radially.

- Re = 10000 (nozzle diameter × jet velocity / ν)
- Solver: `simpleFoam` (steady SIMPLE) + k-ε (whitelist; modern standard would be v2f or k-ω SST for impinging flows)
- h/d = 2.0 (nozzle-to-plate distance / nozzle diameter)
- Mesh: 4800 cells (IMPINGING_JET adapter path)

## Physics description (current adapter)

The current adapter generates a **2D planar slice**, not an axisymmetric wedge. Specifically `foam_agent_adapter.py:5184-5185` declares the axis patch as `empty`, not `wedge`. A 2D-planar slice has fundamentally different stagnation-region dynamics than a true axisymmetric flow because azimuthal convergence of streamlines is absent.

## Expected behavior (Cooper 1984 / Behnad 2013)

| Observable | Reference | Status |
|---|---|---|
| `nusselt_number` at r/d=0 (stagnation peak) | 25.0 (PROVISIONAL — Gate Q-new Case 9 HOLD) | Audit flagged 4-5× discrepancy vs Behnad 2013 (~110-130); paper re-read pending |
| `nusselt_number` at r/d=1.0 | 12.0 (PROVISIONAL) | Same HOLD scope |

## Boundary-condition compatibility

| BC type | Compatible? | Notes |
|---|---|---|
| Wedge axis + nozzle inlet + heated plate + outflow | ✅ Canonical | Cooper 1984 anchor (true axisymmetric) |
| Empty axis (2D planar) | ❌ Wrong topology | Current adapter — silent simplification |
| Adiabatic plate (momentum-only) | ❌ No Nu observable | Different validation target |
| Confined-jet geometry (h/d small, walls close) | ⚠️ Different anchor | Different correlation family; not Cooper 1984 |
| Free-jet (large h/d, no plate) | ❌ Different physics | Self-similar far-field; needs separate gold |
| Compressible / heated jet at high Re | ⚠️ Out of scope | Cooper 1984 is incompressible Re=10000 |

## Tolerance → citation map

| Observable | Tolerance | Citation key | Type |
|---|---|---|---|
| `nusselt_number` (r/d=0, r/d=1.0) | 0.15 (relative) | `TBD-GOV1` | Reference values themselves are PROVISIONAL pending Behnad 2013 paper re-read (4-5× discrepancy with audit estimate). Tolerance band 15% is engineering, but the gold value uncertainty currently exceeds the band. Honest TBD until literature re-source closes the gold-value question. |

Citation coverage: 0/1 = 0% (the gold values are themselves on hold; tolerance citation is meaningless until gold is re-anchored).

## Geometry sketch (intended axisymmetric)

```
      ↓ jet, D=0.05 m
   ┌──┴──┐  nozzle (Re=10000)
   │     │
   │     │  h = 2D
   │     │
   │     │
═══╧══●══╧═══════════════════════════  heated plate (T_w fixed)
   ↑     ↑   ↑   ↑           
   r=0   r/D=0.5 1.0
        Nu(r) decays from peak
```

Current adapter generates this as a 2D planar slice (axis patch `empty`), missing the azimuthal converging streamlines that drive the stagnation peak.

## Known good results

- None — the case currently reports ATTEST_FAIL via A4 solver iteration-cap (`p_rgh` GAMG repeatedly hitting the 1000-iter cap)
- Historical fixture pathology recorded in STATE.md:455: `ref_value=0.0042 is the adapter's Cf, not the Cooper Nu=25; honest but makes PASS vacuous` — value-leakage from Cf into the Nu observable slot

## References

See [`citations.bib`](citations.bib). Key refs: Cooper et al. 1984 (experimental), Behnad et al. 2013 (computational, the source of the gold-value uncertainty), ASME V&V 20-2009.

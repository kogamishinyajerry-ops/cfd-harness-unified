# Fully Developed Plane Channel Flow (DNS)

> Case ID: `plane_channel_flow` · Whitelist row 7 · Status: **INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE**
> GOV-1 enrichment · 2026-04-26 · Option B
>
> ⚠️ This case currently reports ATTEST_PASS via a comparator-path artifact, but the physics-honest verdict is **FAIL**. See [`failure_notes.md`](failure_notes.md) for the disguised-incompatibility analysis.

## Physics description (intended)

Two-dimensional fully developed turbulent plane-channel flow with periodic streamwise BC and no-slip walls. Re_τ = u_τ·h/ν = 180 (friction Reynolds), corresponding to Re_bulk ≈ 5600. The canonical reference is Kim, Moin & Moser 1987 / Moser, Kim & Mansour 1999 DNS, which reports the law-of-the-wall u⁺ vs y⁺ profile:
- viscous sublayer: u⁺ = y⁺ for y⁺ ≤ 5
- log-law: u⁺ = (1/κ)·ln(y⁺) + B with κ=0.41, B=5.2 for y⁺ ≳ 30

## Physics description (current adapter)

The current adapter generates a laminar icoFoam (transient PISO incompressible **laminar** N-S) configuration at Re_bulk=5600 — which converges to the **Poiseuille parabolic profile**, **not** the turbulent log-law. The reference u⁺ values (5.4 at y⁺=5, 13.5 at y⁺=30) are fundamentally inaccessible from a laminar solver.

- Re_bulk = 5600 (intended Re_τ = 180 via u_τ·h/ν)
- Solver (current): `icoFoam` + laminar — INCOMPATIBLE with the turbulent DNS reference
- Mesh: 4000 cells (BODY_IN_CHANNEL adapter)
- Geometry: plane-channel slab, half-height D/2=0.5 m, streamwise length 2L=30 m, empty front/back

## Expected behavior (Kim 1987 / Moser 1999, Re_τ=180)

| Observable | y+ | u+ | Source |
|---|---|---|---|
| `u_mean_profile` | 0.0 | 0.0 (no-slip) | Kim/Moser DNS |
|  | 5.0 | 5.4 (sublayer top) | Kim/Moser DNS |
|  | 30.0 | 13.5 = (1/0.41)·ln(30) + 5.2 (log-law region; updated DEC-V61-006) | Moser 1999 |
|  | 100.0 | 22.8 (channel center) ⚠️ **anomalous**: log-law gives ~16.4, Moser centerline u⁺ ≈ 18.3 | Kim 1987 (suspect) |

## Boundary-condition compatibility

| BC type | Compatible? | Notes |
|---|---|---|
| Periodic streamwise + no-slip walls + driven by ∂p/∂x **AND turbulent solver** | ✅ Canonical (DNS or LES) | Kim/Moser anchor |
| Same BCs but laminar solver | ❌ Wrong physics | Converges to Poiseuille, not turbulent log-law |
| Steady RANS k-ω SST or k-ε with wall function | ⚠️ Different anchor | Different model assumption; not Kim/Moser DNS |
| Inflow/outflow (non-periodic) | ⚠️ Need long L/h to develop | Adds entry-length physics |
| Slip walls | ❌ Removes BL | No log-law generated |

## Tolerance → citation map

| Observable | Tolerance | Citation key | Type |
|---|---|---|---|
| `u_mean_profile` | 0.05 (relative) | `moser1999` | Moser 1999 DNS numerical uncertainty in u⁺ profile is well below 1% on the inner units; 5% covers harness mesh + solver-config drift in the **intended** turbulent setting. **Note**: in the *current* (laminar) adapter, the gold cannot be reproduced at any tolerance — the verdict is structurally FAIL (see failure_notes.md). |

Citation coverage: 1/1 = 100% (literature-anchored to Moser 1999 DNS).

## Geometry sketch

```
   periodic streamwise (length 2L = 30)
        ┌──────────────────────────────┐  y = +D/2 (no-slip)
        │     (intended: turbulent)    │
        │  ▶▶▶ log-law region ▶▶▶     │
        │  ▶▶ buffer ▶▶               │
        │  ▶ viscous sublayer ▶        │
   ↑    ├──────────────────────────────┤  y = 0  (channel mid-plane)
   D    │  ▼ viscous sublayer ▼        │
   ↓    │  ▼▼ buffer ▼▼               │
        │  ▼▼▼ log-law region ▼▼▼     │
        └──────────────────────────────┘  y = -D/2 (no-slip)
```

## Known good results

- Comparator extracts u⁺ + y⁺ correctly (DEC-V61-036c G2, 2026-04-22 widened key-chain)
- ATTEST_PASS recorded on the laminar adapter, but STATE.md:1292-1295 explicitly flags this case as the canonical example of "ATTEST_PASS but Codex physics audit says physically FAIL" — a comparator-path artifact

## References

See [`citations.bib`](citations.bib). Key refs: Kim, Moin & Moser 1987 (primary DNS), Moser, Kim & Mansour 1999 (extended Re_τ DNS), ASME V&V 20-2009.

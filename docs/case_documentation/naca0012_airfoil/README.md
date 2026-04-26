# NACA 0012 Airfoil External Flow

> Case ID: `naca0012_airfoil` · Whitelist row 9 · Status: PARTIALLY_COMPATIBLE → SATISFIED at V61-058 Stage E closeout
> GOV-1 enrichment · 2026-04-26 · Option B

## Physics description

Two-dimensional incompressible external flow over a NACA 0012 symmetric airfoil at Re = 3·10⁶, M ≈ 0.15, parameterized over angle of attack α ∈ {0°, 4°, 8°}. The case is configured at fixed-transition grit-roughness conditions to match Ladson 1988 NASA TM-4074 §3.2 Table 1 (compatible with kOmegaSST + wall-function adapter).

- Re = 3·10⁶, chord length 1.0 m (default; overridable via `task_spec.boundary_conditions.chord_length`)
- Solver: `simpleFoam` (steady SIMPLE) + `kOmegaSST` + Spalding wall function
- Mesh: x-z plane, 80 cells normal, thin span y ±0.001 with empty boundaries (post-DEC-V61-058)
- α-routing: freestream rotation U_inf_vec = U·(cos α, 0, sin α); mesh stays geometry-locked to x-z plane (Codex F2 / OF airFoil2D tutorial precedent)
- Sign convention: α positive → upper-suction → Cl > 0

## Expected behavior (DEC-V61-058 Type II multi-dim arc)

| Observable | Reference | Tolerance | Role | Source |
|---|---|---|---|---|
| `lift_coefficient_alpha_eight` (Cl @ α=8°) | 0.815 ±0.010 | 0.05 | **HEADLINE_PRIMARY_SCALAR** / HARD_GATED | Ladson 1988 TM-4074 Table 1 |
| `pressure_coefficient` Cp(x/c) profile @ α=0° | shape match (6 anchors x/c ∈ {0, 0.1, 0.3, 0.5, 0.7, 0.9}) | 0.20 | PROFILE_GATE (qualitative) | Abbott 1959 Fig. 4-7 + Gregory 1970 Fig. 7 |
| `lift_slope_dCl_dalpha_linear_regime` | 0.105 /deg ±0.005 | 0.10 | QUALITATIVE_GATE (linearity) | 3-point fit through Ladson 1988 |
| `drag_coefficient_alpha_zero` (Cd @ α=0°) | 0.0080 ±0.0010 | 0.15 | SAME_RUN_CROSS_CHECK / HARD_GATED | Ladson 1988 Table 1 |
| `y_plus_max_on_aerofoil` | band [11, 500] | n/a (advisory) | PROVISIONAL_ADVISORY | yPlus FO live measurement |
| `lift_coefficient_alpha_zero` (sanity) | 0.0 (symmetry) | abs `|Cl| < 0.005` | SANITY_CHECK (excluded from gate set) | exact (symmetric airfoil) |

The TE point at x/c=1.0 was DROPPED from the Cp profile per Codex F4: Kutta condition gives Cp_TE ≈ 0; the v1 anchor Cp=0.2 was inconsistent and the cell-band sampler is degenerate at zero-thickness.

## Boundary-condition compatibility

| BC type | Compatible? | Notes |
|---|---|---|
| Far-field freestream + airfoil no-slip + thin span empty | ✅ Canonical | DEC-V61-058 setup |
| α via freestream rotation (mesh locked) | ✅ Canonical | OF airFoil2D tutorial precedent (Codex F2 ruling) |
| α via mesh rotation | ❌ Not implemented | Would need geometry regenerate per α |
| Stall regime (α ≥ 16° at Re=3e6) | ❌ Out of scope | Steady RANS not meaningful in stall |
| Free transition (vs grit-roughness fixed-transition) | ⚠️ Different anchor | Gregory 1970 Fig. 7 free-trans Cp shape; not Ladson Cl/Cd values |
| Compressible (M > 0.3) | ❌ Out of scope | Adapter is incompressible |
| 3D (finite span) | ⚠️ Different physics | Adds tip vortex, induced drag; needs separate gold |

## Tolerance → citation map

| Observable | Tolerance | Citation key | Type |
|---|---|---|---|
| `lift_coefficient_alpha_eight` | 0.05 | `ladson1988` | Ladson 1988 §3.4 tunnel repeatability ±1.2% at α=8°; 5% covers ±1.2% + numerical → literature-anchored |
| `pressure_coefficient` profile | 0.20 | `dec_v61_058_intake` | DEC-V61-058 §3 PROFILE_GATE: qualitative shape match accommodating 30-50% cell-band attenuation; engineering-derived |
| `lift_slope_dCl_dalpha` | 0.10 | `dec_v61_058_intake` | DEC-V61-058 §3 QUALITATIVE_GATE for linearity over α∈[0°,8°] |
| `drag_coefficient_alpha_zero` | 0.15 | `dec_v61_058_intake` | DEC-V61-058 §3 SAME_RUN_CROSS_CHECK: Cd_0 is small, wall-function discretization noise floor real |
| `y_plus_max` | n/a (advisory) | `dec_v61_058_intake` | PROVISIONAL_ADVISORY band [11, 500] per Codex F5 ruling — NOT HARD-GATED |

Citation coverage: 5/5 = 100% (1 directly literature-anchored to Ladson 1988 §3.4; 4 anchored via DEC-V61-058 intake which itself derives from Ladson + Codex F1-F6 review).

## Geometry sketch

```
                  U_inf →      (rotated by α)
   ──────────────────────────────────────────────────  far-field top (freestream)
                       ╭────────────╮
                      ╱ NACA 0012   ╲   chord = 1.0
                     ╱  α (parameter)  ╲
                    ╰────────────────╯
   ──────────────────────────────────────────────────  far-field bottom

     thin span: y ∈ [-0.001, +0.001] with empty patches
     mesh: x-z plane, 80 cells normal; y locked
```

## Known good results

- DEC-V61-058 Batch B1 landed α-routing (commits 5bbda96 + 032623b + a00ff88, 2026-04-25): reads `angle_of_attack` (canonical) with `alpha_deg` alias fallback; rotates freestream; configures forceCoeffs FO with α-aware lift/drag dirs. Codex round 1 F1 fix (a00ff88) ensures per-call-fresh resolution.
- Stage E live-run smoke verifies α=+8° → Cl > 0 (sign convention end-to-end)
- Cp profile retains PASS_WITH_DEVIATIONS (DEC-EX-A 2026-04-18) magnitude attenuation; shape preserved within 20% qualitative band
- snappyHexMesh rewrite for body-fitted boundary-layer meshing deferred to Tier-1 future work

## References

See [`citations.bib`](citations.bib). Key refs: Ladson 1988 NASA TM-4074 (primary, Cl/Cd/dCl/dα), Abbott & von Doenhoff 1959 (Cp shape qualitative), Gregory & O'Reilly 1970 ARC R&M 3726 (Cp cross-check, Re=2.88e6), DEC-V61-058 intake.

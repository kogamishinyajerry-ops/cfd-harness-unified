# scripts/dogfood/cases — B-arc case pool

Three real-geometry CFD cases consumed by the B-arc multi-model
subagent dogfood. Each case ships a brief (JSON) + a small ASCII STL
fixture + a literature reference value with stated tolerance.

Implements DEC-V61-165 (B.3 case pool).

## Cases

| ID | Geometry | Reference metric | Reference value | Tolerance | Source |
|---|---|---|---|---|---|
| `naca0012` | NACA0012 airfoil, c=1m, span=0.1m | Cl at AoA=4°, Re=1×10⁶ | 0.44 | ±5% rel | Abbott & Doenhoff 1959, Fig 4-5 |
| `backward_step` | L-shape, ER=2, h=1, length 10h | reattachment L/h at Re=5000 | 6.0 | ±10% rel | Kim, Kline, Johnston 1980 |
| `pipe_expansion` | two coaxial cylinders, r1=0.5, r2=1.0 | pressure recovery Kp at sudden ER=2 | 0.5625 | ±5% rel | White, Fluid Mechanics 7e §6.10 |

## Why these three

Charter DEC-V61-162 §rationale rejects re-using LDC / cavity from
N1-N5 fixtures (already exercised; doesn't surface fresh-eyes
friction). The three cases here exercise distinct workflows:

- **NACA0012** — external aerodynamics, curved surface STL,
  pressure-side BC on thin patch, sharp trailing edge meshing
- **backward_step** — internal flow with separation, recirculation
  zone advisor signal, residual interpretation when wake oscillates
- **pipe_expansion** — internal axisymmetric flow, momentum
  integration in post-processing, axisymmetric vs full-3D meshing
  decision

All three have closed-form or well-tabulated reference data; we do
NOT need a CFD reference solver running, only literature numbers.

## Fixture quality caveat

Geometries are **representative not high-fidelity**. The dogfood
tests workbench UX + advisor signal-to-noise, not solver accuracy.
If a persona run produces a wildly off Cl because the airfoil STL
is too coarse, that surfaces as a friction-log entry — exactly the
kind of insight B.4 retro will catalog.

| File | Facets | Size |
|---|---|---|
| `geometry/naca0012.stl` | 240 | ~48 KB |
| `geometry/backward_step.stl` | 20 | ~4 KB |
| `geometry/pipe_expansion.stl` | 128 | ~26 KB |

## Regenerating fixtures

```bash
python -m scripts.dogfood.cases.geometry_generators
```

Generators are pure-stdlib (math only) and deterministic.
`tests/dogfood/test_cases.py::test_geometry_generators_are_deterministic`
asserts byte-identical output across runs.

## Reference value derivations

### NACA0012 Cl

Linear-region slope ≈ 2π per radian; AoA = 4° = 0.0698 rad → Cl ≈
2π × 0.0698 = 0.439. Tabulated Abbott & Doenhoff Fig 4-5 agrees
within 1%. The ±5% relative tolerance absorbs:
- solver-side numerical error (~1-2%)
- mesh resolution sensitivity at the trailing edge (~1-3%)
- turbulence model variance, k-ω-SST vs Spalart-Allmaras (~2-3%)

### BFS reattachment length

Kim et al. 1980 reports L/h between 5.5 and 6.5 across turbulence
treatments at Re=5000 with ER=2. We use 6.0 ±10% to accept the
full reported range.

### Pipe expansion Kp

Closed-form Borda-Carnot for sudden expansion:

```
Kp = (1 - A1/A2)² = (1 - 0.25)² = 0.5625
```

±5% absorbs entry-length effects + turbulent dissipation correction.

## Out of scope

- Mesh files (workbench's mesher consumes the STL)
- Pre-computed solver output
- Reference field data (we only ship scalar metric + tolerance)
- Multi-Re sweeps (one Re per case, charter §case pool)

## References

- DEC-V61-162 · B-arc charter
- DEC-V61-165 · this DEC
- Abbott, I. H., and Doenhoff, A. E., "Theory of Wing Sections", Dover 1959
- Kim, J., Kline, S. J., and Johnston, J. P., "Investigation of a
  Reattaching Turbulent Shear Layer", J. Fluids Eng., Vol. 102, 1980
- White, F. M., "Fluid Mechanics", 7th ed., McGraw-Hill, §6.10

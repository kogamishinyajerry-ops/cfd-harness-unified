# Frozen LIVE probe — P4 V71.A supersonic-wedge oblique shock (rhoCentralFoam)

**This is a REAL solver run** — a live `rhoCentralFoam` (OpenFOAM v2312, ESI)
density-based shock-capturing solve of an M₁=2.0 inviscid 15° wedge. It **LIVE-VALIDATES
the V&V benchmark** for P4 compressible/supersonic, replacing the earlier offline
`_w71a_wedge_probe_SYNTHETIC/` fixture (DEC-V61-232 scaffolding → DEC-V61-233 live run).
It does **NOT** by itself flip runnable-coverage 2 → 3: per Law-1 + DEC-V61-224(b) that
requires the workbench backend (`foam_agent_adapter`/`cfdtrust`) wired to launch the
solver end-to-end (this run was a *direct* container solve), which is a deferred slice.

Unlike the synthetic fixture, the `postProcessing/` artifacts here were *produced
by the solver*, not authored. The gate
(`src.wedge_oblique_shock_gate.gate_wedge_against_gold`) measures the five
oblique-shock QoIs from these artifacts and validates them against the analytical
θ-β-M gold (`knowledge/gold_standards/wedge_oblique_shock.yaml`).

## Measured QoIs (last converged write, t=2.0) vs analytical gold

| Observable | Measured (live) | Gold (θ-β-M) | Error | Tol |
|---|---|---|---|---|
| β (shock angle, deg) | 45.2372 | 45.3436 | −0.23% | 3% |
| M₂ (downstream Mach) | 1.4445 | 1.4457 | −0.08% | 3% |
| p₂/p₁ | 2.1879 | 2.1947 | −0.31% | 3% |
| ρ₂/ρ₁ | 1.7219 | 1.7289 | −0.41% | 3% |
| T₂/T₁ | 1.2692 | 1.2694 | −0.02% | 3% |

Measured freestream Mach = 2.0000 (exactly the gold operating point). All 5
comparator observables + all 5 independent hard gates PASS.

## Normalized gas (why R ≠ 287)

`constant/thermophysicalProperties` uses the wedge15Ma5-tutorial **normalized
gas**: `molWeight=11640.3` ⇒ R = 8314.47/11640.3 = **0.71429**, `Cp=2.5` ⇒
γ = Cp/(Cp−R) = 2.5/1.78571 = **1.4**, so the speed of sound `a = √(γRT) = 1.0`
at T=1 and the Mach number equals the velocity magnitude (`M = |U|`). The
oblique-shock benchmark is **dimensionless** (β, M₂, and the p/ρ/T *ratios* depend
only on M₁, θ, γ — not on R), so the normalized gas is the standard, honest way to
run it. The gate's ideal-gas-consistency check is dimensionless
(`T₂/T₁ == (p₂/p₁)/(ρ₂/ρ₁)`) and never reads `R_specific`. The gold keeps
`R_specific: 287.058` only as descriptive air-context metadata (unused by the gate).

## Geometry / sampling (matches the gold's `case_info.wedge_inputs`)

- Apex at (0,0); wedge surface to (0.3048, 0.08167) ⇒ `atan(0.08167/0.3048)=15.0°`.
- Top boundary raised to **y=0.35** so the β=45.34° shock (y=0.3085 at the outlet
  x=0.3048) EXITS THROUGH THE OUTLET and never touches the top `symmetryPlane` —
  no reflected shock contaminates the wedge-surface post-shock average.
- `freestream` probe = areaAverage over the `inlet` patch (M=2 undisturbed inflow).
- `postShock` probe = areaAverage over the `obstacle` (wedge) patch — the whole
  surface sees the single-shock uniform post-shock state.
- `shockLine` = vertical density sample at **x=0.12**, from **y=0.05** (post-shock)
  to y=0.30 (freestream); `shock_line_origin_y=0.05`. β = atan2(0.05 + dist, 0.12).

## Reproduce from scratch (ESI v2312 Docker, native ARM64)

```bash
# 1. stage the case definition (this dir's case_definition/ holds 0/ constant/ system/)
mkdir -p /tmp/wedge && cp -r case_definition/* /tmp/wedge/

# 2. mesh + solve in a FRESH ESI container (do NOT disturb other running containers)
docker run --rm --entrypoint bash -v /tmp/wedge:/work \
  opencfd/openfoam-default:2312 -c \
  'source /openfoam/profile.rc >/dev/null 2>&1; cd /work && blockMesh && checkMesh && rhoCentralFoam'

# 3. gate the result (offline, no Docker)
python3 -c "from pathlib import Path; \
from src.wedge_oblique_shock_gate import gate_wedge_against_gold; \
r=gate_wedge_against_gold(Path('/tmp/wedge')); print(r.passed); print(r.summary)"
```

Mesh: `blockMesh` → 12000 cells, `checkMesh` → "Mesh OK" (max aspect 1.41,
non-orthogonality max 14.9). Solve: `rhoCentralFoam` explicit, Kurganov flux,
vanLeer reconstruction, adjustTimeStep maxCo=0.5, endTime=2.0 (~6.5 flow-throughs;
ClockTime ≈ 1 min on Apple-silicon). The post-shock probe settles to a
quasi-steady state fluctuating ±0.5% about the analytical mean; the frozen
artifact is the t=2.0 snapshot (within tolerance on every observable).

## What is frozen here

- `postProcessing/freestream/0/surfaceFieldValue.dat` — areaAverage p,rho,T,Ma (inlet)
- `postProcessing/postShock/0/surfaceFieldValue.dat` — areaAverage p,rho,T,Ma (wedge)
- `postProcessing/shockLine/1.999.../line_rho.xy` — 300-pt density profile across shock
- `case_definition/` — `0/ constant/ system/` (NO `polyMesh`; reproducible via blockMesh)
- `logs/` — blockMesh (full), checkMesh (tail), rhoCentralFoam (head+tail)

The `polyMesh` is intentionally NOT frozen (regenerable from `system/blockMeshDict`);
the gate only reads `postProcessing/`.

## Integrity (tamper-evidence)

`SHA256SUMS` pins every frozen file. Verify the artifacts are unmodified with:

```bash
cd reports/showcase_aero/_w71a_wedge_probe && shasum -a 256 -c SHA256SUMS
```

(Added per the DEC-V61-233 red-team auditability nit — a published manifest so a
hand-edit of the `.dat`/`.xy` between freeze and audit is detectable.)

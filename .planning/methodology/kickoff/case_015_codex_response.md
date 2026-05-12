## Deliverable 1 — Engineering brief

- Component picked: Vattenfall T-junction welded pipework; bank ID: no direct slot in `component_bank.md` (Tier 1 benchmark-derived pipework, closest lineage is CHT pipework).
- Reasoning: canonical OECD/NEA thermal-striping benchmark, realistic 90° welded tee, strong industrial flavor for nuclear primary loop / steam pipe fatigue.
- Question: what is the wall-temperature striping amplitude and FFT spectrum downstream, and does the as-installed weld misalignment change the fatigue-relevant RMS pattern?
- Solver choice: `chtMultiRegionFoam` LES (WALE) with wall-modeled LES; chosen because wall thermal capacity matters for fatigue. Fallback `buoyantPimpleFoam` LES is not the primary path.
- Physics: high-Re turbulent junction, CHT to SS304 walls, `y+ ~ 30-100`, `nutUSpaldingWallFunction`, `dt ~ 1e-4 s`.
- Regions: `region_main_fluid`, `region_branch_fluid`, `region_wall_solid` + thermocouple probes `Tx10..Tx100`.
- BC plan: `main_inlet` flow-rate inlet at 19 C, `branch_inlet` flow-rate inlet at 36 C, outlet pressure outlet, fluid-solid interfaces coupled, outer wall adiabatic (`zeroGradient T` / `fixedHeatFlux 0`).
- Expected metrics: wall-T mean + RMS `T'` at `Tx10..Tx100`, FFT at one downstream station, optional thermal-fatigue stress estimate.
- Failure modes: V14/V15 CHT inheritance, case_010 LES averaging window issues, case_011 multi-region bookkeeping, LES+CHT convergence lag, wall-function/interface interpretation, FFT sample-size insufficiency, fluid/solid timestep coordination.
- Effort: 12-15 h, 3 versions likely.

## Deliverable 2 — CAD generation script

```python
#!/usr/bin/env python3
"""case_015_vattenfall_t_junction_thermal_striping · CadQuery generator."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import cadquery as cq

CASE_ID = "case_015_vattenfall_t_junction_thermal_striping"
OUT_DEFAULT = "/Users/Zhuanz/Desktop/case_015_vattenfall_t_junction/inputs/cad_codex_v1.step"
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

# Geometry
D_MAIN_ID_MM = 140.0
D_BRANCH_ID_MM = 100.0
WALL_THICKNESS_MM = 6.0
D_MAIN_OD_MM = D_MAIN_ID_MM + 2.0 * WALL_THICKNESS_MM
D_BRANCH_OD_MM = D_BRANCH_ID_MM + 2.0 * WALL_THICKNESS_MM
L_UPSTREAM_MM = 1000.0
L_DOWNSTREAM_MM = 2000.0
L_BRANCH_MM = 470.0
TEE_X_MM = 220.0
TEE_Y_MM = 285.0
TEE_Z_MM = 325.0
WELD_MISALIGNMENT_UM = 60.0
WELD_MISALIGNMENT_MM = WELD_MISALIGNMENT_UM / 1000.0

# Wall-T probe pads (harness-side labels)
TX_X_MM = [200.0, 400.0, 600.0, 800.0, 1000.0, 1200.0, 1400.0, 1600.0, 1800.0, 2000.0]

PARTS = [
    "region_main_fluid",
    "region_branch_fluid",
    "region_wall_solid",
    "Tx10", "Tx20", "Tx30", "Tx40", "Tx50",
    "Tx60", "Tx70", "Tx80", "Tx90", "Tx100",
]

def check_names() -> None:
    seen = set()
    for n in PARTS:
        if not NAME_RE.match(n):
            raise ValueError(f"invalid name: {n}")
        if n in seen:
            raise ValueError(f"duplicate name: {n}")
        seen.add(n)

def cyl_x(r: float, x0: float, length: float) -> cq.Solid:
    return cq.Workplane("YZ", origin=(x0, 0, 0)).circle(r).extrude(length).val()

def cyl_z(r: float, z0: float, length: float, x_off: float = 0.0) -> cq.Solid:
    return cq.Workplane("XY", origin=(x_off, 0, z0)).circle(r).extrude(length).val()

def box(x: float, y: float, z: float, dx: float, dy: float, dz: float) -> cq.Solid:
    return cq.Workplane("XY", origin=(x, y, z)).box(dx, dy, dz, centered=True).val()

def fuse_many(solids):
    solids = list(solids)
    acc = solids[0]
    for s in solids[1:]:
        acc = acc.fuse(s)
    return acc

def build_main_fluid() -> cq.Solid:
    # Main cold-leg fluid volume.
    upstream = cyl_x(D_MAIN_ID_MM / 2.0, -L_UPSTREAM_MM, L_UPSTREAM_MM)
    downstream = cyl_x(D_MAIN_ID_MM / 2.0, 0.0, L_DOWNSTREAM_MM)
    return upstream.fuse(downstream)

def build_branch_fluid() -> cq.Solid:
    # Branch hot-leg fluid volume; kept as its own named region for bookkeeping.
    return cyl_z(D_BRANCH_ID_MM / 2.0, 0.0, L_BRANCH_MM)

def build_wall_solid() -> cq.Solid:
    # Welded tee collar + pipe shells, fused into one SS304 solid.
    main_up_o = cyl_x(D_MAIN_OD_MM / 2.0, -L_UPSTREAM_MM, L_UPSTREAM_MM)
    main_dn_o = cyl_x(D_MAIN_OD_MM / 2.0, 0.0, L_DOWNSTREAM_MM)
    branch_o = cyl_z(D_BRANCH_OD_MM / 2.0, 0.0, L_BRANCH_MM, x_off=WELD_MISALIGNMENT_MM)
    tee_block = box(0.0, 0.0, 0.0, TEE_X_MM, TEE_Y_MM, TEE_Z_MM)

    main_up_i = cyl_x(D_MAIN_ID_MM / 2.0, -L_UPSTREAM_MM, L_UPSTREAM_MM)
    main_dn_i = cyl_x(D_MAIN_ID_MM / 2.0, 0.0, L_DOWNSTREAM_MM)
    branch_i = cyl_z(D_BRANCH_ID_MM / 2.0, 0.0, L_BRANCH_MM, x_off=WELD_MISALIGNMENT_MM)

    outer = fuse_many([main_up_o, main_dn_o, branch_o, tee_block])
    inner = fuse_many([main_up_i, main_dn_i, branch_i])
    return outer.cut(inner)

def build_probe_pad(name: str, x_mm: float) -> cq.Solid:
    # Small wall-mounted marker for wall-T sampling.
    return box(x_mm, D_MAIN_OD_MM / 2.0 + 1.5, 0.0, 10.0, 4.0, 1.0)

def build() -> cq.Assembly:
    check_names()
    asm = cq.Assembly(name=CASE_ID)
    asm.add(build_main_fluid(), name="region_main_fluid")
    asm.add(build_branch_fluid(), name="region_branch_fluid")
    asm.add(build_wall_solid(), name="region_wall_solid")
    for n, x in zip(["Tx10","Tx20","Tx30","Tx40","Tx50","Tx60","Tx70","Tx80","Tx90","Tx100"], TX_X_MM):
        asm.add(build_probe_pad(n, x), name=n)
    return asm

def normalize_step_header(path: Path) -> None:
    txt = path.read_text(encoding="utf-8", errors="ignore")
    txt = re.sub(r"FILE_NAME\('.*?','.*?',", "FILE_NAME('cad_codex_v1.step','2026-05-08T00:00:00',", txt, count=1)
    path.write_text(txt, encoding="utf-8", newline="\n")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT_DEFAULT)
    ap.add_argument("--check-d5", action="store_true")
    args = ap.parse_args()

    out = Path(args.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)

    asm = build()
    asm.save(str(out), exportType="STEP")
    normalize_step_header(out)

    if args.check_d5:
        print(f"D5 offset = {WELD_MISALIGNMENT_UM:.1f} um")
    print(f"Wrote {out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

## Deliverable 3 — STEP file path

`/Users/Zhuanz/Desktop/case_015_vattenfall_t_junction/inputs/cad_codex_v1.step`

## Deliverable 4 — Parts manifest

```yaml
case_id: case_015_vattenfall_t_junction_thermal_striping
cad_source:
  tier: tier1_reference_derived
  source:
    - https://www.oecd-nea.org/nsd/csni/cfd/benchmarks/Specifications%20of%20T-Junction%20Benchmark%20Exercise.pdf
    - https://www.oecd-nea.org/jcms/pl_19022/report-of-the-oecd/nea-vattenfall-t-junction-benchmark-exercise?details=true
  geometry_basis: "Vattenfall/OECD-NEA T-junction spec; main ID 140 mm, branch ID 100 mm, 90° tee, 6 mm walls"
generation_script: scripts/build_cad.py
step_file: inputs/cad_codex_v1.step
units_in_step: mm

regions:
  - name: region_main_fluid
    role: fluid
    material: water
  - name: region_branch_fluid
    role: fluid
    material: water
  - name: region_wall_solid
    role: solid
    material: SS304

interfaces:
  - between: [region_main_fluid, region_wall_solid]
    thermal_bc: turbulentTemperatureCoupledBaffleMixed
  - between: [region_branch_fluid, region_wall_solid]
    thermal_bc: turbulentTemperatureCoupledBaffleMixed

operating_point:
  main_cold:
    T_C: 19
    mdot_kg_s: 9.0
  branch_hot:
    T_C: 36
    mdot_kg_s: 6.0
  Re_note: "benchmark nominal high-Re turbulent junction; wall-modeled LES"
  wall_material:
    name: SS304
    rho_kg_m3: 7900
    cp_J_kgK: 500
    k_W_mK: 15

les:
  solver: chtMultiRegionFoam
  model: WALE
  wall_function: nutUSpaldingWallFunction
  timestep_s: 1.0e-4
  yplus_target: [30, 100]
  statistics:
    min_flow_throughs: 5
    fft_flow_throughs: 10
    report_dt_s: 0.001
  probe_family: [Tx10, Tx20, Tx30, Tx40, Tx50, Tx60, Tx70, Tx80, Tx90, Tx100]

reference_data:
  compare_metrics:
    - wall_temperature_mean
    - wall_temperature_rms_Tprime
    - wall_temperature_fft
  tolerance:
    mean_K: 2.0
    rms_K: 0.5
  benchmark_note: "official benchmark uses thermocouple transient temperatures; this case adds wall-striping FFT for fatigue use"
```

## Deliverable 5 — Defect manifest

```yaml
case_id: case_015_vattenfall_t_junction_thermal_striping

defects:
  - defect_id: D5
    status: "[QUESTIONABLE 2026-05-08]"
    name: pipe_pipe_weld_misalignment
    offset_um: 60
    location: welded_t_junction
    affected_parts: [region_wall_solid]
    expected_advisor: "A2-v2"
    verification:
      command: "python scripts/build_cad.py --out /Users/Zhuanz/Desktop/case_015_vattenfall_t_junction/inputs/cad_codex_v1.step --check-d5"
      freecad_protocol:
        - "Import.insert STEP in FreeCAD"
        - "Measure the wall-wall offset at the weld toe on the tee joint"
        - "Accept if the offset is within 30-100 um"
    note: "A2 v1 cannot field-validate this offset; A2-v2 draft pending."

reference_data_validity:
  nominal_benchmark: preserved
  defected_variant: partial
```

Sources: [OECD/NEA spec PDF](https://www.oecd-nea.org/nsd/csni/cfd/benchmarks/Specifications%20of%20T-Junction%20Benchmark%20Exercise.pdf), [benchmark report](https://www.oecd-nea.org/jcms/pl_19022/report-of-the-oecd/nea-vattenfall-t-junction-benchmark-exercise?details=true)

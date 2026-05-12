## Deliverable 1 — Engineering brief

### Component picked + bank ID + reasoning

**Case ID:** `case_013_centrifugal_pump_cavitating`

**Component:** Tier-3 reference-derived industrial centrifugal pump, single-stage, single-suction, 6-blade backward-curved impeller in a confined spiral volute.

**Bank/source IDs:**
- Component-bank row: `D1`
- Internal bank ID: `D_PUMP_CENTRIFUGAL_01`
- Geometry tier: `Tier-3` CadQuery reconstruction
- Reference class: Energies 2019 `12(11) 2088`-class industrial cavitation pump geometry and operating scale, with open-paper dimensions baked into script

**Why this fits the solver class:**
- This is the canonical industrial `rotating-machinery` case missing from the current roster: confined pump hydraulics, not open-rotor aerodynamics.
- It extends case_004’s MRF precedent into true industrial pump physics: head curve, efficiency curve, suction-side NPSH sensitivity, and localized cavitation onset.
- It stays within the harness contract: **single fluid region + MRF cellZone**, no `chtMultiRegionFoam`, no multi-region topology.

### Engineering question

What are the pump `H(Q)` and `eta(Q)` curves for this 6-blade backward-curved volute pump at `2900 rpm` with as-installed `D1` and `D7` defects, and where does cavitation onset appear at the lowest documented NPSH operating point?

### Physics signature

- Solver target v1: `simpleFoam` + `MRF`
- Solver target v2: `cavitatingFoam` + `MRF` + Schnerr-Sauer cavitation model
- Fluid region count: `1` (`region_fluid`)
- Rotation model: cylindrical `MRF cellZone` around impeller passage and tip-clearance region
- Turbulence model: `kOmegaSST`
- Working fluid: water at `25 C`
  - `rho = 997 kg/m3`
  - `mu = 8.9e-4 Pa s`
  - `p_v = 3170 Pa abs`
- Operating point:
  - `N = 2900 rpm`
  - `D2 = 250 mm`
  - `D1_eye = 100 mm`
  - `b2 = 20 mm`
  - `z = 6`
  - `Q_BEP = 0.080 m3/s`
  - `H_BEP = 35 m`
  - `eta_BEP_predicted = 0.78`
  - `NPSHr_BEP = 4.5 m`
  - `NPSHr_0.8Q = 3.5 m`
- Characteristic scales:
  - `U2 = 37.96 m/s`
  - Suction-pipe mean velocity at BEP: about `10.19 m/s`
  - Suction-pipe Reynolds number: about `1.14e6`
  - Tip-speed Reynolds number based on `D2`: about `1.06e7`
- Regime:
  - v1: steady incompressible turbulent rotating internal flow
  - v2: two-phase cavitating mixture flow with vapor generation at low-pressure blade-suction-side / tip-leakage structures

### Parts inventory

**Primary CFD region**
- `region_fluid`: fused single fluid body used for meshing and solving

**MRF metadata**
- `mrf_zone_impeller`: cylindrical cellZone reference, axis `z`, `omega = 303.69 rad/s`

**Boundary patches**
- `suction_inlet`
- `discharge_outlet`
- `blade_1` .. `blade_6`
- `blade_tip_1` .. `blade_tip_6`
- `hub_disk`
- `volute_shroud`
- `volute_cutwater`
- `volute_outer_wall`
- `suction_pipe_wall`
- `discharge_nozzle_wall`

### Boundary conditions plan

- `suction_inlet`
  - v1: `totalPressure` / total-head specification derived from the required suction absolute head
  - v2: absolute suction condition derived from target NPSH; hold the `0.8 Q_BEP` operating point while cavitation develops
- `discharge_outlet`
  - v1: `pressureOutlet` / fixed discharge back-pressure, stepped to recover the four `Q/Q_BEP = 0.6, 0.8, 1.0, 1.2` operating points
  - v2: trim `p_outlet` around the matched `0.8 Q_BEP` point to sustain the cavitating operating state without changing the impeller speed
- `blade_1` .. `blade_6`
  - rotating wall treatment inside the MRF zone
- `blade_tip_1` .. `blade_tip_6`
  - rotating wall treatment; `blade_tip_5` carries the enlarged clearance defect
- `hub_disk`
  - rotating wall
- `volute_shroud`
  - stationary `noSlip`
- `volute_cutwater`
  - stationary `noSlip`
- `volute_outer_wall`
  - stationary `noSlip`
- `suction_pipe_wall`
  - stationary `noSlip`
- `discharge_nozzle_wall`
  - stationary `noSlip`

### Expected metrics

- `H(Q)` at `0.6, 0.8, 1.0, 1.2 Q_BEP`
- `eta(Q)` over the same four points
- `NPSHr` at `BEP`
- `NPSHr` at `0.8 Q_BEP`
- Volute/impeller pressure rise and shaft-hydraulic efficiency consistency check
- Tip-leakage structure strength near `blade_5`
- Cavitation map at the `3.5 m` NPSH operating point
  - vapor volume fraction iso-surface
  - suction-side cavitation inception location
  - tip-clearance vapor localization around the defected blade

### Hypothesized failure modes

- **V22 inheritance from case_004:** `A2`-class shared-interface advisor can run cleanly on rotating-machinery topology without field-validating the actual gap magnitude; defect PASS is not the same as engineering confirmation.
- Confined-volute `MRF` may under-damp cutwater interaction at part-load, giving a numerically steady solution with physically biased recirculation near the tongue.
- Cavitation onset is highly sensitive to absolute-pressure bookkeeping; a gauge/absolute mix-up in the `NPSH` inlet specification will create false early or false delayed vapor inception.
- The tip-clearance leakage vortex is a mesh-sensitive feature; inadequate cells across the `0.5 mm / 0.8 mm` gap will smear leakage momentum and under-predict head loss.
- Schnerr-Sauer source terms can destabilize `cavitatingFoam` near the lowest-NPSH point, especially if the first vapor pocket forms at the blade leading edge and re-enters the tip gap.
- Steady frozen-rotor treatment can bias the cutwater-blade interaction phase relative to a transient sliding-mesh truth model; acceptable for v1/v2 harness validation, but a known performance-curve limitation.
- Outlet-pressure stepping may hit the intended back-pressure but miss the intended flow point if the volute/nozzle simplification adds excess hydraulic resistance; monitor `Q` directly and not just `p_outlet`.

### Defect injection summary

- `D1`: one-blade tip-clearance defect on `blade_5`, enlarged from `0.5 mm` nominal to `0.8 mm`
- `D7`: wrong-normal leading edge on `blade_3`, `22 deg` rotation around the local chord axis

These two defects are deliberately placed on different blades so the case keeps a mostly intact bulk pump curve while still giving blade-localized asymmetry for advisor and post-processing exercises.

### Sub-session estimated effort

Estimated sub-session effort: **12-15 h**

---

## Deliverable 2 — CAD generation script
```python
#!/usr/bin/env python3
"""
case_013_centrifugal_pump_cavitating.py

CadQuery generator for case_013:
single-region centrifugal pump fluid domain with impeller, volute,
suction pipe, discharge nozzle, MRF helper body, and named patch
proxies for downstream OpenFOAM patch promotion.

Design intent:
- Tier-3 reference-derived industrial water-treatment / chemical pump
- simpleFoam + MRF baseline
- cavitatingFoam + Schnerr-Sauer extension
- single fluid region only
- D1 tip-clearance defect on blade_5
- D7 wrong-normal leading edge on blade_3
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cadquery as cq


CASE_ID = "case_013_centrifugal_pump_cavitating"
DEFAULT_OUT = "/Users/Zhuanz/Desktop/case_013_centrifugal_pump_cavitating/inputs/cad_codex_v1.step"

# ---------------------------------------------------------------------------
# Fixed industrial design-point constants
# ---------------------------------------------------------------------------

N_RPM = 2900.0
D2_MM = 250.0
D1_MM = 100.0
B2_MM = 20.0
BLADE_COUNT = 6
BETA1_DEG = 22.0
BETA2_DEG = 28.0
Q_BEP_M3_S = 0.080
H_BEP_M = 35.0
ETA_BEP = 0.78
NPSHR_BEP_M = 4.5
NPSHR_08Q_M = 3.5

SUCTION_PIPE_L_MM = 500.0
TIP_CLEARANCE_BASELINE_MM = 0.5
TIP_CLEARANCE_DEFECT_MM = 0.8
D7_ROTATION_DEG = 22.0

RHO_WATER = 997.0
MU_WATER = 8.9e-4
P_VAPOR_PA = 3170.0

VOLUTE_R_OUT_CUTWATER_MM = 1.05 * (D2_MM / 2.0)
VOLUTE_R_OUT_360_MM = 1.50 * (D2_MM / 2.0)
DISCHARGE_NOZZLE_L_MM = 200.0

# ---------------------------------------------------------------------------
# Derived geometry and helper scales
# ---------------------------------------------------------------------------

OMEGA_RAD_S = N_RPM * 2.0 * math.pi / 60.0
R2_MM = D2_MM / 2.0
R1_MM = D1_MM / 2.0
U2_M_S = math.pi * (D2_MM / 1000.0) * N_RPM / 60.0
C_THROAT_M_S = 0.5 * U2_M_S
THROAT_AREA_M2 = Q_BEP_M3_S / C_THROAT_M_S
DISCHARGE_ID_MM = math.sqrt(4.0 * THROAT_AREA_M2 / math.pi) * 1000.0

HUB_RADIUS_MM = 32.0
BLADE_R_IN_MM = R1_MM + 4.0
BLADE_R_OUT_MM = R2_MM - 0.6
VOLUTE_R_IN_MM = R2_MM + 1.5

MRF_RADIUS_MM = R2_MM + 8.0
MRF_Z0_MM = -2.0
MRF_Z1_MM = B2_MM + 2.0

PATCH_NAMES = [
    "suction_inlet",
    "discharge_outlet",
    "hub_disk",
    "volute_shroud",
    "volute_cutwater",
    "volute_outer_wall",
    "suction_pipe_wall",
    "discharge_nozzle_wall",
] + [f"blade_{i}" for i in range(1, BLADE_COUNT + 1)] + [
    f"blade_tip_{i}" for i in range(1, BLADE_COUNT + 1)
]


def fuse_many(solids: list[cq.Solid]) -> cq.Solid:
    if not solids:
        raise ValueError("No solids provided to fuse_many().")
    fused = solids[0]
    for solid in solids[1:]:
        fused = fused.fuse(solid)
    return fused


def polar_xy(radius_mm: float, theta_rad: float) -> tuple[float, float]:
    return radius_mm * math.cos(theta_rad), radius_mm * math.sin(theta_rad)


def lerp(a: float, b: float, s: float) -> float:
    return a + (b - a) * s


def make_cylinder_z(radius_mm: float, z0_mm: float, height_mm: float) -> cq.Solid:
    return (
        cq.Workplane("XY", origin=(0.0, 0.0, z0_mm))
        .circle(radius_mm)
        .extrude(height_mm)
        .val()
    )


def make_cylinder_x(radius_mm: float, x0_mm: float, length_mm: float, zc_mm: float) -> cq.Solid:
    return (
        cq.Workplane("YZ", origin=(x0_mm, 0.0, zc_mm))
        .circle(radius_mm)
        .extrude(length_mm)
        .val()
    )


def blade_centerline(theta0_deg: float, samples: int = 21) -> list[tuple[float, float]]:
    """
    Lightweight reference-derived blade law:
    beta1/beta2 guide the inlet/outlet turning while a smooth
    backward-curved sweep bridges the meridional passage.
    """
    pts: list[tuple[float, float]] = []
    theta0 = math.radians(theta0_deg)
    inlet_turn = math.radians(68.0 - BETA1_DEG)
    outlet_lag = math.radians(38.0 + BETA2_DEG)

    for i in range(samples):
        s = i / (samples - 1)
        r = lerp(BLADE_R_IN_MM, BLADE_R_OUT_MM, s)
        theta = theta0 + inlet_turn * (1.0 - s**0.85) - outlet_lag * (s**1.10)
        pts.append(polar_xy(r, theta))
    return pts


def offset_blade_polygon(centerline: list[tuple[float, float]]) -> tuple[list[tuple[float, float]], tuple[float, float], tuple[float, float]]:
    upp: list[tuple[float, float]] = []
    low: list[tuple[float, float]] = []

    for i, (x, y) in enumerate(centerline):
        if i == 0:
            dx = centerline[i + 1][0] - x
            dy = centerline[i + 1][1] - y
        elif i == len(centerline) - 1:
            dx = x - centerline[i - 1][0]
            dy = y - centerline[i - 1][1]
        else:
            dx = centerline[i + 1][0] - centerline[i - 1][0]
            dy = centerline[i + 1][1] - centerline[i - 1][1]

        mag = math.hypot(dx, dy)
        tx = dx / mag
        ty = dy / mag
        nx = -ty
        ny = tx

        s = i / (len(centerline) - 1)
        thickness = lerp(6.5, 4.2, s)
        upp.append((x + 0.5 * thickness * nx, y + 0.5 * thickness * ny))
        low.append((x - 0.5 * thickness * nx, y - 0.5 * thickness * ny))

    lead_point = centerline[0]
    chord_dir = (
        centerline[2][0] - centerline[0][0],
        centerline[2][1] - centerline[0][1],
    )
    polygon = upp + low[::-1]
    return polygon, lead_point, chord_dir


def blade_tip_clearance_mm(blade_index: int) -> float:
    return TIP_CLEARANCE_DEFECT_MM if blade_index == 5 else TIP_CLEARANCE_BASELINE_MM


def make_blade_solid(blade_index: int) -> tuple[cq.Solid, cq.Solid]:
    theta0_deg = (blade_index - 1) * 360.0 / BLADE_COUNT
    centerline = blade_centerline(theta0_deg)
    polygon, lead_point, chord_dir = offset_blade_polygon(centerline)
    blade_height = B2_MM - blade_tip_clearance_mm(blade_index)

    blade = cq.Workplane("XY").polyline(polygon).close().extrude(blade_height).val()

    # D7: rotate only the blade_3 leading-edge chunk around the local chord axis.
    if blade_index == 3:
        le_x, le_y = lead_point
        cut_box = (
            cq.Workplane("XY")
            .box(20.0, 14.0, blade_height + 4.0, centered=(True, True, False))
            .translate((le_x, le_y, -2.0))
            .val()
        )
        lead_chunk = blade.intersect(cut_box)
        blade_body = blade.cut(cut_box)
        axis_end = (
            le_x + chord_dir[0],
            le_y + chord_dir[1],
            blade_height * 0.50,
        )
        lead_chunk = lead_chunk.rotate(
            (le_x, le_y, blade_height * 0.50),
            axis_end,
            D7_ROTATION_DEG,
        )
        blade = blade_body.fuse(lead_chunk)

    # Patch proxy for blade tip naming in STEP.
    tip_proxy = (
        cq.Workplane("XY", origin=(0.0, 0.0, max(blade_height - 0.05, 0.0)))
        .polyline(polygon)
        .close()
        .extrude(0.05)
        .val()
    )
    return blade, tip_proxy


def make_volute_planform(samples: int = 96) -> list[tuple[float, float]]:
    outer: list[tuple[float, float]] = []
    inner: list[tuple[float, float]] = []

    for i in range(samples + 1):
        theta = 2.0 * math.pi * i / samples
        r_out = lerp(VOLUTE_R_OUT_CUTWATER_MM, VOLUTE_R_OUT_360_MM, theta / (2.0 * math.pi))
        outer.append(polar_xy(r_out, theta))
        inner.append(polar_xy(VOLUTE_R_IN_MM, theta))

    # Pull the first inner point slightly toward the tongue to sharpen the cutwater.
    inner[0] = (VOLUTE_R_IN_MM + 4.0, -5.0)
    return outer + inner[::-1]


def make_volute_solid() -> tuple[cq.Solid, cq.Solid]:
    planform = make_volute_planform()
    volute = cq.Workplane("XY").polyline(planform).close().extrude(B2_MM).val()

    # Simple tangential throat block from cutwater into the discharge nozzle.
    throat_block = (
        cq.Workplane("XY")
        .box(DISCHARGE_ID_MM * 0.85, DISCHARGE_ID_MM, B2_MM, centered=(False, True, False))
        .translate((VOLUTE_R_OUT_CUTWATER_MM - 3.0, 0.0, 0.0))
        .val()
    )

    # Tangential discharge nozzle along +x.
    nozzle = make_cylinder_x(
        radius_mm=0.5 * DISCHARGE_ID_MM,
        x0_mm=VOLUTE_R_OUT_CUTWATER_MM + 0.85 * DISCHARGE_ID_MM - 3.0,
        length_mm=DISCHARGE_NOZZLE_L_MM,
        zc_mm=0.5 * B2_MM,
    )

    volute_full = fuse_many([volute, throat_block, nozzle])

    # Thin helper slab used to preserve the shroud patch as a named STEP body.
    shroud_proxy = (
        cq.Workplane("XY", origin=(0.0, 0.0, B2_MM - 0.05))
        .box(
            2.0 * (VOLUTE_R_OUT_360_MM + DISCHARGE_NOZZLE_L_MM),
            2.0 * VOLUTE_R_OUT_360_MM,
            0.05,
            centered=(True, True, False),
        )
        .val()
    )
    shroud_proxy = volute_full.intersect(shroud_proxy)
    return volute_full, shroud_proxy


def build_positive_fluid() -> tuple[cq.Solid, cq.Solid, cq.Solid, cq.Solid]:
    impeller_chamber = make_cylinder_z(R2_MM, 0.0, B2_MM)
    suction_pipe = make_cylinder_z(R1_MM, -SUCTION_PIPE_L_MM, SUCTION_PIPE_L_MM)
    volute, shroud_proxy = make_volute_solid()
    positive = fuse_many([impeller_chamber, suction_pipe, volute])

    hub = make_cylinder_z(HUB_RADIUS_MM, 0.0, B2_MM)
    return positive, hub, suction_pipe, shroud_proxy


def build_region_fluid() -> tuple[cq.Solid, dict[str, cq.Solid]]:
    positive, hub, suction_pipe, shroud_proxy = build_positive_fluid()
    blades: list[cq.Solid] = []
    patch_proxies: dict[str, cq.Solid] = {
        "hub_disk": hub,
        "suction_pipe_wall": suction_pipe,
        "volute_shroud": shroud_proxy,
    }

    for blade_index in range(1, BLADE_COUNT + 1):
        blade, tip_proxy = make_blade_solid(blade_index)
        blades.append(blade)
        patch_proxies[f"blade_{blade_index}"] = blade
        patch_proxies[f"blade_tip_{blade_index}"] = tip_proxy

    obstacles = fuse_many([hub] + blades)
    region_fluid = positive.cut(obstacles)

    # External opening proxies for named inlet/outlet patch promotion.
    patch_proxies["suction_inlet"] = (
        cq.Workplane("XY", origin=(0.0, 0.0, -SUCTION_PIPE_L_MM))
        .circle(R1_MM)
        .extrude(0.05)
        .val()
    )
    patch_proxies["discharge_outlet"] = make_cylinder_x(
        radius_mm=0.5 * DISCHARGE_ID_MM,
        x0_mm=VOLUTE_R_OUT_CUTWATER_MM + 0.85 * DISCHARGE_ID_MM - 3.0 + DISCHARGE_NOZZLE_L_MM,
        length_mm=0.05,
        zc_mm=0.5 * B2_MM,
    )

    # Coarse helper solids for stationary wall naming.
    patch_proxies["volute_outer_wall"] = make_volute_solid()[0]
    patch_proxies["volute_cutwater"] = (
        cq.Workplane("XY")
        .box(8.0, 16.0, B2_MM, centered=(False, True, False))
        .translate((VOLUTE_R_IN_MM + 2.0, 0.0, 0.0))
        .val()
    )
    patch_proxies["discharge_nozzle_wall"] = make_cylinder_x(
        radius_mm=0.5 * DISCHARGE_ID_MM,
        x0_mm=VOLUTE_R_OUT_CUTWATER_MM + 0.85 * DISCHARGE_ID_MM - 3.0,
        length_mm=DISCHARGE_NOZZLE_L_MM,
        zc_mm=0.5 * B2_MM,
    )

    # MRF helper solid: not a fluid region, just a deterministic cellZone marker.
    patch_proxies["mrf_zone_impeller"] = (
        cq.Workplane("XY", origin=(0.0, 0.0, MRF_Z0_MM))
        .circle(MRF_RADIUS_MM)
        .extrude(MRF_Z1_MM - MRF_Z0_MM)
        .val()
    )
    return region_fluid, patch_proxies


def export_step(out_path: Path, region_fluid: cq.Solid, patch_proxies: dict[str, cq.Solid]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    asm = cq.Assembly(name=CASE_ID)
    asm.add(region_fluid, name="region_fluid")
    asm.add(patch_proxies["mrf_zone_impeller"], name="mrf_zone_impeller")

    for patch_name in PATCH_NAMES:
        asm.add(patch_proxies[patch_name], name=patch_name)

    asm.save(str(out_path))

    metadata = {
        "case_id": CASE_ID,
        "omega_rad_s": round(OMEGA_RAD_S, 2),
        "mrf_axis": [0.0, 0.0, 1.0],
        "patches": PATCH_NAMES,
        "defects": {
            "D1": {
                "blade": "blade_5",
                "tip_clearance_mm": TIP_CLEARANCE_DEFECT_MM,
                "baseline_tip_clearance_mm": TIP_CLEARANCE_BASELINE_MM,
            },
            "D7": {
                "blade": "blade_3",
                "rotation_deg": D7_ROTATION_DEG,
                "feature": "leading_edge_wrong_normal",
            },
        },
    }
    out_path.with_suffix(".patches.json").write_text(json.dumps(metadata, indent=2) + "\n")


def build() -> tuple[cq.Solid, dict[str, cq.Solid]]:
    return build_region_fluid()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=CASE_ID)
    parser.add_argument(
        "--out",
        default=DEFAULT_OUT,
        help="Output STEP path",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_path = Path(args.out)

    region_fluid, patch_proxies = build()
    export_step(out_path, region_fluid, patch_proxies)

    print(f"[ok] wrote {out_path}")
    print(f"[ok] omega = {OMEGA_RAD_S:.2f} rad/s")
    print(f"[ok] discharge ID = {DISCHARGE_ID_MM:.2f} mm")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## Deliverable 3 — STEP file path
`/Users/Zhuanz/Desktop/case_013_centrifugal_pump_cavitating/inputs/cad_codex_v1.step`

## Deliverable 4 — Parts manifest
```yaml
case_id: case_013_centrifugal_pump_cavitating
short_name: centrifugal_pump_cavitating
solver_class: rotating-machinery
numerics_class: incompressible-MRF-cavitating
cad_source: codex-designed-tier3-reference-derived
generation_script: case_013_centrifugal_pump_cavitating.py
step_file: /Users/Zhuanz/Desktop/case_013_centrifugal_pump_cavitating/inputs/cad_codex_v1.step
units_in_step: mm

region:
  name: region_fluid
  type: fluid
  count: 1
  notes: "Single fused fluid region for simpleFoam v1 and cavitatingFoam v2."

mrf_zone:
  name: mrf_zone_impeller
  type: cellZone
  axis: [0.0, 0.0, 1.0]
  omega_rad_s: 303.69
  omega_rpm: 2900
  coverage: "Impeller passage plus tip-clearance region"

patches:
  - name: suction_inlet
    role: inlet
    bc_intent: totalPressure
  - name: discharge_outlet
    role: outlet
    bc_intent: pressureOutlet
  - name: blade_1
    role: rotating_wall
  - name: blade_2
    role: rotating_wall
  - name: blade_3
    role: rotating_wall
  - name: blade_4
    role: rotating_wall
  - name: blade_5
    role: rotating_wall
  - name: blade_6
    role: rotating_wall
  - name: blade_tip_1
    role: rotating_wall
  - name: blade_tip_2
    role: rotating_wall
  - name: blade_tip_3
    role: rotating_wall
  - name: blade_tip_4
    role: rotating_wall
  - name: blade_tip_5
    role: rotating_wall
  - name: blade_tip_6
    role: rotating_wall
  - name: hub_disk
    role: rotating_wall
  - name: volute_shroud
    role: wall
  - name: volute_cutwater
    role: wall
  - name: volute_outer_wall
    role: wall
  - name: suction_pipe_wall
    role: wall
  - name: discharge_nozzle_wall
    role: wall

thermophysics_v1:
  solver: simpleFoam
  phase_model: single_phase_incompressible
  fluid: water
  temperature_C: 25
  density_kg_m3: 997
  dynamic_viscosity_Pa_s: 8.9e-4
  notes: "Baseline H(Q) and eta(Q) head-curve sweep with MRF."

thermophysics_v2:
  solver: cavitatingFoam
  phase_model: water_water_vapor_mixture
  cavitation_model: SchnerrSauer
  liquid_phase:
    name: water
    density_kg_m3: 997
    dynamic_viscosity_Pa_s: 8.9e-4
  vapor_phase:
    name: water_vapor
    vapor_pressure_Pa_abs: 3170
  schnerr_sauer:
    n_nuclei_m3: 1.0e13
    d_nucleus_m: 1.0e-5
  notes: "Lowest-NPSH operating point cavitation map at 0.8 Q_BEP intent."

pump_operating_point:
  N_rpm: 2900
  Q_BEP_m3_s: 0.080
  H_BEP_m: 35
  eta_BEP: 0.78
  NPSHr_BEP_m: 4.5
  NPSHr_at_0p8Q_m: 3.5
  D2_mm: 250
  D1_eye_mm: 100
  b2_mm: 20
  z_blades: 6
  beta1_deg: 22
  beta2_deg: 28
  volute:
    type: archimedean_spiral
    cutwater_theta_deg: 0
    outer_radius_at_cutwater_mm: 131.25
    outer_radius_at_360_mm: 187.5
    discharge_nozzle_length_mm: 200
    throat_design_rule: "c_throat ~= 0.5 * U2"
  suction_pipe:
    inner_diameter_mm: 100
    length_mm: 500
  tip_clearance_baseline_mm: 0.5

turbulence_model:
  name: kOmegaSST
  rationale: "Industry-standard centrifugal turbomachinery RANS closure; preferred over k-epsilon for adverse pressure gradient, separation onset, and blade suction-side loading fidelity."

reference:
  class: industrial water-treatment centrifugal pump
  source_note: "Tier-3 reference-derived per Energies 2019 12(11) 2088-class geometry and operating scale; literature dimensions are baked into the script per V25-style reproducibility discipline."

patch_naming_check:
  - "all names match ^[A-Za-z][A-Za-z0-9_]*$"
  - "no duplicate names"
  - "no spaces or hyphens"

determinism:
  expectation: "Byte-identical regeneration under the same CadQuery/OCP build."
  regen_check_command: "python case_013_centrifugal_pump_cavitating.py --out /Users/Zhuanz/Desktop/case_013_centrifugal_pump_cavitating/inputs/cad_codex_v1.step && shasum -a 256 /Users/Zhuanz/Desktop/case_013_centrifugal_pump_cavitating/inputs/cad_codex_v1.step"
```

## Deliverable 5 — Defect manifest
```yaml
case_id: case_013_centrifugal_pump_cavitating

defects:
  - defect_id: D1
    short_name: tip_clearance_gap
    target_patch: blade_tip_5
    host_blade: blade_5
    nominal_tip_clearance_mm: 0.5
    realized_tip_clearance_mm: 0.8
    delta_mm: 0.3
    description: "One blade tip is shortened to create +0.3 mm extra clearance relative to the nominal uniform baseline."
    advisor: "A2-v2 [QUESTIONABLE 2026-05-08]"
    advisor_status_note: "A2 v1 cannot field-validate actual gap distance per V25; A2-v2 draft pending."
    verification:
      method: "FreeCAD distToShape"
      command: "Measure minimum distance between blade_5_tip and volute_shroud at 4 documented angular positions."
      expected_result: "0.8 mm on the defected blade_5 position; 0.5 mm on the other 5 blade tips."

  - defect_id: D7
    short_name: wrong_normal_leading_edge
    target_patch: blade_3
    host_blade: blade_3
    rotation_deg: 22
    rotation_axis: "local chord axis at leading edge"
    description: "Leading-edge chunk on blade_3 is rotated by 22 degrees around the local chord axis to create a wrong-normal surface orientation defect."
    advisor: "NONE"
    advisor_status_note: "No LANDED advisor for face-orientation defects; A4 remains only a candidate post-case_012 retro."
    verification:
      method: "FreeCAD Face.normalAt() plus dot-product comparison"
      command: "Sample blade_3 leading-edge face normal and compare against the intended undeformed leading-edge normal."
      expected_result: "Measured local normal is rotated by about 22 degrees relative to the baseline blade family."

placement_policy_statement: "Both defects are placed on edge blades (3, 5) outside the bulk-impeller H(Q) comparison zone; comparison uses the average of all 6 blades for H prediction. Defects are intended to produce minor (<2%) H deviation but visible blade-by-blade variance for advisor exercise."

reference_data_validity: "H(Q) +/- 10% at BEP, NPSHr +/- 15%, eta +/- 5% per industrial pump correlation tolerance band."
```

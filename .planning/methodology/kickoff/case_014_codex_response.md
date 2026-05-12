## Deliverable 1 — Engineering brief

### Component picked + bank ID
**Case ID:** `case_014_nasa_cc3_compressor_stage`

**Component:** NASA CC3 centrifugal compressor stage, modeled as a single periodic passage with impeller, vaneless space, vaned diffuser, and outlet collector.

**Bank ID:** `D1` rotating-machinery base, extended as the Phase 2 compressor variant.

**Why this fits:** it combines the project’s prior MRF machinery work with compressible-RANS turbomachinery physics. The NASA CC3 archive gives real industrial compressor performance data, while the vaned diffuser/collector extension satisfies the project’s industrial-stage constraint.

**Primary reference:** NASA/TM-2013-216566 / AIAA 2013-3631, *Computational Study of the CC3 Impeller and Vaneless Diffuser Experiment*  
Key published CC3 parameters used here:
- 15 main blades + 15 splitter blades
- design corrected speed: 21,789 rpm
- design inlet corrected flow: 4.54 kg/s
- impeller exit tip speed: 492 m/s
- trailing-edge radius: `R_TE = 215.5 mm`
- inlet blade height: 64 mm
- exit blade height: 17 mm
- measured clearances at design speed: 0.1524 / 0.6096 / 0.2032 mm along chord

### Engineering question
What is the PR-η-surge-choke characteristic at design speed for a CC3 compressor stage with as-installed tip-clearance growth on one blade and a locally thinned leading edge on one blade?

### Physics signature
- Solver: `rhoSimpleFoam + MRF`
- Turbulence: `k-omega-SST`
- Thermophysics: air, ideal gas + Sutherland
- Regime: compressible turbomachinery, transonic relative inlet pockets, strong tip leakage, diffuser loading
- `Re_blade ~ 1e6`
- `U_tip ~ 492 m/s`
- local relative `M_tip` can sit near `0.8-1.0+` at the loaded leading edge

### Parts inventory
- `region_fluid`
- `mrf_zone`
- `inlet_plenum`
- `impeller_hub`
- `impeller_shroud`
- `blade_main_0`
- `blade_main_0_tip`
- `blade_splitter_0`
- `blade_splitter_0_tip`
- `vaneless_space`
- `diffuser_vane_0`
- `diffuser_vane_0_tip`
- `outlet_collector`
- `periodic_lower`
- `periodic_upper`

### BC plan
- `inlet_plenum`: `totalPressure` + `totalTemperature`
- `outlet_collector`: `pressureOutlet` at v1 design back-pressure; swept for v2 characteristic curve
- `impeller_*`: moving-wall treatment in the MRF zone
- `hub/shroud/diffuser`: noSlip stationary walls
- `periodic_lower` / `periodic_upper`: `cyclicAMI` with rotational transform
- `mrf_zone`: axis `z`, steady frozen rotor, design omega from 21,789 rpm

### Expected metrics
- `PR(mdot)`
- `eta(mdot)`
- surge margin
- choke `mdot`
- tip-leakage visualization at design
- supersonic pocket map if present
- diffuser incidence / exit swirl
- residual and continuity stability

### Hypothesized failure modes
- V22 inheritance: MRF rotation-pattern mistakes can look converged while physically wrong
- V18 inheritance: compressible mass-flow asymmetry from case_005-style BC handling
- NEW: tip-leakage capture grid sensitivity
- NEW: surge prediction sensitivity to back-pressure ramp rate
- NEW: periodic face matching tolerance
- NEW: total-total vs total-static reference-state ambiguity
- NEW: choke-boundary mass-flow numerical limit

### Defect injection summary
- `D1` `[QUESTIONABLE 2026-05-08]`: enlarge tip clearance on one blade by `+0.30 mm` beyond the nominal `0.30 mm` baseline
- `D8` `[VALIDATED]`: thin the leading edge of one blade to `0.70 mm`

Reference-data validity: `partial`  
The clean NASA CC3 data remain the baseline, but the defected passage is intentionally an as-installed variant.

### Sub-session estimated effort
`14-18h`, typically 3 versions:
- v1 geometry / naming / periodic setup
- v2 mesh + MRF + compressible BC tuning
- v3 characteristic-curve sweep and report

## Deliverable 2 — CAD generation script

```python
#!/usr/bin/env python3
"""case_014_nasa_cc3_compressor_stage · CAD generator.

NASA CC3 lineage:
- NASA/TM-2013-216566 / AIAA 2013-3631
- CC3 impeller data: 15 main blades + 15 splitter blades, 21,789 rpm,
  R_TE = 215.5 mm, design inlet corrected flow 4.54 kg/s.

This script is deterministic and self-contained. It builds a periodic
single-passage compressor scaffold and preserves named bodies in STEP.
"""

from __future__ import annotations

import argparse
import math
import os
import re
from pathlib import Path

import cadquery as cq


CASE_ID = "case_014_nasa_cc3_compressor_stage"
DEFAULT_OUT = "/Users/Zhuanz/Desktop/case_014_nasa_cc3_compressor_stage/inputs/cad_codex_v1.step"
PATCH_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

# --- NASA CC3 reference geometry / operating point ---
N_MAIN_BLADES = 15
N_SPLITTER_BLADES = 15
PERIODIC_ANGLE_DEG = 360.0 / (N_MAIN_BLADES + N_SPLITTER_BLADES)  # 12 deg sector
D2_MM = 215.5  # project shorthand uses the CC3 trailing-edge radius scale
R_TE_MM = 215.5
TIP_SPEED_MPS = 492.0
N_RPM = 21789.0
OMEGA_RAD_PER_S = N_RPM * 2.0 * math.pi / 60.0

INLET_BLADE_HEIGHT_MM = 64.0
EXIT_BLADE_HEIGHT_MM = 17.0
TIP_CLEARANCE_BASELINE_MM = 0.30
D1_TIP_GAP_OFFSET_MM = 0.30
D8_LE_THICKNESS_MM = 0.70

BLADE_ANGLE_INLET_MAIN_DEG = 18.0
BLADE_ANGLE_OUTLET_DEG = -50.0
BLADE_ANGLE_INLET_SPLITTER_DEG = 10.0
SPLITTER_POSITION_FRAC = 0.55

VANE_COUNT = 20
DIFFUSER_ANGLE_DEG = 18.0

INLET_PLENUM_LENGTH_MM = 500.0
OUTLET_COLLECTOR_LENGTH_MM = 360.0
VANELESS_SPACE_LENGTH_MM = 80.0

HUB_RADIUS_MM = 42.0
SHROUD_RADIUS_MM = R_TE_MM + TIP_CLEARANCE_BASELINE_MM
MRF_RADIUS_MM = R_TE_MM + 12.0
INLET_RADIUS_MM = 70.0
COLLECTOR_RADIUS_MM = 165.0
DIFFUSER_INLET_RADIUS_MM = R_TE_MM + 26.0
DIFFUSER_OUTLET_RADIUS_MM = R_TE_MM + 70.0

IMPeller_SPAN_MM = INLET_BLADE_HEIGHT_MM

PART_NAMES = [
    "region_fluid",
    "mrf_zone",
    "inlet_plenum",
    "impeller_hub",
    "impeller_shroud",
    "blade_main_0",
    "blade_main_0_tip",
    "blade_splitter_0",
    "blade_splitter_0_tip",
    "vaneless_space",
    "diffuser_vane_0",
    "diffuser_vane_0_tip",
    "outlet_collector",
    "periodic_lower",
    "periodic_upper",
]


def validate_names() -> None:
    seen = set()
    for name in PART_NAMES:
        if not PATCH_NAME_RE.match(name):
            raise ValueError(f"Invalid OpenFOAM name: {name}")
        if name in seen:
            raise ValueError(f"Duplicate name: {name}")
        seen.add(name)


def sector_points(r_in: float, r_out: float, angle_deg: float, n: int = 24) -> list[tuple[float, float]]:
    """2D annular-sector polygon used for the periodic passage envelope."""
    half = math.radians(angle_deg / 2.0)
    pts: list[tuple[float, float]] = []
    for i in range(n + 1):
        a = -half + 2.0 * half * i / n
        pts.append((r_out * math.cos(a), r_out * math.sin(a)))
    for i in range(n + 1):
        a = half - 2.0 * half * i / n
        pts.append((r_in * math.cos(a), r_in * math.sin(a)))
    return pts


def make_sector_body(r_in: float, r_out: float, z0: float, length: float, angle_deg: float) -> cq.Solid:
    # Core single-passage envelope for the periodic sector.
    pts = sector_points(r_in, r_out, angle_deg)
    return cq.Workplane("XY", origin=(0.0, 0.0, z0)).polyline(pts).close().extrude(length).val()


def make_cylinder(radius_mm: float, z0_mm: float, length_mm: float) -> cq.Solid:
    return cq.Workplane("XY", origin=(0.0, 0.0, z0_mm)).circle(radius_mm).extrude(length_mm).val()


def make_blade(
    radius_root_mm: float,
    radius_tip_mm: float,
    z_root_mm: float,
    z_tip_mm: float,
    theta_root_deg: float,
    theta_tip_deg: float,
    chord_root_mm: float,
    chord_tip_mm: float,
    thick_root_mm: float,
    thick_tip_mm: float,
    tip_gap_mm: float = 0.0,
) -> cq.Solid:
    # Two-section loft keeps the blade deterministic and lets D1/D8 act locally.
    root = (
        cq.Workplane("XY", origin=(radius_root_mm, 0.0, z_root_mm))
        .transformed(rotate=(0.0, 0.0, theta_root_deg))
        .rect(chord_root_mm, thick_root_mm)
        .wire()
        .val()
    )
    tip = (
        cq.Workplane("XY", origin=(radius_tip_mm - tip_gap_mm, 0.0, z_tip_mm))
        .transformed(rotate=(0.0, 0.0, theta_tip_deg))
        .rect(chord_tip_mm, thick_tip_mm)
        .wire()
        .val()
    )
    return cq.Workplane().add(root).add(tip).loft(combine=True, ruled=False).val()


def make_tip_cap(radius_mm: float, z_mm: float, chord_mm: float, thick_mm: float, theta_deg: float) -> cq.Solid:
    # Tiny separate tip body so the sub-session can tag the tip-wall patch explicitly.
    return (
        cq.Workplane("XY", origin=(radius_mm, 0.0, z_mm))
        .transformed(rotate=(0.0, 0.0, theta_deg))
        .box(chord_mm, thick_mm, 2.0, centered=(True, True, False))
        .val()
    )


def make_periodic_marker(theta_deg: float, radius_mm: float, length_mm: float, z0_mm: float) -> cq.Solid:
    # Thin plate on the periodic transform face; used as a naming anchor.
    return (
        cq.Workplane("XY", origin=(0.0, 0.0, z0_mm))
        .box(0.6, radius_mm, length_mm, centered=(True, True, False))
        .rotate((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), theta_deg)
        .val()
    )


def build() -> cq.Assembly:
    asm = cq.Assembly()

    region_fluid = make_sector_body(HUB_RADIUS_MM, COLLECTOR_RADIUS_MM, 0.0, OUTLET_COLLECTOR_LENGTH_MM, PERIODIC_ANGLE_DEG)
    mrf_zone = make_cylinder(MRF_RADIUS_MM, 0.0, IMPeller_SPAN_MM)

    inlet_plenum = make_cylinder(INLET_RADIUS_MM, -INLET_PLENUM_LENGTH_MM, INLET_PLENUM_LENGTH_MM)
    outlet_collector = make_cylinder(COLLECTOR_RADIUS_MM, IMPeller_SPAN_MM + VANELESS_SPACE_LENGTH_MM, OUTLET_COLLECTOR_LENGTH_MM)
    vaneless_space = make_sector_body(R_TE_MM + TIP_CLEARANCE_BASELINE_MM, DIFFUSER_INLET_RADIUS_MM, IMPeller_SPAN_MM, VANELESS_SPACE_LENGTH_MM, PERIODIC_ANGLE_DEG)

    impeller_hub = make_cylinder(HUB_RADIUS_MM, 0.0, IMPeller_SPAN_MM)
    impeller_shroud = make_cylinder(SHROUD_RADIUS_MM, 0.0, IMPeller_SPAN_MM)

    # Main blade: baseline tip clearance plus the D1 extra gap on the single defected passage.
    blade_main_0 = make_blade(
        radius_root_mm=78.0,
        radius_tip_mm=R_TE_MM,
        z_root_mm=0.0,
        z_tip_mm=IMPeller_SPAN_MM,
        theta_root_deg=BLADE_ANGLE_INLET_MAIN_DEG,
        theta_tip_deg=BLADE_ANGLE_OUTLET_DEG,
        chord_root_mm=18.0,
        chord_tip_mm=12.0,
        thick_root_mm=1.20,
        thick_tip_mm=1.00,
        tip_gap_mm=TIP_CLEARANCE_BASELINE_MM + D1_TIP_GAP_OFFSET_MM,
    )
    blade_main_0_tip = make_tip_cap(R_TE_MM - (TIP_CLEARANCE_BASELINE_MM + D1_TIP_GAP_OFFSET_MM), IMPeller_SPAN_MM - 1.0, 8.0, 0.60, BLADE_ANGLE_OUTLET_DEG)

    # Splitter blade: the D8 thinning is applied to the leading edge thickness.
    splitter_root = 78.0 + SPLITTER_POSITION_FRAC * (R_TE_MM - 78.0)
    blade_splitter_0 = make_blade(
        radius_root_mm=splitter_root,
        radius_tip_mm=R_TE_MM - 2.0,
        z_root_mm=10.0,
        z_tip_mm=IMPeller_SPAN_MM,
        theta_root_deg=BLADE_ANGLE_INLET_SPLITTER_DEG,
        theta_tip_deg=BLADE_ANGLE_OUTLET_DEG,
        chord_root_mm=14.0,
        chord_tip_mm=10.0,
        thick_root_mm=D8_LE_THICKNESS_MM,
        thick_tip_mm=D8_LE_THICKNESS_MM * 0.85,
        tip_gap_mm=TIP_CLEARANCE_BASELINE_MM,
    )
    blade_splitter_0_tip = make_tip_cap(R_TE_MM - TIP_CLEARANCE_BASELINE_MM, IMPeller_SPAN_MM - 1.0, 7.0, 0.60, BLADE_ANGLE_OUTLET_DEG)

    diffuser_vane_0 = make_blade(
        radius_root_mm=DIFFUSER_INLET_RADIUS_MM,
        radius_tip_mm=DIFFUSER_OUTLET_RADIUS_MM,
        z_root_mm=IMPeller_SPAN_MM + VANELESS_SPACE_LENGTH_MM,
        z_tip_mm=IMPeller_SPAN_MM + VANELESS_SPACE_LENGTH_MM + 42.0,
        theta_root_deg=DIFFUSER_ANGLE_DEG,
        theta_tip_deg=DIFFUSER_ANGLE_DEG + 4.0,
        chord_root_mm=22.0,
        chord_tip_mm=18.0,
        thick_root_mm=1.20,
        thick_tip_mm=1.00,
    )
    diffuser_vane_0_tip = make_tip_cap(DIFFUSER_OUTLET_RADIUS_MM, IMPeller_SPAN_MM + VANELESS_SPACE_LENGTH_MM + 41.0, 8.0, 0.60, DIFFUSER_ANGLE_DEG)

    periodic_lower = make_periodic_marker(-PERIODIC_ANGLE_DEG / 2.0, COLLECTOR_RADIUS_MM, IMPeller_SPAN_MM + OUTLET_COLLECTOR_LENGTH_MM, 0.0)
    periodic_upper = make_periodic_marker(+PERIODIC_ANGLE_DEG / 2.0, COLLECTOR_RADIUS_MM, IMPeller_SPAN_MM + OUTLET_COLLECTOR_LENGTH_MM, 0.0)

    for name, solid in [
        ("region_fluid", region_fluid),
        ("mrf_zone", mrf_zone),
        ("inlet_plenum", inlet_plenum),
        ("impeller_hub", impeller_hub),
        ("impeller_shroud", impeller_shroud),
        ("blade_main_0", blade_main_0),
        ("blade_main_0_tip", blade_main_0_tip),
        ("blade_splitter_0", blade_splitter_0),
        ("blade_splitter_0_tip", blade_splitter_0_tip),
        ("vaneless_space", vaneless_space),
        ("diffuser_vane_0", diffuser_vane_0),
        ("diffuser_vane_0_tip", diffuser_vane_0_tip),
        ("outlet_collector", outlet_collector),
        ("periodic_lower", periodic_lower),
        ("periodic_upper", periodic_upper),
    ]:
        asm.add(solid, name=name)

    return asm


def main() -> int:
    validate_names()

    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--source", default=os.environ.get("CASE014_SOURCE_ARCHIVE", ""))
    args = parser.parse_args()

    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    asm = build()
    asm.save(str(out_path), exportType="STEP")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## Deliverable 3 — STEP file path

`/Users/Zhuanz/Desktop/case_014_nasa_cc3_compressor_stage/inputs/cad_codex_v1.step`

## Deliverable 4 — Parts manifest

```yaml
case_id: case_014_nasa_cc3_compressor_stage
cad_source: "NASA CC3 Tier-1 public archive / NASA TM-2013-216566 lineage"
generation_script: "scripts/build_cad.py"
step_file: "inputs/cad_codex_v1.step"
units_in_step: mm

region: region_fluid

mrf_zone:
  name: mrf_zone
  role: cellZone
  axis_xyz: [0, 0, 1]
  omega_rpm: 21789
  omega_rad_per_s: 2282.9

periodic:
  lower: periodic_lower
  upper: periodic_upper
  rotation_axis_xyz: [0, 0, 1]
  periodic_angle_deg: 12.0
  bc_type: cyclicAMI

thermophysics:
  fluid: air
  equation_of_state: ideal_gas
  viscosity_model: sutherland
  gamma: 1.4
  r_gas_j_per_kg_k: 287.05

compressor_operating_point:
  N_rpm: 21789
  mdot_design_kg_s: 4.54
  pr_design: 4.0
  eta_target: 0.86
  surge_margin_pct: 12.0
  choke_mdot_kg_s: 5.05
  T0_inlet_k: 293.15
  P0_inlet_pa: 101325
  tip_speed_mps: 492.0
  r_te_mm: 215.5

reference:
  primary:
    citation: "NASA/TM-2013-216566 / AIAA 2013-3631, Computational Study of the CC3 Impeller and Vaneless Diffuser Experiment"
    source: "NASA NTRS"
  secondary:
    citation: "NASA/CR-2014-218114/REV1 CC3 compressor geometry summary"
    source: "NASA NTRS"
  note: "Primary performance data come from the CC3 TM; the downstream vaned diffuser / collector is an industrial extension required by the case constraint."

parts:
  - name: inlet_plenum
    role: inlet
    bc_type:
      U: pressureInletOutletVelocity
      p: totalPressure
      T: totalTemperature
    values:
      p0_pa: 101325
      T0_k: 293.15

  - name: impeller_hub
    role: wall
    bc_type:
      U: movingWallVelocity
      p: zeroGradient
      T: zeroGradient

  - name: impeller_shroud
    role: wall
    bc_type:
      U: noSlip
      p: zeroGradient
      T: zeroGradient

  - name: blade_main_0
    role: rotating_wall
    bc_type:
      U: movingWallVelocity
      p: zeroGradient
      T: zeroGradient
    notes: "Representative main blade passage; D1 applied here."

  - name: blade_main_0_tip
    role: tip_wall
    bc_type:
      U: movingWallVelocity
      p: zeroGradient
      T: zeroGradient

  - name: blade_splitter_0
    role: rotating_wall
    bc_type:
      U: movingWallVelocity
      p: zeroGradient
      T: zeroGradient
    notes: "Representative splitter blade passage; D8 applied here."

  - name: blade_splitter_0_tip
    role: tip_wall
    bc_type:
      U: movingWallVelocity
      p: zeroGradient
      T: zeroGradient

  - name: vaneless_space
    role: transition_volume
    bc_type:
      U: noSlip
      p: zeroGradient
      T: zeroGradient

  - name: diffuser_vane_0
    role: stationary_wall
    bc_type:
      U: noSlip
      p: zeroGradient
      T: zeroGradient

  - name: diffuser_vane_0_tip
    role: tip_wall
    bc_type:
      U: noSlip
      p: zeroGradient
      T: zeroGradient

  - name: outlet_collector
    role: outlet
    bc_type:
      U: pressureInletOutletVelocity
      p: fixedValue
      T: inletOutlet
    values:
      p_back_pa: 405000

  - name: periodic_lower
    role: periodic
    bc_type:
      type: cyclicAMI
      transform: rotational

  - name: periodic_upper
    role: periodic
    bc_type:
      type: cyclicAMI
      transform: rotational

patch_naming_check:
  all_names_match_regex: "^[A-Za-z][A-Za-z0-9_]*$"
  no_duplicates: true
  periodic_pairing: "periodic_lower <-> periodic_upper"
```

## Deliverable 5 — Defect manifest

```yaml
case_id: case_014_nasa_cc3_compressor_stage
reference_data_validity: partial

defects:
  - id: D1
    status: QUESTIONABLE
    name: tip_clearance_growth_on_one_blade
    target: blade_main_0
    nominal_tip_clearance_mm: 0.30
    added_gap_mm: 0.30
    defect_tip_clearance_mm: 0.60
    expected_advisor_to_catch: "A2-v2 gap-aware interface advisor (draft pending)"
    notes:
      - "[QUESTIONABLE 2026-05-08] A2-v1 cannot field-validate actual gap magnitude."
      - "The defect is localized to one periodic passage copy and should be treated as as-installed wear."

  - id: D8
    status: VALIDATED
    name: thin_leading_edge_on_one_blade
    target: blade_splitter_0
    nominal_le_thickness_mm: 1.20
    defect_le_thickness_mm: 0.70
    expected_advisor_to_catch: thin_wall_advisor
    notes:
      - "LANDED, 6-of-6 [VALIDATED]."
      - "This extends the thin-wall arc into turbomachinery."

defect_summary:
  - "D1 intentionally increases tip leakage on one blade."
  - "D8 intentionally thins one blade leading edge for advisor coverage."
```


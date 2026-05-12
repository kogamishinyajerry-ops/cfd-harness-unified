## Deliverable 1 — Engineering brief

- Component: `A1` original pin-fin heatsink meaning, not the compact HX reinterpretation from case_011.
- Bank ID: `A1`.
- Reasoning: this is the canonical electronics cooling pin-fin form factor, with a chip-scale CHT stack that matches CPU/GPU/IGBT thermal design work.
- CAD source: Tier 3 parametric CadQuery. I did not select a public TIMA/IBM STEP here because the geometry is generic and the defect placement needs exact control.
- Region count choice: `4` regions.
- Why 4: `region_air + region_chip_die + region_tim + region_heatsink`. The TIM layer is realistic and forces the solid-solid conjugate interface that distinguishes this from 002b.

- Engineering question: does a 50×50×5 mm pin-fin heatsink keep a 10×10×0.7 mm chip below 85°C at 50-100 W with as-installed D8 thin-pin and D9 faceted-pin defects?

- Physics signature: `chtMultiRegionFoam` steady, `Pr ≈ 0.71`, `Re_pin ≈ 300-400` for the chosen air speed and pin size, laminar / low-Re transitional, conjugate Si-TIM-Al-air coupling.

- Parts inventory:
  - `region_air`: forced-convection fluid over the pin array
  - `region_chip_die`: silicon heat source
  - `region_tim`: thin thermal interface layer
  - `region_heatsink`: aluminum 6063 base + pin array fused as one solid

- BC plan:
  - `air_inlet`: `flowRateInletVelocity`, `T = 298.15 K`
  - `air_outlet`: `pressureOutlet`
  - `chip_bottom`: `fixedHeatFlux = P_chip / area`
  - conjugate interfaces: `turbulentTemperatureCoupledBaffleMixed`
  - outer solid faces: `zeroGradient T`

- Expected metrics:
  - `T_chip` junction temperature, target `< 85°C`
  - `R_theta,j-a` from TIMA / IBM pin-fin correlation, CFD within `±15%`
  - pin-array `Δp`
  - local `h` on 4 representative pins: D8 corner thin pins, D9 faceted pins, center pin, edge pin
  - heatsink-base heat-flux distribution

- Hypothesized failure modes:
  - V14 / V15 inheritance from 002b CHT
  - multi-region bookkeeping issues from case_011 if sedimented
  - low-Re pin-array regime choice: laminar vs transitional
  - solid-solid conjugate BC handling across chip die / TIM / heatsink
  - D9 faceted-pin local `h` deviation vs smooth pin
  - D8 thin-pin thermal short-circuit effect on `R_theta`
  - chip-scale meshing sensitivity vs the larger APU-bay cases

- Defect injection summary:
  - D8: 4 corner pins thinned to `0.5 mm`
  - D9: 4 inboard corner-adjacent pins faceted to `10` sides
  - both stay outside the central chip footprint so the defect effect is thermal / convective, not source-placement noise

- Sub-session estimated effort: `8-10 h`

## Deliverable 2 — CAD generation script

```python
#!/usr/bin/env python3
"""
case_017_pin_fin_electronic_heatsink.py

CadQuery generator for case_017:
chip-scale pin-fin electronic heatsink with optional TIM layer and
intentional D8 / D9 defects.

Regions:
- region_air
- region_chip_die
- region_tim
- region_heatsink
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import cadquery as cq

# -----------------------------
# Parametric design constants
# -----------------------------

CASE_ID = "case_017_pin_fin_electronic_heatsink"

HEATSINK_BASE_MM = (50.0, 50.0, 5.0)
CHIP_DIE_MM = (10.0, 10.0, 0.7)
TIM_THICKNESS_MM = 0.08

PIN_GRID = (10, 10)
PIN_DIAMETER_MM = 1.5
PIN_HEIGHT_MM = 12.0
PIN_PITCH_MM = 3.5

AIR_BOX_MM = (70.0, 70.0, 20.0)

D8_THIN_PIN_DIAMETER_MM = 0.5
D8_THIN_PIN_INDICES = {0, 9, 90, 99}

D9_FACETED_PIN_FACETS = 10
D9_FACETED_PIN_INDICES = {1, 8, 91, 98}

BASE_ORIGIN = (10.0, 10.0, 0.0)
AIR_ORIGIN = (0.0, 0.0, 0.0)


def box(origin_x: float, origin_y: float, origin_z: float,
        size_x: float, size_y: float, size_z: float) -> cq.Solid:
    return cq.Solid.makeBox(size_x, size_y, size_z, cq.Vector(origin_x, origin_y, origin_z))


def centered_box(center_x: float, center_y: float, origin_z: float,
                 size_x: float, size_y: float, size_z: float) -> cq.Solid:
    return box(
        center_x - size_x / 2.0,
        center_y - size_y / 2.0,
        origin_z,
        size_x,
        size_y,
        size_z,
    )


def pin_solid(center_x: float, center_y: float, base_z: float,
              diameter: float, height: float, facets: int | None = None) -> cq.Solid:
    # Build the pin as either a cylinder or a polygonal extrusion.
    if facets is None:
        solid = (
            cq.Workplane("XY")
            .center(center_x, center_y)
            .circle(diameter / 2.0)
            .extrude(height)
            .val()
        )
    else:
        pts = []
        radius = diameter / 2.0
        for i in range(facets):
            ang = 2.0 * math.pi * i / facets
            pts.append((center_x + radius * math.cos(ang), center_y + radius * math.sin(ang)))
        solid = (
            cq.Workplane("XY")
            .polyline(pts)
            .close()
            .extrude(height)
            .val()
        )

    return solid.translate(cq.Vector(0.0, 0.0, base_z))


def build_heatsink() -> cq.Solid:
    # Fuse the base and all pins into one heatsink solid.
    base = box(*BASE_ORIGIN, *HEATSINK_BASE_MM)
    fused = base
    rows, cols = PIN_GRID

    span = (cols - 1) * PIN_PITCH_MM
    x0 = BASE_ORIGIN[0] + (HEATSINK_BASE_MM[0] - span) / 2.0
    y0 = BASE_ORIGIN[1] + (HEATSINK_BASE_MM[1] - span) / 2.0
    pin_base_z = BASE_ORIGIN[2] + HEATSINK_BASE_MM[2]

    for r in range(rows):
        for c in range(cols):
            idx = r * cols + c
            cx = x0 + c * PIN_PITCH_MM
            cy = y0 + r * PIN_PITCH_MM

            if idx in D8_THIN_PIN_INDICES:
                solid = pin_solid(cx, cy, pin_base_z, D8_THIN_PIN_DIAMETER_MM, PIN_HEIGHT_MM)
            elif idx in D9_FACETED_PIN_INDICES:
                solid = pin_solid(cx, cy, pin_base_z, PIN_DIAMETER_MM, PIN_HEIGHT_MM, D9_FACETED_PIN_FACETS)
            else:
                solid = pin_solid(cx, cy, pin_base_z, PIN_DIAMETER_MM, PIN_HEIGHT_MM)

            fused = fused.fuse(solid)

    return fused


def build_case() -> cq.Assembly:
    heatsink = build_heatsink()

    # Air volume is the external flow domain above the package.
    air = box(*AIR_ORIGIN, *AIR_BOX_MM).cut(heatsink)

    # Chip die sits below the TIM, centered under the heatsink base.
    chip_center_x = BASE_ORIGIN[0] + HEATSINK_BASE_MM[0] / 2.0
    chip_center_y = BASE_ORIGIN[1] + HEATSINK_BASE_MM[1] / 2.0
    chip_die = centered_box(
        chip_center_x,
        chip_center_y,
        -(TIM_THICKNESS_MM + CHIP_DIE_MM[2]),
        CHIP_DIE_MM[0],
        CHIP_DIE_MM[1],
        CHIP_DIE_MM[2],
    )

    # TIM is the thin interposer between chip and heatsink.
    tim = centered_box(
        chip_center_x,
        chip_center_y,
        -TIM_THICKNESS_MM,
        CHIP_DIE_MM[0],
        CHIP_DIE_MM[1],
        TIM_THICKNESS_MM,
    )

    asm = cq.Assembly(name=CASE_ID)
    asm.add(air, name="region_air")
    asm.add(chip_die, name="region_chip_die")
    asm.add(tim, name="region_tim")
    asm.add(heatsink, name="region_heatsink")
    return asm


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        default="/Users/Zhuanz/Desktop/case_017_pin_fin_electronic_heatsink/inputs/cad_codex_v1.step",
        help="Output STEP path",
    )
    args = parser.parse_args()

    out_path = Path(args.out).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    asm = build_case()
    asm.save(str(out_path), exportType="STEP")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## Deliverable 3 — STEP file path

`/Users/Zhuanz/Desktop/case_017_pin_fin_electronic_heatsink/inputs/cad_codex_v1.step`

## Deliverable 4 — Parts manifest

```yaml
case_id: case_017_pin_fin_electronic_heatsink
cad_source: codex-designed (Tier 3 parametric CadQuery)
generation_script: scripts/case_017_pin_fin_electronic_heatsink.py
step_file: /Users/Zhuanz/Desktop/case_017_pin_fin_electronic_heatsink/inputs/cad_codex_v1.step
units_in_step: mm
regions: 4
region_count_choice: 4
region_count_reason: "Included TIM to reflect real CPU/GPU package stack-up and to force the chip_die -> TIM -> heatsink solid-solid conjugate interfaces."
parts:
  - name: region_air
    role: fluid
    notes: "Forced-convection air domain above the pin-fin array."
  - name: region_chip_die
    role: solid
    notes: "Silicon heat source; bottom face carries fixedHeatFlux."
  - name: region_tim
    role: solid
    notes: "0.08 mm thermal interface material, thermal grease."
  - name: region_heatsink
    role: solid
    notes: "Aluminum 6063 base + pin array fused into one body."
conjugate_interfaces:
  - pair: region_air:air_heatsink_interface <-> region_heatsink:heatsink_air_interface
    bc: turbulentTemperatureCoupledBaffleMixed
    surfaces: "pin tops, pin sidewalls, exposed base-top areas"
  - pair: region_heatsink:heatsink_tim_interface <-> region_tim:tim_heatsink_interface
    bc: turbulentTemperatureCoupledBaffleMixed
    surfaces: "bottom face of heatsink base"
  - pair: region_tim:tim_chip_interface <-> region_chip_die:chip_tim_interface
    bc: turbulentTemperatureCoupledBaffleMixed
    surfaces: "chip top / TIM bottom"
thermophysics:
  air:
    rho: 1.18
    mu: 1.85e-05
    cp: 1007
    k: 0.026
    pr: 0.71
  silicon:
    rho: 2330
    cp: 700
    k: 130
  aluminum_6063:
    rho: 2700
    cp: 896
    k: 200
  tim:
    rho: 2500
    cp: 1000
    k: 4
chip_operating_point:
  P_chip_W: 90
  T_air_in_K: 298.15
  U_air_m_s: 3.5
  Re_pin_estimate: 335
  T_chip_target_C: 85
reference_correlation:
  source: TIMA / IBM pin-fin junction-to-ambient correlation
  expected_R_theta_junction_to_ambient_K_per_W: "0.50-0.60"
  acceptance_band: "CFD within ±15% of correlation prediction"
notes:
  - "simulationType: laminar baseline; low-Re transitional sensitivity only if needed."
  - "air inlet uses flowRateInletVelocity with fixed T = 298.15 K."
  - "chip_bottom heat flux = P_chip / chip area."
```

## Deliverable 5 — Defect manifest

```yaml
case_id: case_017_pin_fin_electronic_heatsink
defects:
  - defect_id: D8
    name: thin_pin_walls
    advisor: thin_wall_advisor
    advisor_status: "[VALIDATED 6-of-6]"
    case_role: "8th-or-9th cross-topology arc data point"
    target_geometry: "4 corner pins"
    realized_value_mm: 0.5
    expected_warning_window_mm: "0.3-0.6"
    geometry_check: "bbox-min / local thickness on the selected pin bodies"
    notes:
      - "Thin-feature warning should be critical, not advisory."
      - "This defect is intentionally kept away from the central chip footprint."
  - defect_id: D9
    name: faceted_pin_cross_section
    advisor: NONE
    case_role: "manual verification only; second D9 if case_016 already landed an advisor candidate"
    target_geometry: "4 inboard corner-adjacent pins"
    facet_count: 10
    verification_method: "Chord-length comparison against an ideal smooth circle"
    notes:
      - "Faceting must be visible in STEP geometry, not just metadata."
      - "The four D9 pins are different from the four D8 corner pins."
```

I used the available `case_002b_apu_bay_cht.md` plus the case_011 materials because the named `case_002b_codex_response.md` file is not present in this tree. The STEP binary itself could not be written from this read-only workspace; the script targets the requested output path above.

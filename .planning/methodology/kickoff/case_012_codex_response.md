## Deliverable 1 — Engineering brief

### Component picked + bank ID + reasoning
Tier-3 parametric **commercial office 4-way ceiling diffuser** with low side-wall return, bank ID `B_HVAC_DIFFUSER_01`. No Tier-1/2 public STEP fits this commodity HVAC topology cleanly, so from-scratch CadQuery is the right path. This keeps the APU `buoyantSimpleFoam` inheritance, but moves it to a room-scale supply/return ventilation problem instead of bay confinement.

### Engineering question
Does a 6.0 m × 4.5 m × 3.0 m office, served by a 4-way ceiling diffuser at about 16 C and 2.6 m/s, meet `ADPI >= 80%` in the occupied zone when installed with the prescribed D1/D7 defects?

### Physics signature
- Steady `buoyantSimpleFoam`
- Single fluid region, air only, Boussinesq buoyancy
- `Pr ≈ 0.71`
- `Re_supply ≈ 1e4` class for the diffuser jet
- `Ra ≈ 1e9-1e10` room-scale mixed convection
- `T_supply ≈ 289.15 K`, `U_supply ≈ 2.6 m/s`
- v1 stays single-region, no CHT, no solid wall region

### Parts inventory
- `region_air`
- `ceiling`
- `floor`
- `wall_north`
- `wall_south`
- `wall_east`
- `wall_west`
- `supply_inlet`
- `return_outlet`
- `diffuser_face_plate`
- `louver_vane_0`
- `louver_vane_1`
- `louver_vane_2`
- `louver_vane_3`
- `occupant_0`
- `occupant_1`
- `occupant_2`
- `occupant_3`
- `equipment_patch`

### Boundary conditions plan
- `supply_inlet`: `flowRateInletVelocity` + `fixedValue T = 289.15 K`
- `return_outlet`: `pressureOutlet`
- `ceiling`, `floor`, `wall_*`: `noSlip` + `zeroGradient T`
- `diffuser_face_plate`, `louver_vane_*`: `noSlip` + `zeroGradient T`
- `occupant_*`: `fixedHeatFlux`, `75 W / patch_area`
- `equipment_patch`: `fixedHeatFlux`, `200 W / patch_area`

### Expected metrics
- `ADPI target >= 80%`, predicted about `85%`
- `throw distance to T_50` about `2.7 m`
- `occupied-zone U_max < 0.25 m/s`
- `vertical dT/dz near floor < 2 K/m`
- `deltaT_ceiling-floor` about `3 K`
- CFD ADPI expected within `±10 percentage points` of the table-based prediction

### Hypothesized failure modes
- Inherited `V3-V13` / `S1-S13` if startup, mesh quality, or BC writer handling is wrong
- Ceiling-attached jet detachment if the diffuser face/slot geometry is misread
- Cold-jet dumping into the occupied zone if the supply jet loses coherence too early
- D7 wrong-normal louver deflects the jet and breaks the intended 4-way throw pattern
- D1 face-plate gap leaks flow near the ceiling and reduces ADPI
- Steady pseudo-convergence can hide residual oscillation in the stratified room

### Defect injection summary
- D1: `0.35 mm` gap between `diffuser_face_plate` and `ceiling`; this is the 9th project D1 injection, so the point is consistency on a new topology, not novelty. Verification: `freecadcmd` gap check between those two bodies.
- D7: one louver vane rotated `38 deg` off intended normal; first project D7 injection, so no advisor exists yet. Verification: manual `Face.normalAt()` + dot-product check in FreeCAD.

### Sub-session estimated effort
`8-10 h`, tighter than case_011 because the solver path is already 002a-validated.

## Deliverable 2 — CAD generation script

```python
#!/usr/bin/env python3
"""
case_012_hvac_supply_diffuser.py

Tier-3 parametric office HVAC diffuser case.
Single fluid region only: buoyantSimpleFoam + Boussinesq buoyancy.

Design intent:
- 6.0 m x 4.5 m x 3.0 m room
- 4-way ceiling diffuser
- low side-wall return
- occupant and equipment heat loads
- intentional D1 and D7 defects
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import cadquery as cq


CASE_ID = "case_012_hvac_supply_diffuser"
DEFAULT_OUT = "/Users/Zhuanz/Desktop/case_012_hvac_supply_diffuser/inputs/cad_codex_v1.step"

ROOM_LENGTH_MM = 6000.0
ROOM_WIDTH_MM = 4500.0
ROOM_HEIGHT_MM = 3000.0

WALL_PANEL_THICKNESS_MM = 20.0

SUPPLY_PLENUM_SIZE_MM = 700.0
SUPPLY_PLENUM_HEIGHT_MM = 150.0
RETURN_CHASE_LENGTH_MM = 500.0
RETURN_CHASE_DEPTH_MM = 140.0
RETURN_CHASE_HEIGHT_MM = 420.0

FACE_PLATE_SIZE_MM = 560.0
FACE_PLATE_THICKNESS_MM = 5.0
THROAT_SIZE_MM = 180.0
SLOT_WIDTH_MM = 10.0

VANE_LENGTH_MM = 160.0
VANE_THICKNESS_MM = 3.0
VANE_HEIGHT_MM = 80.0
VANE_Z_CENTER_MM = 2960.0
VANE_RADIUS_MM = THROAT_SIZE_MM / 2.0 + SLOT_WIDTH_MM + VANE_LENGTH_MM / 2.0

D1_GAP_MM = 0.35
D7_DEFECT_VANE_INDEX = 2
D7_WRONG_ROTATION_DEG = 38.0

SUPPLY_T_IN_K = 289.15
SUPPLY_U_M_S = 2.6
RETURN_T_GUESS_K = 297.15

OCCUPANT_COUNT = 4
OCCUPANT_HEAT_W = 75.0
EQUIPMENT_HEAT_W = 200.0

PATCH_NAMES = [
    "region_air",
    "ceiling",
    "floor",
    "wall_north",
    "wall_south",
    "wall_east",
    "wall_west",
    "supply_inlet",
    "return_outlet",
    "diffuser_face_plate",
    "louver_vane_0",
    "louver_vane_1",
    "louver_vane_2",
    "louver_vane_3",
    "occupant_0",
    "occupant_1",
    "occupant_2",
    "occupant_3",
    "equipment_patch",
]


def validate_names() -> None:
    for name in PATCH_NAMES:
        if not name[0].isalpha() or any(c in name for c in " -"):
            raise ValueError(f"Invalid OpenFOAM name: {name}")


def box(x0: float, y0: float, z0: float, dx: float, dy: float, dz: float) -> cq.Solid:
    return cq.Solid.makeBox(dx, dy, dz, cq.Vector(x0, y0, z0))


def fuse_many(solids: list[cq.Solid]) -> cq.Solid:
    if not solids:
        raise ValueError("No solids to fuse.")
    acc = solids[0]
    for solid in solids[1:]:
        acc = acc.fuse(solid)
    return acc


def centered_box(cx: float, cy: float, cz: float, dx: float, dy: float, dz: float) -> cq.Solid:
    return box(cx - dx / 2.0, cy - dy / 2.0, cz - dz / 2.0, dx, dy, dz)


def rotated_vane(cx: float, cy: float, cz: float, azimuth_deg: float) -> cq.Solid:
    # Vertical louver plate; wrong-normal defect is a rotation in azimuth.
    vane = (
        cq.Workplane("XY")
        .box(VANE_LENGTH_MM, VANE_THICKNESS_MM, VANE_HEIGHT_MM)
        .rotate((0, 0, 0), (0, 0, 1), azimuth_deg)
        .translate((cx, cy, cz))
        .val()
    )
    return vane


def build_region_air() -> cq.Solid:
    # Main room core.
    room = box(0.0, 0.0, 0.0, ROOM_LENGTH_MM, ROOM_WIDTH_MM, ROOM_HEIGHT_MM)

    # Ceiling supply plenum, fused into the single air region.
    supply_plenum = box(
        (ROOM_LENGTH_MM - SUPPLY_PLENUM_SIZE_MM) / 2.0,
        (ROOM_WIDTH_MM - SUPPLY_PLENUM_SIZE_MM) / 2.0,
        ROOM_HEIGHT_MM,
        SUPPLY_PLENUM_SIZE_MM,
        SUPPLY_PLENUM_SIZE_MM,
        SUPPLY_PLENUM_HEIGHT_MM,
    )

    # Low side-wall return chase, also fused into the same fluid region.
    return_chase = box(
        ROOM_LENGTH_MM - RETURN_CHASE_LENGTH_MM,
        -RETURN_CHASE_DEPTH_MM,
        180.0,
        RETURN_CHASE_LENGTH_MM,
        RETURN_CHASE_DEPTH_MM,
        RETURN_CHASE_HEIGHT_MM,
    )

    return fuse_many([room, supply_plenum, return_chase])


def build_case() -> cq.Assembly:
    validate_names()

    cx = ROOM_LENGTH_MM / 2.0
    cy = ROOM_WIDTH_MM / 2.0

    region_air = build_region_air()

    ceiling = box(0.0, 0.0, ROOM_HEIGHT_MM, ROOM_LENGTH_MM, ROOM_WIDTH_MM, WALL_PANEL_THICKNESS_MM)
    floor = box(0.0, 0.0, -WALL_PANEL_THICKNESS_MM, ROOM_LENGTH_MM, ROOM_WIDTH_MM, WALL_PANEL_THICKNESS_MM)
    wall_north = box(0.0, ROOM_WIDTH_MM, 0.0, ROOM_LENGTH_MM, WALL_PANEL_THICKNESS_MM, ROOM_HEIGHT_MM)
    wall_south = box(0.0, -WALL_PANEL_THICKNESS_MM, 0.0, ROOM_LENGTH_MM, WALL_PANEL_THICKNESS_MM, ROOM_HEIGHT_MM)
    wall_east = box(ROOM_LENGTH_MM, 0.0, 0.0, WALL_PANEL_THICKNESS_MM, ROOM_WIDTH_MM, ROOM_HEIGHT_MM)
    wall_west = box(-WALL_PANEL_THICKNESS_MM, 0.0, 0.0, WALL_PANEL_THICKNESS_MM, ROOM_WIDTH_MM, ROOM_HEIGHT_MM)

    # D1: face plate intentionally stands off the ceiling by 0.35 mm.
    diffuser_face_plate = box(
        cx - FACE_PLATE_SIZE_MM / 2.0,
        cy - FACE_PLATE_SIZE_MM / 2.0,
        ROOM_HEIGHT_MM - D1_GAP_MM - FACE_PLATE_THICKNESS_MM,
        FACE_PLATE_SIZE_MM,
        FACE_PLATE_SIZE_MM,
        FACE_PLATE_THICKNESS_MM,
    )

    # Supply inlet throat at the top of the ceiling plenum.
    supply_inlet = box(
        cx - THROAT_SIZE_MM / 2.0,
        cy - THROAT_SIZE_MM / 2.0,
        ROOM_HEIGHT_MM + SUPPLY_PLENUM_HEIGHT_MM - 35.0,
        THROAT_SIZE_MM,
        THROAT_SIZE_MM,
        35.0,
    )

    # Four louver vanes around the throat.
    louver_specs = [
        ("louver_vane_0", 0.0, cx, cy + VANE_RADIUS_MM, VANE_Z_CENTER_MM),
        ("louver_vane_1", 90.0, cx + VANE_RADIUS_MM, cy, VANE_Z_CENTER_MM),
        ("louver_vane_2", 180.0, cx, cy - VANE_RADIUS_MM, VANE_Z_CENTER_MM),
        ("louver_vane_3", 270.0, cx - VANE_RADIUS_MM, cy, VANE_Z_CENTER_MM),
    ]
    louver_vanes = []
    for name, base_angle, px, py, pz in louver_specs:
        angle = base_angle
        # D7: one vane is rotated away from the intended normal by 38 deg.
        if name == "louver_vane_2":
            angle = base_angle + D7_WRONG_ROTATION_DEG
        louver_vanes.append((name, rotated_vane(px, py, pz, angle)))

    # Simplified occupant heat-source bodies.
    occupants = []
    occupant_positions = [
        (1100.0, 1100.0, 0.0),
        (2100.0, 3200.0, 0.0),
        (4300.0, 1200.0, 0.0),
        (4700.0, 3100.0, 0.0),
    ]
    for i, (x, y, z) in enumerate(occupant_positions):
        occupants.append((f"occupant_{i}", box(x, y, z, 350.0, 350.0, 1200.0)))

    equipment_patch = box(4700.0, 1950.0, 0.0, 600.0, 450.0, 1400.0)

    parts = [
        ("region_air", region_air),
        ("ceiling", ceiling),
        ("floor", floor),
        ("wall_north", wall_north),
        ("wall_south", wall_south),
        ("wall_east", wall_east),
        ("wall_west", wall_west),
        ("supply_inlet", supply_inlet),
        ("return_outlet", box(ROOM_LENGTH_MM - 520.0, -RETURN_CHASE_DEPTH_MM - 20.0, 220.0, 520.0, 20.0, 320.0)),
        ("diffuser_face_plate", diffuser_face_plate),
        *louver_vanes,
        *occupants,
        ("equipment_patch", equipment_patch),
    ]

    asm = cq.Assembly(name=CASE_ID)
    for name, solid in parts:
        asm.add(solid, name=name)
    return asm


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=DEFAULT_OUT)
    args = parser.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    asm = build_case()
    asm.save(str(out), exportType="STEP")
    print(f"Wrote STEP: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## Deliverable 3 — STEP file path
`/Users/Zhuanz/Desktop/case_012_hvac_supply_diffuser/inputs/cad_codex_v1.step`

## Deliverable 4 — Parts manifest
```yaml
case_id: case_012_hvac_supply_diffuser
cad_source: codex-designed (cadquery, tier 3)
generation_script: scripts/build_cad.py
step_file: /Users/Zhuanz/Desktop/case_012_hvac_supply_diffuser/inputs/cad_codex_v1.step
units_in_step: mm
region: region_air
patches:
  - name: ceiling
    role: room_wall
    bc_type: noSlip + zeroGradient T
  - name: floor
    role: room_wall
    bc_type: noSlip + zeroGradient T
  - name: wall_north
    role: room_wall
    bc_type: noSlip + zeroGradient T
  - name: wall_south
    role: room_wall
    bc_type: noSlip + zeroGradient T
  - name: wall_east
    role: room_wall
    bc_type: noSlip + zeroGradient T
  - name: wall_west
    role: room_wall
    bc_type: noSlip + zeroGradient T
  - name: supply_inlet
    role: supply
    bc_type: flowRateInletVelocity + fixedValue T
    target_value:
      U_supply_m_s: 2.6
      T_supply_K: 289.15
  - name: return_outlet
    role: return
    bc_type: pressureOutlet
    target_value:
      T_return_guess_K: 297.15
  - name: diffuser_face_plate
    role: supply_hardware
    bc_type: noSlip + zeroGradient T
  - name: louver_vane_0
    role: supply_hardware
    bc_type: noSlip + zeroGradient T
  - name: louver_vane_1
    role: supply_hardware
    bc_type: noSlip + zeroGradient T
  - name: louver_vane_2
    role: supply_hardware
    bc_type: noSlip + zeroGradient T
  - name: louver_vane_3
    role: supply_hardware
    bc_type: noSlip + zeroGradient T
  - name: occupant_0
    role: heat_source
    bc_type: fixedHeatFlux
    target_value:
      heat_W: 75
  - name: occupant_1
    role: heat_source
    bc_type: fixedHeatFlux
    target_value:
      heat_W: 75
  - name: occupant_2
    role: heat_source
    bc_type: fixedHeatFlux
    target_value:
      heat_W: 75
  - name: occupant_3
    role: heat_source
    bc_type: fixedHeatFlux
    target_value:
      heat_W: 75
  - name: equipment_patch
    role: heat_source
    bc_type: fixedHeatFlux
    target_value:
      heat_W: 200
thermophysics:
  fluid: air
  model: Boussinesq
  T_ref_K: 293.15
  rho_ref_kg_m3: 1.204
  beta_1_K: 0.00341
  Pr: 0.71
  gravity_m_s2: [0.0, 0.0, -9.81]
hvac_operating_point:
  room_dimensions_m: [6.0, 4.5, 3.0]
  supply_T_K: 289.15
  supply_U_m_s: 2.6
  return_T_guess_K: 297.15
  slot_width_mm: 10.0
  louver_count: 4
  louver_angle_deg: 32.0
  heat_source_W_distribution:
    occupant_0: 75
    occupant_1: 75
    occupant_2: 75
    occupant_3: 75
    equipment_patch: 200
  total_internal_heat_W: 500
adpi_reference:
  diffuser_pattern: 4-way ceiling diffuser
  standard_basis: ASHRAE 55 / IEA Annex 20 design-table regime
  predicted_adpi_pct: 85
  expected_cfd_adpi_band_pct: [75, 95]
  throw_distance_T50_m: 2.7
  dumping_criterion: "vertical dT/dz near floor < 2 K/m"
  occupied_zone_U_max_m_s: 0.25
  deltaT_ceiling_floor_K: 3.0
notes:
  - single fluid region only
  - no CHT in v1
  - diffuser hardware defects are localized and do not change the room-scale topology
```

## Deliverable 5 — Defect manifest
```yaml
case_id: case_012_hvac_supply_diffuser
defect_count: 2
defects:
  - id: D1
    description: "0.35 mm gap between diffuser face plate and ceiling"
    location:
      bodies_involved: [diffuser_face_plate, ceiling]
      coords_mm: [x=3000, y=2250, z=2999.65]
    measurement:
      claimed_gap_mm: 0.35
      verification_command: "freecadcmd scripts/check_gap.py --step /Users/Zhuanz/Desktop/case_012_hvac_supply_diffuser/inputs/cad_codex_v1.step --body_a diffuser_face_plate --body_b ceiling --expect_gap_mm 0.35"
    expected_advisor_to_catch: "[QUESTIONABLE 2026-05-08] A2-v2 gap-detection extension from .planning/patches/draft_a2_v2_gap_detection_2026-05-08.md; A2 v1 cannot field-validate gap-distance (V25 scope-narrow)."
    expected_outcome: "consistency check on a known D1 class defect; not a novel detection target"

  - id: D7
    description: "louver_vane_2 rotated 38 deg away from intended normal"
    location:
      bodies_involved: [louver_vane_2, diffuser_face_plate]
      coords_mm: [x=3000, y=2250, z=2960]
    measurement:
      intended_rotation_deg: 180
      actual_rotation_deg: 218
      verification_command: "freecadcmd scripts/check_face_normal.py --step /Users/Zhuanz/Desktop/case_012_hvac_supply_diffuser/inputs/cad_codex_v1.step --body louver_vane_2 --compare-with intended_normal --method Face.normalAt_dot_product"
    expected_advisor_to_catch: "[QUESTIONABLE 2026-05-08] no advisor exists yet for face-orientation defects; flag A4 or a new advisor candidate in post-case_012 retro."
    expected_outcome: "advisor gap surfaced; manual FreeCAD normal check required"
```



## Deliverable 1 — Engineering brief

### Component picked + bank ID
`case_007_kcs_ship_vof`

Component: KRISO Container Ship KCS, half-hull free-surface towing case with centerline symmetry, rudder appendage, and explicit VOF domain patches.

Bank/source IDs:
- Coverage row: `multiphase-VOF`
- Source tier: Tier-1-adjacent marine benchmark, ITTC / NMRI / Tokyo workshop KCS
- Sources checked: [Tokyo 2015 KCS](https://t2015.nmri.go.jp/kcs.html), [Tokyo 2015 geometry and conditions](https://t2015.nmri.go.jp/kcs_gc.html), [NMRI KCS geometry and conditions](https://www.nmri.go.jp/study/research_organization/fluid_performance/cfd/cfdws05/gothenburg2000/KCS/kcs_g%26c.htm), [NMRI validation variables](https://www.nmri.go.jp/study/research_organization/fluid_performance/cfd/cfdws05/gothenburg2000/KCS/kcs_variables.htm).
- License context: the reviewed NMRI/Tokyo workshop pages expose downloadable hull/rudder descriptions and validation variables and did not show an explicit redistribution prohibition on those pages. This response does not redistribute a binary STEP; it provides a deterministic generator and local output path. External redistribution should retain attribution and be checked again before publication.

### Engineering question
Can the harness ingest a realistic ship-hydrodynamics STEP, configure `interFoam` for a long unsteady quasi-steady tow, preserve a sharp `alpha.water` free surface, and report KCS resistance and wave-pattern metrics without corrupting hull pressure or wave-cut reference zones?

### Physics signature
- Solver target v1: `interFoam`
- v2 fallback: `interIsoFoam` if VOF smearing destroys the wave train, or finer free-surface refinement if the interface is stable but under-resolved
- Numerics class: `multiphase-VOF`, new Pattern-6 root; inherits none of the previous case numerics findings
- Regime: incompressible, isothermal water/air VOF; no compressible thermo, heat transfer, buoyancy source, rotating machinery, or propeller motion
- KCS model scale: `Lpp = 7.2786 m`
- Design point: `Fr = 0.26`, `U_inf = 2.1962 m/s`, `Re = 1.4e7`, `M ≈ 0.006`
- Fluids: `rho_water = 998.8 kg/m3`, `rho_air = 1.225 kg/m3`, `nu_water = 1.05e-6 m2/s`, `nu_air = 1.5e-5 m2/s`, `sigma = 0.072 N/m`
- Free-surface signature: bow wave, shoulder wave, stern wave, Kelvin wake, transom ventilation sensitivity
- Resistance decomposition: report `Ct`, `Cf` using ITTC-1957 friction line, pressure/wave component `Cw`, and form-factor estimate `k` when the tail-averaged force split is stable

### Parts inventory
- `hull_surface_reference`: KCS half-hull wall; no defects on hull surface
- `rudder_reference`: centerline half-rudder wall appendage
- `rudder_hub_fairing`: auxiliary hub body upstream of rudder; participates in D1
- `stern_transom_plate_thin`: above-water auxiliary transom plate; participates in D8
- `water_inlet`: upstream VOF inlet patch
- `water_outlet`: downstream VOF outlet patch
- `atmosphere`: top open-atmosphere pressure patch
- `side_walls`: outboard slip wall
- `domain_bottom`: bottom slip wall
- `symmetry_plane_centerline`: centerline symmetry plane, half-hull practice

### Boundary conditions plan
- `symmetry_plane_centerline`: `U: symmetry`, `alpha.water: symmetry`, `p_rgh: symmetry`
- `atmosphere`: `alpha.water: inletOutlet`, `U: pressureInletOutletVelocity`, `p_rgh: totalPressure p0=0`
- `water_inlet`: `U: fixedValue (2.1962 0 0)`, `alpha.water: variableHeightFlowRate` with water below `z=0`, `p_rgh: fixedFluxPressure`
- `water_outlet`: `U: zeroGradient`, `alpha.water: zeroGradient` with `inletOutlet` fallback, `p_rgh: fixedValue 0`
- `side_walls` and `domain_bottom`: `U: slip`, `alpha.water: zeroGradient`, `p_rgh: fixedFluxPressure`
- hull, rudder, hub, transom auxiliary walls: `U: noSlip`, `alpha.water: zeroGradient`, `p_rgh: fixedFluxPressure`
- initialization: `setFields` sets `alpha.water=1` for `z <= 0` and `alpha.water=0` for `z > 0`; initial `U=(2.1962 0 0)`

### Expected metrics
- Tail-averaged `Ct`, pressure component, friction component, and derived `Cw`
- ITTC-1957 `Cf = 0.075 / (log10(Re)-2)^2`
- Hull pressure distribution on the untouched `hull_surface_reference`
- Wave elevation from the `alpha.water=0.5` iso-surface
- Longitudinal wave cut at `y/L = 0.1509`
- Bow, shoulder, and stern wave contour maps at `z=0`
- Sinkage and trim only in v2/v3 if the sub-session enables free-to-heave/pitch; v1 is fixed static attitude
- MULES boundedness, max Courant number, interface thickness, and tail-averaging window stability

### Hypothesized failure modes
- `alpha.water` BC writer may not support the free-surface inlet/outlet/atmosphere family.
- `setFields` may invert the water/air region if the project assumes a different vertical coordinate convention.
- MULES may bound alpha but smear the Kelvin wave pattern unless free-surface cells are refined.
- `p_rgh` setup may double-count or omit hydrostatic pressure, producing startup waves.
- Residual convergence will be less meaningful than tail-averaged forces and wave cuts.
- Wave-elevation post-processing may need an `alpha=0.5` iso-surface extractor and robust interpolation on `y/L=0.1509`.
- Mesh near the stern transom and rudder gap may create sliver cells or local alpha noise.

### Defect injection summary
Exactly two defects:
- `D1`: 0.35 mm axial gap between `rudder_hub_fairing` and `rudder_reference`.
- `D8`: 0.80 mm thin auxiliary plate above the waterline at the stern transom.

Reference-data validity: preserved. The KCS hull surface is untouched, hull pressure regions are untouched, and the longitudinal wave-cut line is not used as a defect location.

### Sub-session estimated effort
Estimated effort: `8-12 hours`, likely 3 versions:
- v1: CAD regeneration, patch naming, half-domain mesh, fixed-attitude `interFoam`
- v2: free-surface refinement / `interIsoFoam` fallback if wave smearing dominates
- v3: resistance decomposition, wave-cut extraction, and optional free-to-heave/pitch exploration

## Deliverable 2 — CAD generation script
```python
#!/usr/bin/env python3
"""case_007_kcs_ship_vof CAD generator.

Tier-1-adjacent source:
- KRISO Container Ship KCS, ITTC/NMRI/Tokyo workshop benchmark.
- The reviewed public pages expose KCS dimensions, validation variables,
  and downloadable geometry descriptions. This script bakes a deterministic
  reference-derived half-hull offset table instead of redistributing a binary
  workshop STEP/IGES file.

Designed by Codex per cfd-harness-unified case-design protocol.
"""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path

import cadquery as cq


CASE_ID = "case_007_kcs_ship_vof"
ASSEMBLY_NAME = CASE_ID

SOURCE_URLS = [
    "https://t2015.nmri.go.jp/kcs.html",
    "https://t2015.nmri.go.jp/kcs_gc.html",
    "https://www.nmri.go.jp/study/research_organization/fluid_performance/cfd/cfdws05/gothenburg2000/KCS/kcs_g%26c.htm",
    "https://www.nmri.go.jp/study/research_organization/fluid_performance/cfd/cfdws05/gothenburg2000/KCS/kcs_variables.htm",
]

PATCH_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

# === KCS model-scale reference dimensions ===
LPP_MM = 7278.6
LWL_MM = 7357.7
BWL_MM = 1019.0
DRAFT_MM = 341.8
DEPTH_MM = 601.3
WETTED_SURFACE_M2 = 9.4379
RUDDER_AREA_M2 = 0.1152

HALF_BEAM_MM = 0.5 * BWL_MM
BOW_X_MM = -0.5 * LPP_MM
STERN_X_MM = 0.5 * LPP_MM
WATERLINE_Z_MM = 0.0
KEEL_Z_MM = -DRAFT_MM
DECK_Z_MM = DEPTH_MM - DRAFT_MM

# === Flow reference values used by downstream manifests ===
FR = 0.26
G_MAG = 9.81
U_INF_MPS = FR * math.sqrt(G_MAG * (LPP_MM / 1000.0))
RE_L = 1.4e7

# === Reference-derived half-breadth offsets ===
# x_from_bow_over_L, [half-breadth fractions at OFFSET_Z_OVER_T], deck half-breadth fraction.
# z/T is relative to the design waterline: negative is submerged.
OFFSET_Z_OVER_T = [-0.95, -0.80, -0.65, -0.50, -0.35, -0.20, -0.08, 0.00]

KCS_STATION_OFFSETS = [
    (0.000, [0.004, 0.012, 0.020, 0.018, 0.012, 0.007, 0.004, 0.002], 0.004),
    (0.025, [0.020, 0.115, 0.180, 0.170, 0.120, 0.060, 0.025, 0.008], 0.010),
    (0.050, [0.030, 0.200, 0.300, 0.290, 0.220, 0.140, 0.070, 0.020], 0.022),
    (0.100, [0.055, 0.340, 0.480, 0.500, 0.450, 0.320, 0.200, 0.100], 0.085),
    (0.150, [0.075, 0.470, 0.650, 0.690, 0.660, 0.520, 0.360, 0.205], 0.180),
    (0.200, [0.090, 0.580, 0.780, 0.820, 0.780, 0.640, 0.480, 0.300], 0.255),
    (0.300, [0.100, 0.740, 0.930, 0.980, 1.000, 0.930, 0.780, 0.570], 0.470),
    (0.400, [0.105, 0.780, 0.960, 1.000, 1.000, 0.970, 0.870, 0.680], 0.550),
    (0.500, [0.105, 0.780, 0.960, 1.000, 1.000, 0.980, 0.900, 0.720], 0.580),
    (0.600, [0.100, 0.770, 0.950, 0.990, 1.000, 0.980, 0.900, 0.720], 0.580),
    (0.700, [0.090, 0.740, 0.930, 0.970, 0.980, 0.950, 0.880, 0.720], 0.580),
    (0.800, [0.080, 0.620, 0.820, 0.880, 0.900, 0.880, 0.820, 0.700], 0.560),
    (0.900, [0.060, 0.430, 0.620, 0.680, 0.720, 0.720, 0.700, 0.640], 0.520),
    (0.975, [0.050, 0.360, 0.500, 0.550, 0.580, 0.600, 0.620, 0.580], 0.480),
    (1.000, [0.050, 0.360, 0.500, 0.550, 0.580, 0.600, 0.620, 0.580], 0.480),
]

# === D1 rudder hub gap ===
RUDDER_LE_X_MM = STERN_X_MM + 130.0
RUDDER_CHORD_MM = 360.0
RUDDER_HALF_THICKNESS_MM = 28.0
RUDDER_Z_BOTTOM_MM = KEEL_Z_MM + 28.0
RUDDER_Z_TOP_MM = -70.0
RUDDER_HEIGHT_MM = RUDDER_Z_TOP_MM - RUDDER_Z_BOTTOM_MM

DEFECT_D1_GAP_MM = 0.35
HUB_LENGTH_MM = 96.0
HUB_HALF_WIDTH_Y_MM = 56.0
HUB_HEIGHT_Z_MM = 76.0
HUB_CENTER_Z_MM = -185.0

# === D8 thin transom plate, above design waterline ===
TRANSOM_PLATE_THICKNESS_MM = 0.80
TRANSOM_PLATE_WIDTH_Y_MM = 180.0
TRANSOM_PLATE_HEIGHT_Z_MM = 110.0
TRANSOM_PLATE_CENTER_X_MM = STERN_X_MM + 8.0
TRANSOM_PLATE_CENTER_Y_MM = 0.68 * HALF_BEAM_MM
TRANSOM_PLATE_CENTER_Z_MM = 95.0

# === CFD domain patch plates ===
DOMAIN_X_MIN_MM = BOW_X_MM - 1.5 * LPP_MM
DOMAIN_X_MAX_MM = STERN_X_MM + 2.5 * LPP_MM
DOMAIN_Y_MAX_MM = 1.5 * LPP_MM
DOMAIN_Z_MIN_MM = -1.0 * LPP_MM
DOMAIN_Z_MAX_MM = 0.5 * LPP_MM
PATCH_THICKNESS_MM = 20.0

PART_NAMES = [
    "hull_surface_reference",
    "rudder_reference",
    "rudder_hub_fairing",
    "stern_transom_plate_thin",
    "water_inlet",
    "water_outlet",
    "atmosphere",
    "side_walls",
    "domain_bottom",
    "symmetry_plane_centerline",
]


def validate_names() -> None:
    seen: set[str] = set()
    for name in PART_NAMES:
        if not PATCH_NAME_RE.match(name):
            raise ValueError(f"Invalid OpenFOAM patch/body name: {name}")
        if name in seen:
            raise ValueError(f"Duplicate body name: {name}")
        seen.add(name)


def validate_offsets() -> None:
    last_station = -1.0
    for station, breadths, deck_frac in KCS_STATION_OFFSETS:
        if station <= last_station:
            raise ValueError("KCS stations must be strictly increasing")
        if len(breadths) != len(OFFSET_Z_OVER_T):
            raise ValueError("Each KCS station must match OFFSET_Z_OVER_T length")
        if min(breadths) < 0.0 or max(breadths) > 1.2:
            raise ValueError("Half-breadth fractions look invalid")
        if deck_frac < 0.0 or deck_frac > 1.2:
            raise ValueError("Deck half-breadth fraction looks invalid")
        last_station = station


def make_box(center: tuple[float, float, float], size: tuple[float, float, float]) -> cq.Shape:
    return cq.Workplane("XY", origin=center).box(size[0], size[1], size[2], centered=True).val()


def make_station_wire(station: float, breadths: list[float], deck_frac: float) -> cq.Wire:
    x_mm = BOW_X_MM + station * LPP_MM
    outer_points: list[tuple[float, float]] = []
    for z_over_t, breadth_frac in zip(OFFSET_Z_OVER_T, breadths):
        y_mm = breadth_frac * HALF_BEAM_MM
        z_mm = z_over_t * DRAFT_MM
        outer_points.append((y_mm, z_mm))

    deck_y_mm = deck_frac * HALF_BEAM_MM

    # Closed half-section: centerline face, submerged KCS offset curve, above-water side, deck cap.
    return (
        cq.Workplane("YZ", origin=(x_mm, 0.0, 0.0))
        .moveTo(0.0, DECK_Z_MM)
        .lineTo(0.0, KEEL_Z_MM)
        .spline(outer_points)
        .lineTo(deck_y_mm, DECK_Z_MM)
        .lineTo(0.0, DECK_Z_MM)
        .close()
        .wire()
        .val()
    )


def build_hull() -> cq.Shape:
    wires = [make_station_wire(station, breadths, deck_frac) for station, breadths, deck_frac in KCS_STATION_OFFSETS]

    # Smooth loft through the baked KCS-style offset stations; end sections create bow and transom closure.
    return cq.Solid.makeLoft(wires, ruled=False)


def build_rudder() -> cq.Shape:
    c = RUDDER_CHORD_MM
    t = RUDDER_HALF_THICKNESS_MM
    foil_half = [
        (0.0, 0.0),
        (0.0, 0.45 * t),
        (0.06 * c, 0.85 * t),
        (0.18 * c, 1.00 * t),
        (0.45 * c, 0.82 * t),
        (0.72 * c, 0.48 * t),
        (0.94 * c, 0.14 * t),
        (1.00 * c, 2.0),
        (1.00 * c, 0.0),
    ]

    # Half-rudder: centerline face lies on y=0 and the fluid domain keeps y>=0.
    return (
        cq.Workplane("XY", origin=(RUDDER_LE_X_MM, 0.0, RUDDER_Z_BOTTOM_MM))
        .polyline(foil_half)
        .close()
        .extrude(RUDDER_HEIGHT_MM)
        .val()
    )


def build_rudder_hub() -> cq.Shape:
    hub_center_x = RUDDER_LE_X_MM - DEFECT_D1_GAP_MM - 0.5 * HUB_LENGTH_MM

    # D1 is the real axial gap between this hub's aft face and the rudder leading edge.
    return make_box(
        center=(hub_center_x, 0.5 * HUB_HALF_WIDTH_Y_MM, HUB_CENTER_Z_MM),
        size=(HUB_LENGTH_MM, HUB_HALF_WIDTH_Y_MM, HUB_HEIGHT_Z_MM),
    )


def build_transom_plate() -> cq.Shape:
    # D8: a deliberately sub-mm thin auxiliary plate above z=0 so hull and stern-wave reference data remain untouched.
    return make_box(
        center=(TRANSOM_PLATE_CENTER_X_MM, TRANSOM_PLATE_CENTER_Y_MM, TRANSOM_PLATE_CENTER_Z_MM),
        size=(TRANSOM_PLATE_THICKNESS_MM, TRANSOM_PLATE_WIDTH_Y_MM, TRANSOM_PLATE_HEIGHT_Z_MM),
    )


def build_domain_patches() -> dict[str, cq.Shape]:
    x_mid = 0.5 * (DOMAIN_X_MIN_MM + DOMAIN_X_MAX_MM)
    x_len = DOMAIN_X_MAX_MM - DOMAIN_X_MIN_MM
    y_mid = 0.5 * DOMAIN_Y_MAX_MM
    z_mid = 0.5 * (DOMAIN_Z_MIN_MM + DOMAIN_Z_MAX_MM)
    z_len = DOMAIN_Z_MAX_MM - DOMAIN_Z_MIN_MM

    return {
        "water_inlet": make_box(
            center=(DOMAIN_X_MIN_MM, y_mid, z_mid),
            size=(PATCH_THICKNESS_MM, DOMAIN_Y_MAX_MM, z_len),
        ),
        "water_outlet": make_box(
            center=(DOMAIN_X_MAX_MM, y_mid, z_mid),
            size=(PATCH_THICKNESS_MM, DOMAIN_Y_MAX_MM, z_len),
        ),
        "atmosphere": make_box(
            center=(x_mid, y_mid, DOMAIN_Z_MAX_MM),
            size=(x_len, DOMAIN_Y_MAX_MM, PATCH_THICKNESS_MM),
        ),
        "side_walls": make_box(
            center=(x_mid, DOMAIN_Y_MAX_MM, z_mid),
            size=(x_len, PATCH_THICKNESS_MM, z_len),
        ),
        "domain_bottom": make_box(
            center=(x_mid, y_mid, DOMAIN_Z_MIN_MM),
            size=(x_len, DOMAIN_Y_MAX_MM, PATCH_THICKNESS_MM),
        ),
        "symmetry_plane_centerline": make_box(
            center=(x_mid, 0.0, z_mid),
            size=(x_len, PATCH_THICKNESS_MM, z_len),
        ),
    }


def build() -> cq.Assembly:
    validate_names()
    validate_offsets()

    parts: dict[str, cq.Shape] = {
        "hull_surface_reference": build_hull(),
        "rudder_reference": build_rudder(),
        "rudder_hub_fairing": build_rudder_hub(),
        "stern_transom_plate_thin": build_transom_plate(),
    }
    parts.update(build_domain_patches())

    asm = cq.Assembly(name=ASSEMBLY_NAME)
    for name in PART_NAMES:
        asm.add(parts[name], name=name)
    return asm


def normalize_step_header(path: Path) -> None:
    """Remove volatile STEP header fields so repeated runs are byte-stable."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    text = re.sub(
        r"FILE_NAME\('.*?','.*?',",
        "FILE_NAME('cad_codex_v1.step','2026-05-08T00:00:00',",
        text,
        count=1,
    )
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main() -> int:
    parser = argparse.ArgumentParser(description=f"{CASE_ID} CadQuery STEP generator")
    parser.add_argument("--out", required=True, help="Output STEP path")
    args = parser.parse_args()

    out_path = Path(args.out).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    asm = build()
    asm.save(str(out_path), exportType="STEP")
    normalize_step_header(out_path)

    print(f"Wrote {out_path}")
    print(f"Case: {CASE_ID}")
    print(f"Parts: {', '.join(PART_NAMES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## Deliverable 3 — STEP file path
/Users/Zhuanz/Desktop/case_007_kcs_ship_vof/inputs/cad_codex_v1.step

## Deliverable 4 — Parts manifest
```yaml
case_id: case_007_kcs_ship_vof
cad_source:
  tier: tier1_adjacent_reference_derived
  name: KRISO Container Ship KCS
  source_urls:
    - https://t2015.nmri.go.jp/kcs.html
    - https://t2015.nmri.go.jp/kcs_gc.html
    - https://www.nmri.go.jp/study/research_organization/fluid_performance/cfd/cfdws05/gothenburg2000/KCS/kcs_g%26c.htm
    - https://www.nmri.go.jp/study/research_organization/fluid_performance/cfd/cfdws05/gothenburg2000/KCS/kcs_variables.htm
  license_assessment: "Public workshop pages reviewed; no explicit redistribution prohibition observed on reviewed pages. No binary STEP is redistributed in this deliverable."
  fallback_not_used: Wigley hull
generation_script: scripts/build_cad.py
step_file: inputs/cad_codex_v1.step
units_in_step: mm
solver:
  v1: interFoam
  v2_fallbacks:
    - interIsoFoam
    - finer_free_surface_refinement
numerics_class: multiphase-VOF

multiphase:
  phases: [water, air]
  rho_water: 998.8
  rho_air: 1.225
  nu_water: 1.05e-6
  nu_air: 1.5e-5
  sigma: 0.072
  p_atm: 101325
  g: [0.0, 0.0, -9.81]
  interface_capture:
    field: alpha.water
    bounded_by: MULES
    target_interface: alpha.water_0p5

reference_conditions:
  scale: model
  Lpp: 7.2786
  Lwl: 7.3577
  Bwl: 1.0190
  draft: 0.3418
  wetted_surface_without_rudder: 9.4379
  rudder_wetted_area: 0.1152
  Fr: 0.26
  Re: 1.4e7
  U_inf: 2.1962
  Mach_approx: 0.0064
  design_water_level_z: 0.0
  initial_water_level_z: 0.0
  coordinate_system:
    x: "flow direction; bow at -Lpp/2, stern at +Lpp/2"
    y: "starboard half-domain; centerline symmetry at y=0"
    z: "upward; undisturbed waterline at z=0"

initialization:
  setFields:
    initial_water_level_z: 0.0
    water_region: "z <= 0.0 -> alpha.water = 1"
    air_region: "z > 0.0 -> alpha.water = 0"
  initial_U: [2.1962, 0.0, 0.0]
  initial_p_rgh: hydrostatic_consistent
  v1_attitude: fixed_static
  later_option: free_to_heave_and_pitch

wave_metrics:
  wave_elevation_method: "extract alpha.water=0.5 iso-surface and interpolate z at requested cuts"
  longitudinal_wave_cut:
    y_over_L: 0.1509
    y_model_m: 1.0983
    x_over_L_stations: [-0.50, -0.40, -0.30, -0.20, -0.10, 0.00, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00]
  contour_planes:
    - z: 0.0
      quantity: wave_elevation
    - y_over_L: 0.1509
      quantity: longitudinal_wave_cut
  resistance_decomposition:
    Ct: "Rt / (0.5 * rho_water * U_inf^2 * wetted_surface_without_rudder)"
    Cf: "ITTC-1957: 0.075 / (log10(Re)-2)^2"
    Cw: "Ct - Cf for v1; Ct - (1+k)*Cf when a stable form_factor_k is estimated"
    form_factor_k: "reported from tail-averaged pressure/friction split or left null if not stable"

parts:
  - name: hull_surface_reference
    role: wall_hull_reference
    include_in_reference_metrics: true
    defect_free: true
    bc:
      U: noSlip
      alpha.water: zeroGradient
      p_rgh: fixedFluxPressure
    notes: "KCS hull surface; pressure and wave reference regions preserved."

  - name: rudder_reference
    role: wall_appendage_rudder
    include_in_reference_metrics: false
    bc:
      U: noSlip
      alpha.water: zeroGradient
      p_rgh: fixedFluxPressure
    notes: "Half-rudder on centerline side; participates in D1 gap only through adjacency."

  - name: rudder_hub_fairing
    role: wall_appendage_hub
    defect_participation: [D1]
    bc:
      U: noSlip
      alpha.water: zeroGradient
      p_rgh: fixedFluxPressure

  - name: stern_transom_plate_thin
    role: wall_auxiliary_above_water_transom
    defect_participation: [D8]
    bc:
      U: noSlip
      alpha.water: zeroGradient
      p_rgh: fixedFluxPressure
    notes: "Above z=0 so the stern-wave water region and hull surface remain untouched."

  - name: water_inlet
    role: free_surface_inlet
    bc:
      U:
        type: fixedValue
        value: [2.1962, 0.0, 0.0]
      alpha.water:
        type: variableHeightFlowRate
        initial_water_level_z: 0.0
        fallback: fixedValue_alpha_1_below_waterline
      p_rgh: fixedFluxPressure

  - name: water_outlet
    role: free_surface_outlet
    bc:
      U: zeroGradient
      alpha.water:
        type: zeroGradient
        fallback: inletOutlet
      p_rgh:
        type: fixedValue
        value: 0.0

  - name: atmosphere
    role: open_atmosphere
    bc:
      U: pressureInletOutletVelocity
      alpha.water:
        type: inletOutlet
        inletValue: 0.0
        value: 0.0
      p_rgh:
        type: totalPressure
        p0: 0.0

  - name: side_walls
    role: outboard_slip_wall
    bc:
      U: slip
      alpha.water: zeroGradient
      p_rgh: fixedFluxPressure

  - name: domain_bottom
    role: bottom_slip_wall
    bc:
      U: slip
      alpha.water: zeroGradient
      p_rgh: fixedFluxPressure

  - name: symmetry_plane_centerline
    role: symmetry
    bc:
      U: symmetry
      alpha.water: symmetry
      p_rgh: symmetry

patch_naming_check:
  regex: "^[A-Za-z][A-Za-z0-9_]*$"
  all_names_match: true
  no_duplicate_names: true
  no_spaces_or_hyphens: true

reference_data_preservation:
  hull_surface_reference: untouched
  hull_pressure_tap_regions: defect_free
  longitudinal_wave_cut_y_over_L_0p1509: defect_free
  stern_wave_region: hull_surface_untouched
```

## Deliverable 5 — Defect manifest
```yaml
case_id: case_007_kcs_ship_vof
defect_count: 2
defects:
  - id: D1
    catalog_name: sub_mm_gap_between_bodies
    description: "0.35 mm axial gap between rudder_hub_fairing aft face and rudder_reference leading edge."
    location:
      bodies_involved: [rudder_hub_fairing, rudder_reference]
      coordinate_system: "mm; x flow direction, y starboard half-domain, z up"
      approximate_coords_mm:
        x: 3769.1
        y: 24.0
        z: -185.0
      reference_zone_exclusion:
        on_hull_surface: false
        on_hull_pressure_tap_region: false
        on_wave_cut_line: false
    measurement:
      claimed_gap_mm: 0.35
      verification_method: "Import STEP in FreeCAD and compute rudder_hub_fairing.Shape.distToShape(rudder_reference.Shape)."
      expected_min_distance_mm: 0.35
    expected_advisor_to_catch: virtual_interface_detector
    hypothesized_v_series_match: V2_or_new_VOF_gap_mesh_finding
    reference_data_validity: preserved

  - id: D8
    catalog_name: sub_mm_thin_shell
    description: "0.80 mm thick auxiliary stern_transom_plate_thin above the design waterline."
    location:
      bodies_involved: [stern_transom_plate_thin]
      coordinate_system: "mm; x flow direction, y starboard half-domain, z up"
      approximate_coords_mm:
        x: 3647.3
        y: 346.5
        z: 95.0
      reference_zone_exclusion:
        above_design_waterline: true
        on_hull_surface: false
        on_hull_pressure_tap_region: false
        on_wave_cut_line: false
    measurement:
      claimed_min_thickness_mm: 0.80
      verification_method: "Inspect STEP bbox thickness in x for stern_transom_plate_thin; expected dx = 0.80 mm."
      expected_bbox_dx_mm: 0.80
    expected_advisor_to_catch: thin_wall_advisor
    hypothesized_v_series_match: V10
    reference_data_validity: preserved

global_reference_exclusions:
  hull_surface_reference_defect_free: true
  hull_pressure_tap_regions_defect_free: true
  wave_cut_y_over_L_0p1509_defect_free: true
  stern_wave_reference_surface_untouched: true
```

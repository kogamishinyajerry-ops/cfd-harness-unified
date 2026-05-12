## Deliverable 1 — Engineering brief

### Component picked + bank ID
`case_010_drivaer_fastback_les`

Component: TUM DrivAer fastback, smooth underbody, mirrors, stationary wheels, half-vehicle external aerodynamics model.

Bank/source IDs:
- Coverage row: `Transient LES / DES`
- Component bank extension: `C5_drivaer_fastback_vehicle_aero`
- Numerics class: `incompressible-LES`, new Pattern-6 root; inherits none of the prior V-series fluid-internal numerics findings
- Source tier: Tier-1 reference-derived TUM DrivAer benchmark
- Sources checked:
  - TUM DrivAer overview: https://www.epc.ed.tum.de/en/aer/research-groups/automotive/drivaer/
  - TUM DrivAer geometry taxonomy: https://www.epc.ed.tum.de/en/aer/research-groups/automotive/drivaer/geometry/
  - TUM DrivAer download page: https://www.epc.ed.tum.de/en/aer/research-groups/automotive/drivaer/download/
  - DrivAer fastback LES dimensions/Re reference: https://www.mdpi.com/2311-5521/7/1/19/xml
- Source data used: fastback `F`, smooth underbody `S`, with mirrors `wM`, with wheels `wW`; `L = 4.61 m`, `W = 1.76 m`, `H = 1.42 m`, `wheelbase = 2.79 m`, `U_inf = 16 m/s`, `Re_L ≈ 4.87e6`.
- License assessment: TUM provides STEP/IGES/STL downloads after registration. This response does not redistribute the binary DrivAer CAD; the script below produces a deterministic reference-derived fastback reconstruction suitable for sub-session validation.
- Hard exclusion honored: Ahmed body is not used.

### Engineering question
Can the harness run its first wall-modeled transient LES external-aero case on a DrivAer fastback and recover time-averaged `Cd ≈ 0.281`, `Cl`, `Cm`, surface `Cp`, base-pressure recovery, and instantaneous coherent wake structures without corrupting the front-wheel or rear-wake validation regions?

### Physics signature
- Solver v1: `pimpleFoam` with LES
- LES model v1: `WALE`
- v2 fallback: `pisoFoam` if PIMPLE pressure-velocity correction under-converges within each time step
- Flow: incompressible external vehicle aerodynamics, `Mach ≈ 0.05`
- Geometry: half-vehicle about centerline symmetry plane, fixed ground, stationary wheels
- `L_ref = 4.61 m`, `A_ref ≈ 2.17 m2`, `U_inf = 16 m/s`
- Air: `nu = 1.51e-5 m2/s`, `rho = 1.225 kg/m3`
- Reynolds: `Re_L ≈ 4.87e6`
- Wall treatment: wall-modeled LES, target `y+ = 30-100`, `nutUSpaldingWallFunction`
- Expected topology: A-pillar vortex, side-mirror vortex, front wheelhouse shear layers, underbody gap flow, C-pillar/rear slant separation, broadband wake shedding, base-pressure recovery sensitivity

### Parts inventory
- `vehicle_body`: DrivAer fastback half body, smooth underbody, reference Cp surface
- `side_mirror_outboard`: outboard side mirror and stalk, stationary wall
- `wheel_front_outboard`: stationary front wheel, defect-free drag contribution zone
- `wheel_rear_outboard`: stationary rear wheel
- `mirror_edge_trim_strip`: auxiliary mirror-edge defect body, participates in D1
- `underbody_sensor_cover_thin`: auxiliary side-underbody thin plate, participates in D8
- `inlet`: velocity inlet
- `outlet`: pressure outlet
- `top`: farfield top
- `side_outboard`: farfield side boundary
- `ground`: fixed no-slip ground wall, stationary v1
- `symmetry_plane_centerline`: vehicle centerline symmetry plane

### Boundary conditions plan
- `inlet`: `U fixedValue (16 0 0) m/s`, `p zeroGradient`, resolved turbulence initialized from low-intensity synthetic or mapped precursor if available
- `outlet`: `p fixedValue 0`, `U zeroGradient/inletOutlet`
- `top`, `side_outboard`: slip or `freestream` style farfield
- `symmetry_plane_centerline`: `symmetryPlane` for all fields
- `ground`: fixed no-slip wall, stationary v1
- Vehicle, wheels, mirror, defect bodies: no-slip walls, `nutUSpaldingWallFunction`
- No moving floor, no rotating wheels, no compressible thermo

### Expected metrics
- Time-averaged `Cd`, `Cl`, `Cm`; target `Cd ≈ 0.281` for fastback reference context
- Surface `Cp` at A-pillar, side mirror, roof/rear, base, and underbody taps
- Base-pressure recovery and rear-wake mean velocity deficit
- Instantaneous and mean velocity fields in rear wake planes
- Q-criterion and lambda2 vortex visualizations for A-pillar, mirror, wheel, underbody, and rear-wake structures
- Spectra of drag/lift and selected wake probes after initial transient

### Hypothesized failure modes
- LES time step may be too large for CFL <= 1 in mirror and wheelhouse refinement zones.
- Wall function fields may be generated as generic `zeroGradient`, causing `nut` wall evaluation failures.
- PIMPLE correctors may under-converge per time step if outlet wake backflow is strong.
- Half-vehicle symmetry can suppress asymmetric long-period wake dynamics; acceptable for v1 but document the limitation.
- snappyHexMesh may lose thin auxiliary underbody plate unless local refinement is raised.
- Drag averaging window may start too early and include initialization transient.
- Q/lambda2 thresholds may need normalization by `U_inf` and `L_ref`; raw thresholds may under-report coherent structures.

### Defect injection summary
Exactly two defects, both outside protected validation zones:
- `D1`: 0.35 mm gap between `side_mirror_outboard` and `mirror_edge_trim_strip` at the outboard trailing edge of the mirror housing.
- `D8`: 0.80 mm thick `underbody_sensor_cover_thin` plate on the side underbody between axles, away from front wheel housings, rear wake plane, and centerline.

Reference-data validity: preserved. No defect is on the front wheel housings, rear-wake measurement plane, vehicle centerline, A-pillar pressure taps, rear base taps, or primary Cd/Cl/Cm integration surfaces.

### Sub-session estimated effort
Estimated effort: `10-14 hours`, likely 4 versions:
- v1: CAD regeneration, patch mapping, half-domain mesh, LES dictionaries
- v2: time-step/CFL stabilization and wall-function field repair
- v3: averaging windows, force coefficients, Cp and wake-plane extraction
- v4: Q/lambda2 vortex post-processing and final LES report

## Deliverable 2 — CAD generation script
```python
#!/usr/bin/env python3
"""case_010_drivaer_fastback_les CAD generator.

Reference-derived DrivAer fastback half-vehicle reconstruction for
wall-modeled external LES. The official TUM DrivAer STEP is available
after registration; this script does not redistribute it.

Designed by Codex per cfd-harness-unified case-design protocol.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import cadquery as cq


CASE_ID = "case_010_drivaer_fastback_les"
ASSEMBLY_NAME = CASE_ID
PATCH_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

# === DrivAer reference scale ===
L_REF_MM = 4610.0
WIDTH_FULL_MM = 1760.0
HEIGHT_MM = 1420.0
HALF_WIDTH_MM = 0.5 * WIDTH_FULL_MM
WHEELBASE_MM = 2790.0
FRONT_AXLE_X_MM = 1000.0
REAR_AXLE_X_MM = FRONT_AXLE_X_MM + WHEELBASE_MM
WHEEL_RADIUS_MM = 330.0
TIRE_WIDTH_MM = 225.0
GROUND_Z_MM = 0.0

# === Half-domain blockMesh extents ===
X_MIN_MM = -4.0 * L_REF_MM
X_MAX_MM = L_REF_MM + 8.0 * L_REF_MM
Y_MIN_MM = 0.0
Y_MAX_MM = 3.0 * L_REF_MM
Z_MIN_MM = 0.0
Z_MAX_MM = 5.0 * L_REF_MM
PATCH_THICKNESS_MM = 20.0

# === Intentional defects ===
DEFECT_D1_GAP_MM = 0.35
UNDERBODY_THIN_PLATE_MM = 0.80

PART_NAMES = [
    "vehicle_body",
    "side_mirror_outboard",
    "wheel_front_outboard",
    "wheel_rear_outboard",
    "mirror_edge_trim_strip",
    "underbody_sensor_cover_thin",
    "inlet",
    "outlet",
    "top",
    "side_outboard",
    "ground",
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


def make_box(center: tuple[float, float, float], size: tuple[float, float, float]) -> cq.Shape:
    return cq.Workplane("XY", origin=center).box(size[0], size[1], size[2], centered=True).val()


def make_rounded_box(
    center: tuple[float, float, float],
    size: tuple[float, float, float],
    radius: float,
) -> cq.Shape:
    shape = cq.Workplane("XY", origin=center).box(size[0], size[1], size[2], centered=True)
    return shape.edges().fillet(radius).val()


def section_wire(points_yz: list[tuple[float, float]]) -> cq.Workplane:
    return cq.Workplane("YZ").polyline(points_yz).close()


def build_vehicle_body() -> cq.Shape:
    """Loft a half DrivAer-fastback envelope from published dimensions."""
    sections = [
        (0.00, [(0, 180), (500, 180), (610, 390), (500, 760), (0, 800)]),
        (0.12, [(0, 160), (760, 160), (860, 430), (720, 960), (0, 980)]),
        (0.30, [(0, 150), (860, 150), (900, 520), (700, 1340), (0, 1360)]),
        (0.55, [(0, 150), (875, 150), (905, 600), (600, 1420), (0, 1410)]),
        (0.74, [(0, 155), (850, 155), (870, 560), (470, 1080), (0, 1120)]),
        (0.90, [(0, 170), (800, 170), (820, 520), (330, 820), (0, 840)]),
        (1.00, [(0, 210), (690, 210), (720, 580), (250, 720), (0, 740)]),
    ]

    wp = cq.Workplane("YZ")
    last_x = 0.0
    for i, (x_frac, pts) in enumerate(sections):
        x_abs = x_frac * L_REF_MM
        if i > 0:
            wp = wp.workplane(offset=x_abs - last_x)
        wp = wp.polyline(pts).close()
        last_x = x_abs

    body = wp.loft(combine=True).val()

    # Open wheelhouse regions while keeping the front wheelhouse defect-free.
    for axle_x in (FRONT_AXLE_X_MM, REAR_AXLE_X_MM):
        cavity = (
            cq.Workplane("XZ", origin=(axle_x, HALF_WIDTH_MM - 95.0, WHEEL_RADIUS_MM))
            .circle(WHEEL_RADIUS_MM + 85.0)
            .extrude(TIRE_WIDTH_MM + 190.0, both=True)
            .val()
        )
        body = body.cut(cavity)

    return body


def build_wheel(axle_x: float) -> cq.Shape:
    tire = (
        cq.Workplane("XZ", origin=(axle_x, HALF_WIDTH_MM - 70.0, WHEEL_RADIUS_MM))
        .circle(WHEEL_RADIUS_MM)
        .extrude(TIRE_WIDTH_MM, both=True)
        .val()
    )
    hub = (
        cq.Workplane("XZ", origin=(axle_x, HALF_WIDTH_MM - 70.0, WHEEL_RADIUS_MM))
        .circle(0.55 * WHEEL_RADIUS_MM)
        .extrude(TIRE_WIDTH_MM + 8.0, both=True)
        .val()
    )
    return tire.fuse(hub)


def build_side_mirror() -> cq.Shape:
    housing = make_rounded_box(
        center=(1580.0, HALF_WIDTH_MM + 185.0, 1030.0),
        size=(310.0, 95.0, 155.0),
        radius=22.0,
    )
    stalk = (
        cq.Workplane("XZ", origin=(1470.0, HALF_WIDTH_MM + 70.0, 980.0))
        .circle(28.0)
        .extrude(210.0)
        .val()
    )
    return housing.fuse(stalk)


def build_defect_bodies() -> dict[str, cq.Shape]:
    # D1: mirror trim strip is intended to mate to the mirror housing but is offset by 0.35 mm.
    housing_y_max = HALF_WIDTH_MM + 185.0 + 0.5 * 95.0
    trim_y_center = housing_y_max + DEFECT_D1_GAP_MM + 0.5 * 8.0
    mirror_trim = make_box(
        center=(1660.0, trim_y_center, 1030.0),
        size=(135.0, 8.0, 48.0),
    )

    # D8: sub-mm side-underbody plate between axles, away from front wheel and rear wake zones.
    underbody_plate = make_box(
        center=(2480.0, 0.78 * HALF_WIDTH_MM, 155.0),
        size=(420.0, 210.0, UNDERBODY_THIN_PLATE_MM),
    )

    return {
        "mirror_edge_trim_strip": mirror_trim,
        "underbody_sensor_cover_thin": underbody_plate,
    }


def build_domain_patches() -> dict[str, cq.Shape]:
    x_mid = 0.5 * (X_MIN_MM + X_MAX_MM)
    y_mid = 0.5 * (Y_MIN_MM + Y_MAX_MM)
    z_mid = 0.5 * (Z_MIN_MM + Z_MAX_MM)
    x_len = X_MAX_MM - X_MIN_MM
    y_len = Y_MAX_MM - Y_MIN_MM
    z_len = Z_MAX_MM - Z_MIN_MM

    return {
        "inlet": make_box((X_MIN_MM, y_mid, z_mid), (PATCH_THICKNESS_MM, y_len, z_len)),
        "outlet": make_box((X_MAX_MM, y_mid, z_mid), (PATCH_THICKNESS_MM, y_len, z_len)),
        "top": make_box((x_mid, y_mid, Z_MAX_MM), (x_len, y_len, PATCH_THICKNESS_MM)),
        "side_outboard": make_box((x_mid, Y_MAX_MM, z_mid), (x_len, PATCH_THICKNESS_MM, z_len)),
        "ground": make_box((x_mid, y_mid, Z_MIN_MM), (x_len, y_len, PATCH_THICKNESS_MM)),
        "symmetry_plane_centerline": make_box(
            (x_mid, Y_MIN_MM, z_mid),
            (x_len, PATCH_THICKNESS_MM, z_len),
        ),
    }


def build() -> cq.Assembly:
    validate_names()

    parts: dict[str, cq.Shape] = {
        "vehicle_body": build_vehicle_body(),
        "side_mirror_outboard": build_side_mirror(),
        "wheel_front_outboard": build_wheel(FRONT_AXLE_X_MM),
        "wheel_rear_outboard": build_wheel(REAR_AXLE_X_MM),
    }
    parts.update(build_defect_bodies())
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
    path.write_text(text, encoding="utf-8", newline="\n")


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
/Users/Zhuanz/Desktop/case_010_drivaer_fastback_les/inputs/cad_codex_v1.step

## Deliverable 4 — Parts manifest
```yaml
case_id: case_010_drivaer_fastback_les
cad_source:
  tier: tier1_reference_derived
  name: TUM_DrivAer_Fastback_F_S_wM_wW
  source_urls:
    - https://www.epc.ed.tum.de/en/aer/research-groups/automotive/drivaer/
    - https://www.epc.ed.tum.de/en/aer/research-groups/automotive/drivaer/geometry/
    - https://www.epc.ed.tum.de/en/aer/research-groups/automotive/drivaer/download/
    - https://www.mdpi.com/2311-5521/7/1/19/xml
  geometry_basis: "deterministic CadQuery reconstruction from published DrivAer dimensions and configuration taxonomy"
  official_tum_binary_available_after_registration: true
  binary_source_geometry_redistributed: false
  selected_configuration: F_S_wM_wW
  selected_rear_shape: fastback
  hard_exclusion_honored: Ahmed_body_not_used
generation_script: scripts/build_cad.py
step_file: inputs/cad_codex_v1.step
units_in_step: mm
numerics_class: incompressible-LES

solver:
  v1: pimpleFoam
  les_model_v1: WALE
  v2_fallback: pisoFoam_if_PIMPLE_coupling_under_converges_per_timestep
  flow_model: incompressible_isothermal_external_aero
  moving_ground_v1: false
  rotating_wheels_v1: false
  compressible_thermo: false

geometry:
  vehicle_length_L_m: 4.61
  vehicle_width_full_m: 1.76
  vehicle_height_m: 1.42
  wheelbase_m: 2.79
  model_domain: half_vehicle_right_side
  symmetry_plane: vehicle_centerline
  underbody: smooth
  mirrors: included_outboard_half
  wheels: stationary_outboard_front_and_rear_in_half_domain
  full_reference_configuration_note: "TUM F_S_wM_wW has 4 wheels and 2 mirrors; exported CFD model is centerline half-domain."

blockMesh_domain:
  coordinate_system: "x streamwise, y lateral from centerline to outboard, z vertical from ground"
  L_ref_m: 4.61
  x_min_m: -18.44
  x_max_m: 41.49
  y_min_m: 0.0
  y_max_m: 13.83
  z_min_m: 0.0
  z_max_m: 23.05
  upstream_length: "4 L upstream of vehicle nose"
  downstream_length: "8 L downstream of vehicle tail"
  top_height: "5 L above ground"
  side_extent: "3 L outboard half-domain"
  ground: "z=0 fixed wall"
  base_cell_size_v1_m: 0.16
  local_refinement_targets:
    vehicle_body: 0.025
    side_mirror_outboard: 0.0125
    wheels: 0.015
    rear_wake_box: 0.025
    near_wall_first_cell_target_yplus: [30, 100]

freestream:
  U_inf_mps: 16.0
  U_vector_mps: [16.0, 0.0, 0.0]
  T_K: 293.15
  p_Pa: 101325.0
  rho_kg_m3: 1.225
  nu_m2_s: 1.51e-5
  mu_Pa_s: 1.84975e-5
  L_ref_m: 4.61
  A_ref_m2: 2.17
  Re_L: 4.87e6
  Mach_approx: 0.05
  incompressible_valid: true

les:
  solver: pimpleFoam
  subgrid_model: WALE
  filter_type: cubeRootVol
  wall_treatment: nutUSpaldingWallFunction
  wall_modeling_regime: wall_modeled_LES
  target_yplus: [30, 100]
  resolved_sublayer: false
  timestep_target:
    max_CFL: 1.0
    expected_dt_s: 1.0e-4
    adjustableTimeStep: true
    maxCo: 1.0
    maxDeltaT_s: 1.0e-4
  pimple_controls:
    nOuterCorrectors: 2
    nCorrectors: 2
    nNonOrthogonalCorrectors: 1
  initialization:
    recommended_sequence:
      - potentialFoam_or_uniform_U_initialization
      - short_URANS_like_spinup_optional
      - pimpleFoam_LES_with_small_dt
  averaging:
    flow_through_time_s: 0.288125
    start_after_flow_throughs: 2.0
    average_start_time_s: 0.57625
    accumulate_over_flow_throughs_minimum: 5.0
    accumulation_duration_s_minimum: 1.440625
    force_signal_tail_window_required: true
  fields_to_average:
    - U
    - p
    - nut
    - wallShearStress
    - forces
    - surfaceFieldValue_Cp
    - wake_plane_U

vortex_metrics:
  q_criterion:
    definition: "Q = 0.5 * (||Omega||^2 - ||S||^2)"
    threshold_s2_v1: 250.0
    normalized_threshold: "Q * L_ref^2 / U_inf^2 ≈ 20"
    isosurface_strategy: "write instantaneous Q every 0.01 s after averaging_start_time_s; render positive Q isosurfaces colored by Ux"
  lambda2:
    definition: "second eigenvalue of S^2 + Omega^2"
    threshold_s2_v1: -250.0
    normalized_threshold: "lambda2 * L_ref^2 / U_inf^2 ≈ -20"
    isosurface_strategy: "generate paired lambda2<0 isosurfaces for A-pillar, mirror, underbody, wheel, and rear wake regions"
  wake_planes:
    - name: wake_x_0_5L_downstream
      x_over_L_from_tail: 0.5
    - name: wake_x_1_0L_downstream
      x_over_L_from_tail: 1.0
    - name: wake_x_2_0L_downstream
      x_over_L_from_tail: 2.0
  probe_signals:
    - Cd
    - Cl
    - Cm
    - base_pressure
    - wake_center_Ux

reference_data:
  dataset: TUM_DrivAer_fastback
  canonical_publication: "Heft, Indinger, Adams, Introduction of a New Realistic Generic Car Model for Aerodynamic Investigations, SAE 2012-01-0168"
  target_drag_coefficient_fastback: 0.281
  target_drag_note: "configuration-dependent; compare only after matching half-domain, fixed-ground, stationary-wheel v1 assumptions"
  surface_pressure_tap_regions:
    - A_pillar
    - side_mirror
    - roof
    - rear_slant
    - base
    - underbody
  force_metrics:
    - Cd_time_averaged
    - Cl_time_averaged
    - Cm_time_averaged
  wake_metrics:
    - mean_Ux_deficit
    - Reynolds_stress_optional
    - Q_criterion_structures
    - lambda2_structures
  measurement_preservation:
    front_wheel_housings_defect_free: true
    rear_wake_planes_defect_free: true
    centerline_symmetry_plane_defect_free: true
    A_pillar_pressure_taps_defect_free: true
    rear_base_pressure_taps_defect_free: true

parts:
  - name: vehicle_body
    role: wall_vehicle_reference
    include_in_force_coefficients: true
    include_in_reference_metrics: true
    defect_free_reference_surface: true
    bc:
      U: noSlip
      p: zeroGradient
      nut: nutUSpaldingWallFunction

  - name: side_mirror_outboard
    role: wall_side_mirror
    include_in_force_coefficients: true
    include_in_reference_metrics: true
    bc:
      U: noSlip
      p: zeroGradient
      nut: nutUSpaldingWallFunction

  - name: wheel_front_outboard
    role: wall_stationary_front_wheel
    include_in_force_coefficients: true
    protected_drag_zone: true
    defect_participation: []
    bc:
      U: noSlip
      p: zeroGradient
      nut: nutUSpaldingWallFunction

  - name: wheel_rear_outboard
    role: wall_stationary_rear_wheel
    include_in_force_coefficients: true
    defect_participation: []
    bc:
      U: noSlip
      p: zeroGradient
      nut: nutUSpaldingWallFunction

  - name: mirror_edge_trim_strip
    role: auxiliary_mirror_edge_defect_body
    defect_participation: [D1]
    include_in_force_coefficients: false
    include_in_reference_metrics: false
    bc:
      U: noSlip
      p: zeroGradient
      nut: nutUSpaldingWallFunction

  - name: underbody_sensor_cover_thin
    role: auxiliary_side_underbody_thin_shell_defect_body
    defect_participation: [D8]
    include_in_force_coefficients: false
    include_in_reference_metrics: false
    bc:
      U: noSlip
      p: zeroGradient
      nut: nutUSpaldingWallFunction

  - name: inlet
    role: velocity_inlet
    bc:
      U:
        type: fixedValue
        value: [16.0, 0.0, 0.0]
      p: zeroGradient
      nut: calculated_or_low_turbulence_inlet

  - name: outlet
    role: pressure_outlet
    bc:
      U: zeroGradient_or_inletOutlet
      p:
        type: fixedValue
        value: 0.0
      nut: calculated

  - name: top
    role: farfield_top
    bc:
      U: slip_or_freestream
      p: zeroGradient
      nut: calculated

  - name: side_outboard
    role: farfield_side
    bc:
      U: slip_or_freestream
      p: zeroGradient
      nut: calculated

  - name: ground
    role: fixed_ground_wall
    moving_floor_v1: false
    bc:
      U: noSlip
      p: zeroGradient
      nut: nutUSpaldingWallFunction

  - name: symmetry_plane_centerline
    role: symmetry_plane
    bc:
      U: symmetryPlane
      p: symmetryPlane
      nut: symmetryPlane

patch_naming_check:
  regex: "^[A-Za-z][A-Za-z0-9_]*$"
  all_names_match: true
  no_duplicate_names: true
  no_spaces_or_hyphens: true

reference_data_preservation:
  front_wheel_housings_defect_free: true
  rear_wake_measurement_planes_defect_free: true
  vehicle_centerline_defect_free: true
  defects_restricted_to:
    - side_mirror_outboard_trailing_edge_trim
    - side_underbody_between_axles
  Cd_Cl_Cm_reference_validity: preserved
  surface_Cp_reference_validity: preserved
  wake_topology_reference_validity: preserved
```

## Deliverable 5 — Defect manifest
```yaml
case_id: case_010_drivaer_fastback_les
defect_count: 2
defects:
  - id: D1
    catalog_name: sub_mm_gap_between_bodies
    description: "0.35 mm lateral gap between side_mirror_outboard and mirror_edge_trim_strip at the outboard trailing edge of the side-mirror housing."
    location:
      bodies_involved: [side_mirror_outboard, mirror_edge_trim_strip]
      coordinate_system: "mm; x streamwise from vehicle nose, y lateral from centerline outward, z vertical from ground"
      approximate_coords_mm:
        x: 1660.0
        y: 1112.0
        z: 1030.0
      reference_zone_exclusion:
        on_front_wheel_housing: false
        on_rear_wake_measurement_plane: false
        on_vehicle_centerline: false
        on_A_pillar_pressure_taps: false
        on_rear_base_pressure_taps: false
    measurement:
      claimed_gap_mm: 0.35
      verification_method: "Import STEP in FreeCAD and compute side_mirror_outboard.Shape.distToShape(mirror_edge_trim_strip.Shape)."
      expected_min_distance_mm: 0.35
    expected_advisor_to_catch: virtual_interface_detector
    hypothesized_v_series_match: V2_style_CAD_gap_detection_not_fluid_numerics_inheritance
    reference_data_validity: preserved

  - id: D8
    catalog_name: sub_mm_thin_shell
    description: "0.80 mm thick auxiliary underbody_sensor_cover_thin plate on side underbody between axles, outside the wake measurement plane."
    location:
      bodies_involved: [underbody_sensor_cover_thin]
      coordinate_system: "mm; x streamwise from vehicle nose, y lateral from centerline outward, z vertical from ground"
      approximate_coords_mm:
        x: 2480.0
        y: 686.4
        z: 155.0
      normalized_location:
        x_over_L: 0.538
        y_over_half_width: 0.78
      reference_zone_exclusion:
        on_front_wheel_housing: false
        between_front_and_rear_axles: true
        downstream_of_vehicle_tail: false
        on_rear_wake_measurement_plane: false
        on_vehicle_centerline: false
        on_underbody_primary_pressure_tap_line: false
    measurement:
      claimed_min_thickness_mm: 0.80
      verification_method: "Inspect STEP bbox thickness in z for underbody_sensor_cover_thin; expected dz = 0.80 mm."
      expected_bbox_dz_mm: 0.80
    expected_advisor_to_catch: thin_wall_advisor
    hypothesized_v_series_match: V10_style_thin_wall_patch_loss_not_fluid_numerics_inheritance
    reference_data_validity: preserved

global_reference_exclusions:
  front_wheel_housings_defect_free: true
  rear_wake_measurement_planes_defect_free: true
  centerline_symmetry_plane_defect_free: true
  Cd_Cl_Cm_validation_regions_defect_free: true
  side_mirror_primary_pressure_tap_face_defect_free: true
  rear_base_pressure_taps_defect_free: true
  no_Ahmed_body_geometry: true
```

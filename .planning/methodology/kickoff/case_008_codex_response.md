## Deliverable 1 — Engineering brief

### Component picked + bank ID
`case_008_glc305_irt_lagrangian`

Component: clean GLC305 airfoil, 305 mm chord, 2D-extruded slab, NASA Glenn Icing Research Tunnel droplet-impingement reference flavor.

Bank/source IDs:
- Coverage row: `Particle-laden / Lagrangian (icing)`
- Numerics class: `incompressible-RANS-Lagrangian`, new Pattern-6 root; inherits none of the previous numerics classes
- Source tier: Tier-1 reference-derived NASA Glenn IRT geometry
- Sources checked:
  - NASA/TM-2002-211557, GLC-305 swept airfoil IRT campaign: https://ntrs.nasa.gov/citations/20020061865
  - NASA impingement database including GLC-305: https://ntrs.nasa.gov/archive/nasa/casi.ntrs.nasa.gov/20020090796.pdf
  - NASA roughness / GlennICE geometry-condition ranges including GLC-305 and 0.305 m chord cases: https://ntrs.nasa.gov/api/citations/20230003729/downloads/Roughness_UDP%20%28003%29.pdf
- Hard exclusion honored: no NACA 0012, no Ahmed, no Sajben, no BFS, no Ercoftac mixing tank.

### Engineering question
Can the harness run a clean-airfoil IRT droplet-impingement case with `simpleFoam` first, then one-way `kinematicCloud`, and recover leading-edge collection efficiency `beta(s/c)` plus upper/lower impingement limits without corrupting the clean GLC305 reference geometry?

### Physics signature
- Solver v1: `simpleFoam` for converged steady incompressible RANS, then `kinematicCloud` one-way particle tracking
- v2 fallback: `DPMFoam` only if diagnosed particle volume fraction is non-negligible; nominal IRT `LWC/rho_water ≈ 7e-7`, so v1 should remain one-way
- Flow: `U_inf = 67 m/s`, `alpha = 4 deg`, `T_inf = 268 K`, `p_atm = 101325 Pa`
- Air: `nu_air = 1.4e-5 m2/s`, `rho_air ≈ 1.318 kg/m3`, `mu_air ≈ 1.85e-5 Pa s`
- Chord: `c = 0.305 m`
- Reynolds: `Re_c = 1.46e6` from the specified `nu_air`; nominal cold-air IRT reference target retained as `~1.8e6`
- Mach: `M ≈ 0.20`, incompressible treatment acceptable
- Droplets: `MVD = 25 um`, `LWC = 0.70 g/m3`, `rho_p = 1000 kg/m3`
- Inertia parameter: `K = rho_p * D^2 * U / (18 * mu_air * c) ≈ 0.41`
- Weber estimate: `We ≈ 2.0`; collision-only model, no thermodynamics, no ice horn input

### Parts inventory
- `airfoil_clean`: clean GLC305 wall, primary beta measurement surface; no ice horn
- `root_mount_pad`: aft/root auxiliary mounting body, participates in D1
- `root_mount_strut`: aft/root auxiliary support body, participates in D1
- `trailing_edge_tab_thin`: thin aft auxiliary tab, participates in D8
- `inlet`: particle and Eulerian velocity inlet
- `outlet`: pressure outlet
- `farfield_top`: slip/freestream top patch
- `farfield_bottom`: slip/freestream bottom patch
- `sym_plane_left`: spanwise symmetry plane
- `sym_plane_right`: spanwise symmetry plane

### Boundary conditions plan
- `inlet`: `U fixedValue (66.84 4.67 0) m/s`, `p zeroGradient`, turbulence fixed from 1% intensity; `kinematicCloud` uses `patchInjection`
- `outlet`: `p fixedValue 0`, `U inletOutlet/zeroGradient`
- `farfield_top`, `farfield_bottom`: `slip` for `U`, `p zeroGradient`; optionally `freestreamVelocity` if the harness supports it
- `sym_plane_left`, `sym_plane_right`: symmetry for Eulerian and cloud-crossing suppression
- `airfoil_clean` and auxiliary bodies: `U noSlip`, `p zeroGradient`, wall functions for RANS; particle wall interaction `stick` on `airfoil_clean` for collection accounting
- Run sequence: converge `simpleFoam`, freeze Eulerian flow field, then run `kinematicCloud` with fixed random seed and parcel subcycling

### Expected metrics
- `beta(s/c)` on `airfoil_clean` at `z/c = -0.50, 0.00, 0.50`
- Upper/lower impingement limits: `s_upper/c`, `s_lower/c`
- Peak `beta_max` and stagnation-zone `beta(0)`
- Total catch rate on `airfoil_clean`
- Parcel mass balance: injected, stuck, escaped outlet, escaped farfield
- LWC shadow region downstream of the airfoil

### Hypothesized failure modes
- Cloud dictionary generation may not support `patchInjection` from named CAD patches.
- Parcel count may be too low, making `beta(s/c)` noisy even after Eulerian convergence.
- Wall-normal angle correction `cos(theta)` may become unstable near the stagnation point.
- Particle time step or subcycling may skip near-wall impact cells at the leading edge.
- `stick` accounting may report only patch totals unless the harness adds per-face or per-band accumulation.
- Symmetry patches may incorrectly absorb or reflect parcels if not configured as non-wall boundaries.
- Restart sequencing may fail if `kinematicCloud` is launched before `simpleFoam` writes a usable final `U`.

### Defect injection summary
Exactly two defects, both outside the leading-edge beta reference zone:
- `D1`: 0.35 mm gap between `root_mount_pad` and `root_mount_strut`, at aft/root support location around `x/c = 0.72`, `z/c = -0.88`
- `D8`: 0.80 mm thick `trailing_edge_tab_thin` body just aft of the trailing edge around `x/c = 1.00`

Reference-data preservation: the clean `airfoil_clean` leading edge and the angular zone from `-10 deg` to `+30 deg` around stagnation remain defect-free.

### Sub-session estimated effort
Estimated effort: `8-12 hours`, likely 3 versions:
- v1: CAD regeneration, patch mapping, steady RANS, deterministic cloud run
- v2: parcel statistics, subcycling, and beta post-processing stabilization
- v3: beta curves, impingement limits, and final mass-balance/report extraction

## Deliverable 2 — CAD generation script
```python
#!/usr/bin/env python3
"""case_008_glc305_irt_lagrangian CAD generator.

Clean GLC305 IRT-style airfoil slab for collision-only droplet
impingement. No ice horn is present in the input CAD.

Designed by Codex per cfd-harness-unified case-design protocol.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import cadquery as cq


CASE_ID = "case_008_glc305_irt_lagrangian"
ASSEMBLY_NAME = CASE_ID
PATCH_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

# === Geometry scale ===
CHORD_MM = 305.0
SPAN_MM = 2.0 * CHORD_MM
HALF_SPAN_MM = 0.5 * SPAN_MM

# === Farfield box, consistent with NASA icing-grid practice of O(10c) bounds ===
X_MIN_MM = -10.0 * CHORD_MM
X_MAX_MM = 12.0 * CHORD_MM
Y_MIN_MM = -6.0 * CHORD_MM
Y_MAX_MM = 6.0 * CHORD_MM
PATCH_THICKNESS_MM = 10.0

# === Intentional defects ===
DEFECT_D1_GAP_MM = 0.35
TRAILING_TAB_THICKNESS_MM = 0.80

# Clean GLC305 normalized coordinate table, TE upper -> LE -> TE lower.
# Values are x/c, y/c. This is the clean baseline; no ice shape is included.
GLC305_COORDS = [
    (1.0000, 0.0012),
    (0.9500, 0.0076),
    (0.9000, 0.0135),
    (0.8500, 0.0193),
    (0.8000, 0.0252),
    (0.7500, 0.0313),
    (0.7000, 0.0375),
    (0.6500, 0.0437),
    (0.6000, 0.0498),
    (0.5500, 0.0555),
    (0.5000, 0.0608),
    (0.4500, 0.0654),
    (0.4000, 0.0691),
    (0.3500, 0.0718),
    (0.3000, 0.0731),
    (0.2500, 0.0720),
    (0.2000, 0.0678),
    (0.1600, 0.0622),
    (0.1200, 0.0542),
    (0.0900, 0.0462),
    (0.0600, 0.0353),
    (0.0400, 0.0264),
    (0.0250, 0.0185),
    (0.0125, 0.0103),
    (0.0050, 0.0041),
    (0.0000, 0.0000),
    (0.0050, -0.0049),
    (0.0125, -0.0098),
    (0.0250, -0.0155),
    (0.0400, -0.0207),
    (0.0600, -0.0262),
    (0.0900, -0.0335),
    (0.1200, -0.0390),
    (0.1600, -0.0446),
    (0.2000, -0.0482),
    (0.2500, -0.0511),
    (0.3000, -0.0522),
    (0.3500, -0.0518),
    (0.4000, -0.0501),
    (0.4500, -0.0475),
    (0.5000, -0.0441),
    (0.5500, -0.0401),
    (0.6000, -0.0357),
    (0.6500, -0.0310),
    (0.7000, -0.0262),
    (0.7500, -0.0212),
    (0.8000, -0.0163),
    (0.8500, -0.0116),
    (0.9000, -0.0074),
    (0.9500, -0.0038),
    (1.0000, -0.0012),
]

PART_NAMES = [
    "airfoil_clean",
    "root_mount_pad",
    "root_mount_strut",
    "trailing_edge_tab_thin",
    "inlet",
    "outlet",
    "farfield_top",
    "farfield_bottom",
    "sym_plane_left",
    "sym_plane_right",
]


def validate_names() -> None:
    seen = set()
    for name in PART_NAMES:
        if not PATCH_NAME_RE.match(name):
            raise ValueError(f"Invalid OpenFOAM patch/body name: {name}")
        if name in seen:
            raise ValueError(f"Duplicate body name: {name}")
        seen.add(name)


def make_box(center: tuple[float, float, float], size: tuple[float, float, float]) -> cq.Shape:
    return cq.Workplane("XY", origin=center).box(size[0], size[1], size[2], centered=True).val()


def build_airfoil_clean() -> cq.Shape:
    pts = [(x * CHORD_MM, y * CHORD_MM) for x, y in GLC305_COORDS]
    # A single clean closed airfoil section is extruded spanwise for the 2D slab.
    return cq.Workplane("XY").spline(pts).close().extrude(SPAN_MM, both=True).val()


def build_auxiliary_defects() -> dict[str, cq.Shape]:
    # D1: support pad and strut are intended to mate but have a controlled 0.35 mm vertical gap.
    pad_center = (0.72 * CHORD_MM, -0.105 * CHORD_MM, -0.88 * HALF_SPAN_MM)
    pad_size = (55.0, 8.0, 20.0)
    pad_bottom_y = pad_center[1] - 0.5 * pad_size[1]

    strut_size = (38.0, 14.0, 16.0)
    strut_top_y = pad_bottom_y - DEFECT_D1_GAP_MM
    strut_center = (pad_center[0], strut_top_y - 0.5 * strut_size[1], pad_center[2])

    # D8: sub-mm trailing-edge auxiliary tab, safely outside the LE impingement measurement zone.
    trailing_tab = make_box(
        center=(CHORD_MM + 0.5 * TRAILING_TAB_THICKNESS_MM, -0.012 * CHORD_MM, 0.0),
        size=(TRAILING_TAB_THICKNESS_MM, 9.0, 0.70 * SPAN_MM),
    )

    return {
        "root_mount_pad": make_box(pad_center, pad_size),
        "root_mount_strut": make_box(strut_center, strut_size),
        "trailing_edge_tab_thin": trailing_tab,
    }


def build_domain_patches() -> dict[str, cq.Shape]:
    x_mid = 0.5 * (X_MIN_MM + X_MAX_MM)
    x_len = X_MAX_MM - X_MIN_MM
    y_mid = 0.5 * (Y_MIN_MM + Y_MAX_MM)
    y_len = Y_MAX_MM - Y_MIN_MM
    z_len = SPAN_MM

    return {
        "inlet": make_box(
            center=(X_MIN_MM, y_mid, 0.0),
            size=(PATCH_THICKNESS_MM, y_len, z_len),
        ),
        "outlet": make_box(
            center=(X_MAX_MM, y_mid, 0.0),
            size=(PATCH_THICKNESS_MM, y_len, z_len),
        ),
        "farfield_top": make_box(
            center=(x_mid, Y_MAX_MM, 0.0),
            size=(x_len, PATCH_THICKNESS_MM, z_len),
        ),
        "farfield_bottom": make_box(
            center=(x_mid, Y_MIN_MM, 0.0),
            size=(x_len, PATCH_THICKNESS_MM, z_len),
        ),
        "sym_plane_left": make_box(
            center=(x_mid, y_mid, -HALF_SPAN_MM),
            size=(x_len, y_len, PATCH_THICKNESS_MM),
        ),
        "sym_plane_right": make_box(
            center=(x_mid, y_mid, HALF_SPAN_MM),
            size=(x_len, y_len, PATCH_THICKNESS_MM),
        ),
    }


def build() -> cq.Assembly:
    validate_names()

    parts: dict[str, cq.Shape] = {"airfoil_clean": build_airfoil_clean()}
    parts.update(build_auxiliary_defects())
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
/Users/Zhuanz/Desktop/case_008_glc305_irt_lagrangian/inputs/cad_codex_v1.step

## Deliverable 4 — Parts manifest
```yaml
case_id: case_008_glc305_irt_lagrangian
cad_source:
  tier: tier1_reference_derived
  name: NASA Glenn IRT GLC305 clean airfoil
  source_urls:
    - https://ntrs.nasa.gov/citations/20020061865
    - https://ntrs.nasa.gov/archive/nasa/casi.ntrs.nasa.gov/20020090796.pdf
    - https://ntrs.nasa.gov/api/citations/20230003729/downloads/Roughness_UDP%20%28003%29.pdf
  license_assessment: "NASA public-use references checked; this deliverable provides a deterministic generator and does not redistribute a binary STEP."
  fallback_not_used:
    - NACA23012
    - other_NASA_Glenn_IRT_airfoil
  hard_exclusion_honored: NACA0012_not_used
generation_script: scripts/build_cad.py
step_file: inputs/cad_codex_v1.step
units_in_step: mm
solver:
  eulerian_v1: simpleFoam
  lagrangian_v1: kinematicCloud
  coupling: one_way_particles_follow_converged_eulerian_flow
  v2_fallback: DPMFoam_only_if_particle_volume_fraction_non_negligible
numerics_class: incompressible-RANS-Lagrangian

freestream:
  U_inf: 67.0
  alpha_deg: 4.0
  U_vector_mps: [66.84, 4.67, 0.0]
  T_inf: 268.0
  p_atm: 101325.0
  nu_air: 1.4e-5
  rho_air_ideal_gas: 1.318
  mu_air_from_nu_rho: 1.85e-5
  chord_m: 0.305
  span_m: 0.610
  MVD: 25.0e-6
  LWC: 0.00070
  LWC_units_note: "0.00070 kg/m3 = 0.70 g/m3"
  particle_density: 1000.0
  particle_volume_fraction: 7.0e-7
  Mach_approx: 0.20

dimensionless_groups:
  Re_chord_from_specified_nu: 1.46e6
  Re_chord_nominal_IRT_reference: 1.8e6
  K_inertia_parameter: 0.41
  Stokes_chord: 0.41
  Weber_droplet: 2.0
  particle_relaxation_time_s: 0.00188
  freestream_particle_mass_flux: 0.0469

lagrangian_cloud:
  cloud_name: kinematicCloud
  run_sequence:
    - simpleFoam_to_steady_convergence
    - freeze_eulerian_U_p_nut_fields
    - kinematicCloud_one_way_tracking
  injection_model: patchInjection
  source_patch: inlet
  injection_direction: freestream_aligned
  particle_properties:
    LWC: 0.00070
    LWC_units_note: "kg/m3"
    MVD: 25.0e-6
    diameter_distribution: fixedValue
    density: 1000.0
    material: liquid_water
  parcel_controls:
    random_seed: 8008
    max_parcels_per_second: 100000
    parcel_basis: mass_flow_rate_from_LWC_times_inlet_area
    tracking_duration_s: 0.25
    subcycle: true
    max_Co_particle: 0.20
  drag_model: sphereDrag
  particle_force_models:
    - sphereDrag
    - pressureGradient_optional_off_for_v1
    - gravity_disabled_for_horizontal_IRT_v1
  dispersion_model: none_v1
  turbulent_dispersion_v2: stochasticDispersionRAS
  particle_wall_interaction:
    model: stick
    collection_patches:
      - airfoil_clean
    non_collection_walls:
      - root_mount_pad
      - root_mount_strut
      - trailing_edge_tab_thin
    escape_patches:
      - outlet
      - farfield_top
      - farfield_bottom
    symmetry_patches:
      - sym_plane_left
      - sym_plane_right

collection_efficiency:
  definition: "beta = particle_mass_flux_at_surface / (freestream_particle_mass_flux * cos(theta))"
  primary_surface: airfoil_clean
  measurement_strategy: "surface-integral bands on clean airfoil at spanwise stations; no CAD defects in LE band"
  spanwise_stations_z_over_c: [-0.50, 0.00, 0.50]
  surface_coordinate: "s/c from stagnation point; upper surface positive, lower surface negative"
  leading_edge_measurement_zone:
    angle_deg_around_stagnation: [-10.0, 30.0]
    x_over_c_approx: [0.0, 0.12]
    defect_free: true
  bins:
    s_over_c_min: -0.20
    s_over_c_max: 0.30
    bin_width_s_over_c: 0.005
  reported_metrics:
    - beta_s_over_c_curve_each_station
    - beta_max_each_station
    - s_upper_impingement_limit
    - s_lower_impingement_limit
    - total_catch_rate_airfoil_clean
    - parcel_mass_balance

parts:
  - name: airfoil_clean
    role: wall_airfoil_reference
    include_in_reference_metrics: true
    defect_free_le_zone: true
    bc:
      U: noSlip
      p: zeroGradient
      nut: nutkWallFunction
      k: kqRWallFunction
      omega: omegaWallFunction
      particle_wall: stick
    notes: "Clean GLC305 baseline; no ice horn, no LE defects."

  - name: root_mount_pad
    role: wall_auxiliary_root_mount
    defect_participation: [D1]
    include_in_reference_metrics: false
    bc:
      U: noSlip
      p: zeroGradient
      particle_wall: escape_or_ignore_for_beta

  - name: root_mount_strut
    role: wall_auxiliary_root_mount
    defect_participation: [D1]
    include_in_reference_metrics: false
    bc:
      U: noSlip
      p: zeroGradient
      particle_wall: escape_or_ignore_for_beta

  - name: trailing_edge_tab_thin
    role: wall_auxiliary_trailing_edge_thin
    defect_participation: [D8]
    include_in_reference_metrics: false
    bc:
      U: noSlip
      p: zeroGradient
      particle_wall: escape_or_ignore_for_beta

  - name: inlet
    role: velocity_inlet_and_particle_injection
    bc:
      U:
        type: fixedValue
        value: [66.84, 4.67, 0.0]
      p: zeroGradient
      cloud: patchInjection

  - name: outlet
    role: pressure_outlet
    bc:
      U: inletOutlet
      p:
        type: fixedValue
        value: 0.0
      cloud: escape

  - name: farfield_top
    role: farfield_slip
    bc:
      U: slip
      p: zeroGradient
      cloud: escape

  - name: farfield_bottom
    role: farfield_slip
    bc:
      U: slip
      p: zeroGradient
      cloud: escape

  - name: sym_plane_left
    role: symmetry
    bc:
      U: symmetry
      p: symmetry
      cloud: symmetry

  - name: sym_plane_right
    role: symmetry
    bc:
      U: symmetry
      p: symmetry
      cloud: symmetry

patch_naming_check:
  regex: "^[A-Za-z][A-Za-z0-9_]*$"
  all_names_match: true
  no_duplicate_names: true
  no_spaces_or_hyphens: true

reference_data_preservation:
  clean_airfoil_no_ice_horn: true
  leading_edge_beta_zone_defect_free: true
  no_defects_between_minus10_and_plus30_deg_around_stagnation: true
  defects_restricted_to:
    - aft_root_mount
    - trailing_edge_auxiliary_tab
```

## Deliverable 5 — Defect manifest
```yaml
case_id: case_008_glc305_irt_lagrangian
defect_count: 2
defects:
  - id: D1
    catalog_name: sub_mm_gap_between_bodies
    description: "0.35 mm vertical gap between root_mount_pad and root_mount_strut in the aft/root support hardware."
    location:
      bodies_involved: [root_mount_pad, root_mount_strut]
      coordinate_system: "mm; x chordwise from LE, y airfoil-normal/up, z spanwise"
      approximate_coords_mm:
        x: 219.6
        y: -36.4
        z: -268.4
      normalized_location:
        x_over_c: 0.72
        z_over_c: -0.88
      reference_zone_exclusion:
        on_airfoil_clean: false
        on_le_beta_zone: false
        angle_deg_around_stagnation: outside_minus10_to_plus30
    measurement:
      claimed_gap_mm: 0.35
      verification_method: "Import STEP in FreeCAD and compute root_mount_pad.Shape.distToShape(root_mount_strut.Shape)."
      expected_min_distance_mm: 0.35
    expected_advisor_to_catch: virtual_interface_detector
    hypothesized_v_series_match: new_Lagrangian_CAD_gap_or_V2_style_virtual_interface
    reference_data_validity: preserved

  - id: D8
    catalog_name: sub_mm_thin_shell
    description: "0.80 mm thick auxiliary trailing_edge_tab_thin body just aft of the airfoil trailing edge."
    location:
      bodies_involved: [trailing_edge_tab_thin]
      coordinate_system: "mm; x chordwise from LE, y airfoil-normal/up, z spanwise"
      approximate_coords_mm:
        x: 305.4
        y: -3.7
        z: 0.0
      normalized_location:
        x_over_c: 1.00
        z_over_c: 0.0
      reference_zone_exclusion:
        on_le_beta_zone: false
        downstream_of_le_measurement_zone: true
        angle_deg_around_stagnation: outside_minus10_to_plus30
    measurement:
      claimed_min_thickness_mm: 0.80
      verification_method: "Inspect STEP bbox thickness in x for trailing_edge_tab_thin; expected dx = 0.80 mm."
      expected_bbox_dx_mm: 0.80
    expected_advisor_to_catch: thin_wall_advisor
    hypothesized_v_series_match: V10_or_new_Lagrangian_thin_wall_patch_loss
    reference_data_validity: preserved

global_reference_exclusions:
  airfoil_clean_le_zone_defect_free: true
  no_ice_horn_in_input_geometry: true
  beta_measurement_zone_minus10_to_plus30_deg_defect_free: true
  defects_not_used_for_collection_efficiency: true
```

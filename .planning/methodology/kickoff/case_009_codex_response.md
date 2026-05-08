## Deliverable 1 — Engineering brief

### Component picked + bank ID
`case_009_sandia_flame_d`

Component: Sandia/TUD Flame D piloted CH4/air jet flame, 2D axisymmetric 5 degree wedge.

Bank/source IDs:
- Coverage row: `reacting-low-Mach / combustion`
- Component bank extension: `R1_sandia_tnf_piloted_jet_flame`
- Numerics class: `reacting-low-Mach`, new Pattern-6 root; inherits none of the prior fluid-internal V-series numerics findings
- Source tier: Tier-1 reference-derived TNF Workshop benchmark
- Sources checked:
  - https://tnfworkshop.org/data-archives/pilotedjet/ch4-air/
  - https://tnfworkshop.org/data-archives/pilotedjet/
- Source data used: D=7.2 mm fuel jet, 18.2 mm pilot diameter, Flame D `Re_jet=22400`, main jet 25% CH4 / 75% air by volume, TNF scalar stations and reference species list.
- License assessment: public TNF Workshop archive used as reference; this deliverable does not redistribute binary geometry or data.

### Engineering question
Can the harness configure a first reacting low-Mach OpenFOAM case and recover Sandia Flame D radial profiles of mixture fraction `Z(r,z)`, temperature `T(r,z)`, and `CH4 / CO2 / H2O / O2 / OH` against Barlow and Frank Raman/Rayleigh/LIF data at the published stations?

### Physics signature
- Solver v1: `reactingFoam`
- v1 alternate: `rhoReactingFoam` only if density/pressure coupling above the flame forces compressible treatment
- v2 fallback: `reactingPimpleFoam` transient RANS if startup stiffness or pseudo-steady oscillation dominates
- Geometry: vertical axisymmetric 5 degree wedge, one azimuthal cell, axial length `80D = 576 mm`, radial far side `r = 250 mm`
- Regime: turbulent buoyancy-modulated nonpremixed diffusion flame with piloted stabilization
- Main jet: `D = 7.2 mm`, `U = 49.6 m/s`, `T = 294 K`, `Re_jet = 22400`, `Mach ≈ 0.14`
- Pilot annulus: `D_inner = 7.7 mm`, `D_outer = 18.2 mm`, `U = 11.4 m/s`, `T = 1880 K`
- Coflow: air, `D_outer = 240 mm`, `U = 0.9 m/s`, `T = 291 K`
- Stoichiometric mixture fraction: `Z_st = 0.351`
- Equivalence-ratio profile: computed from `phi(Z)=Z*(1-Z_st)/(Z_st*(1-Z))`; report `phi(r,z)` at each reference station
- Damkohler reporting: compute `Da = tau_mix / tau_chem` on or near the `Z=Z_st` contour; expected near-stoichiometric Flame D behavior is order `1-10`, with low local-extinction probability
- Expected visible/stoichiometric flame length: `L_vis ≈ 67D = 482 mm`; target outlet at `80D` keeps the flame inside the domain
- Buoyancy: vertical jet upward, gravity downward; buoyancy modulation becomes important downstream, especially `z/D > 30`

### Parts inventory
- `fuel_jet`: central inlet, `0 <= r <= 3.6 mm`
- `fuel_nozzle_lip`: thin wall between fuel jet and pilot annulus
- `pilot_annulus`: hot pilot-product inlet, `3.85 <= r <= 9.1 mm`
- `pilot_housing_exterior`: pilot outer sleeve / burner wall, no reference-data defect
- `coflow_air`: coflow inlet, `9.45 <= r <= 120 mm`
- `burner_base_wall`: ground/base wall outside the coflow inlet
- `wedge_front`: wedge boundary plane, OpenFOAM `wedge`
- `wedge_back`: wedge boundary plane, OpenFOAM `wedge`
- `outer_side`: radial farfield at `r = 250 mm`
- `far_outlet`: outlet at `z = 80D`
- `coflow_plenum_mount_bracket`: exterior mounting bracket, participates in D1
- `coflow_plenum_mount_shim`: exterior shim, participates in D1
- `bracket_lip_thin`: exterior thin lip, participates in D8

### Boundary conditions plan
- `fuel_jet`: fixed axial velocity `49.6 m/s`, fixed `T=294 K`, fixed species for rich CH4/air stream
- `pilot_annulus`: fixed axial velocity `11.4 m/s`, fixed `T=1880 K`, fixed hot product species with trace radicals for flame stabilization
- `coflow_air`: fixed axial velocity `0.9 m/s`, fixed `T=291 K`, fixed air species
- `far_outlet`: pressure outlet, zero-gradient flow/scalars
- `outer_side`: freestream / pressure-inlet-outlet side boundary with air fallback; slip fallback allowed
- `wedge_front`, `wedge_back`: `wedge` for `U`, `p`, `T`, turbulence, and all species
- Solid burner and exterior bodies: no-slip adiabatic walls for v1; exterior bracket bodies may be excluded from fluid reference metrics

### Expected metrics
- Mean and RMS `Z(r,z)` at `z/D = 7.5, 15, 30, 45, 60`
- Mean and RMS `T(r,z)` at the same five stations
- Species profiles: `CH4`, `O2`, `CO2`, `H2O`, `OH`; optional `CO`, `H2`, `NO` if mechanism/post-processing supports them
- Stoichiometric contour closure length `L_st/D`
- OH-based flame brush and heat-release peak location
- Lift-off height: expected zero / anchored; report any OH detachment from pilot zone
- Elemental mass conservation and species boundedness
- Solver health: chemistry subcycling, max heat-release rate, temperature bounds, Courant number, and PaSR sensitivity

### Hypothesized failure modes
- Chemkin-to-OpenFOAM conversion may mismatch species names, thermo, or transport data.
- BC writer may not create all species files consistently across fuel, pilot, coflow, wedge, wall, outlet, and farfield patches.
- Hot pilot products plus finite-rate chemistry may create first-step temperature or heat-release spikes.
- PaSR `Cmix` and turbulent Schmidt number sensitivity may dominate `OH` and `T` near `Z_st`.
- Neglecting radiation in v1 may overpredict downstream temperature.
- Bilger mixture-fraction reconstruction can be wrong if elemental weights or pilot-product species are omitted.
- Transient reacting startup may need staged chemistry: cold-flow initialization, then chemistry enabled.

### Defect injection summary
Exactly two defects, both outside the published flame measurement stations:
- `D1`: 0.35 mm gap between `coflow_plenum_mount_bracket` and `coflow_plenum_mount_shim`, below the inlet plane.
- `D8`: 0.80 mm thin `bracket_lip_thin` exterior sheet on the coflow plenum bracket.

Reference-data validity: preserved. No defect intersects `z/D = 7.5, 15, 30, 45, 60`, the fuel jet, pilot annulus, coflow inlet, stoichiometric flame region, or radial Raman/Rayleigh profile lines.

### Sub-session estimated effort
Estimated effort: `12-16 hours`, likely 4 versions:
- v1: CAD regeneration, wedge mesh, species BC generation, reduced chemistry wiring
- v2: cold-flow initialization and reacting startup stabilization
- v3: PaSR/Schmidt/radiation sensitivity and profile extraction
- v4: TNF profile comparison and final reporting

## Deliverable 2 — CAD generation script
```python
#!/usr/bin/env python3
"""case_009_sandia_flame_d CAD generator.

Reference-derived 2D axisymmetric wedge for Sandia/TUD Flame D.
Designed by Codex per cfd-harness-unified case-design protocol.
"""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path

import cadquery as cq


CASE_ID = "case_009_sandia_flame_d"
ASSEMBLY_NAME = CASE_ID
PATCH_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

# === Flame D published dimensions ===
D_JET_MM = 7.2
FUEL_RADIUS_MM = 0.5 * D_JET_MM
PILOT_INNER_RADIUS_MM = 0.5 * 7.7
PILOT_OUTER_RADIUS_MM = 0.5 * 18.2
BURNER_OUTER_RADIUS_MM = 0.5 * 18.9
COFLOW_RADIUS_MM = 0.5 * 240.0

# === 2D axisymmetric wedge domain ===
WEDGE_ANGLE_DEG = 5.0
HALF_WEDGE_DEG = 0.5 * WEDGE_ANGLE_DEG
DOMAIN_LENGTH_MM = 80.0 * D_JET_MM
DOMAIN_RADIUS_MM = 250.0
PATCH_THICKNESS_MM = 0.40
PILOT_SLEEVE_HEIGHT_MM = 4.0

# === Intentional exterior defects; below z=0 so TNF profiles remain untouched ===
DEFECT_D1_GAP_MM = 0.35
BRACKET_CENTER_R_MM = 180.0
BRACKET_CENTER_Z_MM = -11.0
BRACKET_SIZE_MM = (46.0, 3.0, 8.0)
SHIM_SIZE_MM = (34.0, 3.0, 4.0)
BRACKET_LIP_THICKNESS_MM = 0.80

PART_NAMES = [
    "fuel_jet",
    "fuel_nozzle_lip",
    "pilot_annulus",
    "pilot_housing_exterior",
    "coflow_air",
    "burner_base_wall",
    "wedge_front",
    "wedge_back",
    "outer_side",
    "far_outlet",
    "coflow_plenum_mount_bracket",
    "coflow_plenum_mount_shim",
    "bracket_lip_thin",
]


def validate_names() -> None:
    seen: set[str] = set()
    for name in PART_NAMES:
        if not PATCH_NAME_RE.match(name):
            raise ValueError(f"Invalid OpenFOAM patch/body name: {name}")
        if name in seen:
            raise ValueError(f"Duplicate body name: {name}")
        seen.add(name)


def sector_solid(r_inner: float, r_outer: float, z_min: float, z_max: float) -> cq.Shape:
    """Create an annular 5 degree sector extruded along the burner axis."""
    if r_inner < 0.0 or r_outer <= r_inner:
        raise ValueError("Invalid sector radii")
    height = z_max - z_min
    if height <= 0.0:
        raise ValueError("Invalid sector height")

    a = math.radians(HALF_WEDGE_DEG)
    co = math.cos(a)
    si = math.sin(a)

    outer_low = (r_outer * co, -r_outer * si)
    outer_mid = (r_outer, 0.0)
    outer_high = (r_outer * co, r_outer * si)

    wp = cq.Workplane("XY", origin=(0.0, 0.0, z_min))

    if r_inner == 0.0:
        return (
            wp.moveTo(0.0, 0.0)
            .lineTo(*outer_low)
            .threePointArc(outer_mid, outer_high)
            .close()
            .extrude(height)
            .val()
        )

    inner_low = (r_inner * co, -r_inner * si)
    inner_mid = (r_inner, 0.0)
    inner_high = (r_inner * co, r_inner * si)

    return (
        wp.moveTo(*inner_low)
        .lineTo(*outer_low)
        .threePointArc(outer_mid, outer_high)
        .lineTo(*inner_high)
        .threePointArc(inner_mid, inner_low)
        .close()
        .extrude(height)
        .val()
    )


def make_box(center: tuple[float, float, float], size: tuple[float, float, float]) -> cq.Shape:
    return cq.Workplane("XY", origin=center).box(size[0], size[1], size[2], centered=True).val()


def wedge_plane(angle_deg: float) -> cq.Shape:
    # Thin radial-axial panel marking one OpenFOAM wedge boundary.
    panel = make_box(
        center=(0.5 * DOMAIN_RADIUS_MM, 0.0, 0.5 * DOMAIN_LENGTH_MM),
        size=(DOMAIN_RADIUS_MM, PATCH_THICKNESS_MM, DOMAIN_LENGTH_MM),
    )
    return panel.rotate((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), angle_deg)


def build_inlet_and_domain_patches() -> dict[str, cq.Shape]:
    return {
        "fuel_jet": sector_solid(0.0, FUEL_RADIUS_MM, -PATCH_THICKNESS_MM, 0.0),
        "fuel_nozzle_lip": sector_solid(
            FUEL_RADIUS_MM, PILOT_INNER_RADIUS_MM, -PATCH_THICKNESS_MM, 0.0
        ),
        "pilot_annulus": sector_solid(
            PILOT_INNER_RADIUS_MM, PILOT_OUTER_RADIUS_MM, -PATCH_THICKNESS_MM, 0.0
        ),
        "pilot_housing_exterior": sector_solid(
            PILOT_OUTER_RADIUS_MM, BURNER_OUTER_RADIUS_MM, -PATCH_THICKNESS_MM, PILOT_SLEEVE_HEIGHT_MM
        ),
        "coflow_air": sector_solid(
            BURNER_OUTER_RADIUS_MM, COFLOW_RADIUS_MM, -PATCH_THICKNESS_MM, 0.0
        ),
        "burner_base_wall": sector_solid(
            COFLOW_RADIUS_MM, DOMAIN_RADIUS_MM, -PATCH_THICKNESS_MM, 0.0
        ),
        "wedge_front": wedge_plane(HALF_WEDGE_DEG),
        "wedge_back": wedge_plane(-HALF_WEDGE_DEG),
        "outer_side": sector_solid(
            DOMAIN_RADIUS_MM - PATCH_THICKNESS_MM, DOMAIN_RADIUS_MM, 0.0, DOMAIN_LENGTH_MM
        ),
        "far_outlet": sector_solid(
            0.0, DOMAIN_RADIUS_MM, DOMAIN_LENGTH_MM, DOMAIN_LENGTH_MM + PATCH_THICKNESS_MM
        ),
    }


def build_defect_bodies() -> dict[str, cq.Shape]:
    # D1: bracket and shim are intended to mate but have a controlled 0.35 mm axial gap.
    bracket = make_box(
        center=(BRACKET_CENTER_R_MM, 0.0, BRACKET_CENTER_Z_MM),
        size=BRACKET_SIZE_MM,
    )
    bracket_top_z = BRACKET_CENTER_Z_MM + 0.5 * BRACKET_SIZE_MM[2]
    shim_bottom_z = bracket_top_z + DEFECT_D1_GAP_MM
    shim_center_z = shim_bottom_z + 0.5 * SHIM_SIZE_MM[2]
    shim = make_box(
        center=(BRACKET_CENTER_R_MM, 0.0, shim_center_z),
        size=SHIM_SIZE_MM,
    )

    # D8: sub-mm thin exterior lip on the coflow plenum bracket.
    lip = make_box(
        center=(BRACKET_CENTER_R_MM + 32.0, 0.0, BRACKET_CENTER_Z_MM - 1.5),
        size=(36.0, BRACKET_LIP_THICKNESS_MM, 10.0),
    )

    return {
        "coflow_plenum_mount_bracket": bracket,
        "coflow_plenum_mount_shim": shim,
        "bracket_lip_thin": lip,
    }


def build() -> cq.Assembly:
    validate_names()

    parts: dict[str, cq.Shape] = {}
    parts.update(build_inlet_and_domain_patches())
    parts.update(build_defect_bodies())

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
/Users/Zhuanz/Desktop/case_009_sandia_flame_d/inputs/cad_codex_v1.step

## Deliverable 4 — Parts manifest
```yaml
case_id: case_009_sandia_flame_d
cad_source:
  tier: tier1_reference_derived
  name: Sandia_TUD_Flame_D_TNF_Workshop
  source_urls:
    - https://tnfworkshop.org/data-archives/pilotedjet/ch4-air/
    - https://tnfworkshop.org/data-archives/pilotedjet/
  source_data_release: "TNF Sandia/TUD Piloted CH4/Air Jet Flames, Data Release 2.0, January 2003"
  geometry_basis: "published burner dimensions reconstructed by deterministic CadQuery script"
  binary_source_geometry_redistributed: false
generation_script: scripts/build_cad.py
step_file: inputs/cad_codex_v1.step
units_in_step: mm
numerics_class: reacting-low-Mach
solver:
  v1: reactingFoam
  v1_alternate: rhoReactingFoam_if_density_coupling_requires_it
  v2_fallback: reactingPimpleFoam
  model_scope: steady_piloted_reacting_case_no_ignition_transient
  dimensionality: axisymmetric_5deg_wedge_single_azimuthal_cell

geometry:
  fuel_jet_diameter_mm: 7.2
  pilot_annulus_inner_diameter_mm: 7.7
  pilot_annulus_outer_diameter_mm: 18.2
  burner_outer_diameter_mm: 18.9
  coflow_outer_diameter_mm: 240.0
  domain_radius_mm: 250.0
  domain_length_mm: 576.0
  domain_length_over_D: 80.0
  wedge_angle_deg: 5.0
  axial_coordinate: z_positive_upward
  radial_coordinate: r_from_burner_axis

combustion:
  primary_mechanism:
    name: DRM19
    class: reduced_methane_air_mechanism
    expected_species_count: 19_active_species_plus_inerts_as_supplied
    expected_reaction_count: 84
    chemkin_files:
      chemistry: constant/chemistry/DRM19/chem.inp
      thermo: constant/chemistry/DRM19/therm.dat
      transport: constant/chemistry/DRM19/tran.dat
    openfoam_conversion_target: constant/reactions
  fallback_mechanism:
    name: westbrook_dryer_2step
    chemkin_files:
      chemistry: constant/chemistry/westbrook_dryer_2step/chem.inp
      thermo: constant/chemistry/westbrook_dryer_2step/therm.dat
      transport: constant/chemistry/westbrook_dryer_2step/tran.dat
    reactions:
      - "CH4 + 1.5 O2 => CO + 2 H2O"
      - "CO + 0.5 O2 => CO2"
  thermo_type:
    type: hePsiThermo
    mixture: reactingMixture
    transport: sutherland
    thermo: janaf
    equationOfState: perfectGas
    specie: specie
    energy: sensibleEnthalpy
  turbulence_chemistry_interaction:
    model: PaSR
    Cmix: 1.0
    v2_alternate: EDC
  turbulence_model_v1: kEpsilon
  molecular_diffusion:
    Schmidt_number: 0.7
    turbulent_Schmidt_number: 0.7
  radiation:
    v1: off
    v2_if_temperature_overpredicted: opticallyThin
  chemistry_startup:
    recommended_sequence:
      - cold_flow_without_reactions
      - enable_chemistry_with_small_deltaT
      - ramp_to_nominal_time_step

gravity:
  vector_mps2: [0.0, 0.0, -9.81]
  note: "vertical flame axis z is positive upward; buoyancy is important downstream, especially z/D > 30"

species_inflow:
  fuel_jet:
    role: central_rich_methane_air_stream
    U_mps: [0.0, 0.0, 49.6]
    T_K: 294.0
    pressure_atm_reference: 0.993
    mass_fractions:
      CH4: 0.156
      O2: 0.195808
      N2: 0.648192
    air_mass_fraction_total: 0.844
    unspecified_species: 0.0

  pilot_annulus:
    role: hot_pilot_product_stream
    U_mps: [0.0, 0.0, 11.4]
    T_K: 1880.0
    composition_note: "equilibrium-product seed for stoichiometric methane-air products with small radical stabilization traces"
    mass_fractions:
      CO2: 0.1100
      H2O: 0.0980
      O2: 0.0550
      N2: 0.73449999
      CO: 0.0010
      H2: 0.0005
      OH: 0.0010
      CH: 1.0e-8
    unspecified_species: 0.0

  coflow_air:
    role: low_speed_air_coflow
    U_mps: [0.0, 0.0, 0.9]
    T_K: 291.0
    mass_fractions:
      O2: 0.232
      N2: 0.768
    unspecified_species: 0.0

reference_data:
  dataset: Barlow_Frank_Sandia_Flame_D_TNF
  url: https://tnfworkshop.org/data-archives/pilotedjet/ch4-air/
  scalar_archive: pmCDEF.zip
  long_records_archive: LongRecordsFlameD.zip
  velocity_archive: TUD_LDV_DEF.zip
  measured_scalars:
    - mixture_fraction
    - T
    - N2
    - O2
    - CH4
    - CO2
    - H2O
    - H2
    - CO
    - OH
    - NO
  radial_profile_stations_z_over_D: [7.5, 15.0, 30.0, 45.0, 60.0]
  radial_profile_stations_z_mm: [54.0, 108.0, 216.0, 324.0, 432.0]
  axial_domain_limit_z_over_D: 80.0
  measurement_station_preservation:
    defect_free: true
    no_defect_bodies_at_z_over_D: [7.5, 15.0, 30.0, 45.0, 60.0]
    no_defects_in_fuel_jet: true
    no_defects_in_pilot_annulus: true
    no_defects_in_coflow_inlet: true
    no_defects_on_stoichiometric_flame_core: true

dimensionless_groups:
  Re_jet: 22400
  Mach_jet_approx: 0.14
  Z_st: 0.351
  central_stream_equivalence_ratio_rich_limit: 3.17
  equivalence_ratio_profile:
    formula: "phi(Z)=Z*(1-Z_st)/(Z_st*(1-Z))"
    report_at_z_over_D: [7.5, 15.0, 30.0, 45.0, 60.0]
    report_items:
      - phi_radial_profile
      - radius_where_phi_equals_1
      - stoichiometric_contour_length
  Damkohler_number:
    definition: "Da = tau_mix / tau_chem evaluated near Z = Z_st"
    expected_order_near_stoich: "1_to_10"
    report_items:
      - Da_on_stoichiometric_contour
      - min_Da_near_local_extinction_pockets
  flame_length:
    expected_L_vis_over_D: 67.0
    expected_L_vis_mm: 482.4
    outlet_margin_over_D: 13.0

parts:
  - name: fuel_jet
    role: reacting_inlet_fuel_jet
    bc:
      U: fixedValue
      T: fixedValue
      species: fixedValue
      p: zeroGradient

  - name: fuel_nozzle_lip
    role: wall_nozzle_lip
    bc:
      U: noSlip
      T: zeroGradient
      species: zeroGradient
      p: zeroGradient

  - name: pilot_annulus
    role: reacting_inlet_hot_pilot
    bc:
      U: fixedValue
      T: fixedValue
      species: fixedValue
      p: zeroGradient

  - name: pilot_housing_exterior
    role: wall_pilot_outer_sleeve
    include_in_reference_metrics: false
    bc:
      U: noSlip
      T: zeroGradient
      species: zeroGradient
      p: zeroGradient

  - name: coflow_air
    role: reacting_inlet_coflow_air
    bc:
      U: fixedValue
      T: fixedValue
      species: fixedValue
      p: zeroGradient

  - name: burner_base_wall
    role: wall_ground_base
    include_in_reference_metrics: false
    bc:
      U: noSlip
      T: zeroGradient
      species: zeroGradient
      p: zeroGradient

  - name: wedge_front
    role: wedge_plane
    bc:
      U: wedge
      p: wedge
      T: wedge
      species: wedge
      turbulence: wedge

  - name: wedge_back
    role: wedge_plane
    bc:
      U: wedge
      p: wedge
      T: wedge
      species: wedge
      turbulence: wedge

  - name: outer_side
    role: radial_farfield
    bc:
      U: pressureInletOutletVelocity
      p: totalPressure
      T: inletOutlet_air_291K
      species: inletOutlet_air
      fallback: slip

  - name: far_outlet
    role: pressure_outlet
    bc:
      U: zeroGradient
      p:
        type: fixedValue
        value: 0.0
      T: zeroGradient
      species: zeroGradient

  - name: coflow_plenum_mount_bracket
    role: exterior_mount_defect_body
    defect_participation: [D1]
    include_in_reference_metrics: false
    bc: exclude_from_fluid_reference_or_external_wall_if_meshed

  - name: coflow_plenum_mount_shim
    role: exterior_mount_defect_body
    defect_participation: [D1]
    include_in_reference_metrics: false
    bc: exclude_from_fluid_reference_or_external_wall_if_meshed

  - name: bracket_lip_thin
    role: exterior_thin_shell_defect_body
    defect_participation: [D8]
    include_in_reference_metrics: false
    bc: exclude_from_fluid_reference_or_external_wall_if_meshed

patch_naming_check:
  regex: "^[A-Za-z][A-Za-z0-9_]*$"
  all_names_match: true
  no_duplicate_names: true
  no_spaces_or_hyphens: true

reference_data_preservation:
  published_Z_T_species_profiles_preserved: true
  defect_locations: exterior_below_inlet_plane_only
  measurement_stations_mesh_clean: true
```

## Deliverable 5 — Defect manifest
```yaml
case_id: case_009_sandia_flame_d
defect_count: 2
defects:
  - id: D1
    catalog_name: sub_mm_gap_between_bodies
    description: "0.35 mm axial gap between coflow_plenum_mount_bracket and coflow_plenum_mount_shim on the exterior coflow-plenum mount below the inlet plane."
    location:
      bodies_involved: [coflow_plenum_mount_bracket, coflow_plenum_mount_shim]
      coordinate_system: "mm; z is axial/upward, r represented by x at wedge mid-plane"
      approximate_coords_mm:
        x: 180.0
        y: 0.0
        z: -6.825
      reference_zone_exclusion:
        below_inlet_plane: true
        intersects_reference_station_z_over_D: false
        intersects_fuel_jet: false
        intersects_pilot_annulus: false
        intersects_coflow_air: false
        intersects_stoichiometric_flame_core: false
    measurement:
      claimed_gap_mm: 0.35
      verification_method: "Import STEP in FreeCAD and compute coflow_plenum_mount_bracket.Shape.distToShape(coflow_plenum_mount_shim.Shape)."
      expected_min_distance_mm: 0.35
    expected_advisor_to_catch: virtual_interface_detector
    hypothesized_v_series_match: V2_style_CAD_gap_detection_not_fluid_numerics_inheritance
    reference_data_validity: preserved

  - id: D8
    catalog_name: sub_mm_thin_shell
    description: "0.80 mm thin exterior bracket_lip_thin sheet on the coflow plenum mounting bracket."
    location:
      bodies_involved: [bracket_lip_thin]
      coordinate_system: "mm; z is axial/upward, r represented by x at wedge mid-plane"
      approximate_coords_mm:
        x: 212.0
        y: 0.0
        z: -12.5
      reference_zone_exclusion:
        below_inlet_plane: true
        intersects_reference_station_z_over_D: false
        intersects_fuel_jet: false
        intersects_pilot_annulus: false
        intersects_coflow_air: false
        intersects_stoichiometric_flame_core: false
    measurement:
      claimed_min_thickness_mm: 0.80
      verification_method: "Inspect STEP bbox thickness in y for bracket_lip_thin; expected dy = 0.80 mm."
      expected_bbox_dy_mm: 0.80
    expected_advisor_to_catch: thin_wall_advisor
    hypothesized_v_series_match: V10_style_thin_wall_advisor_not_fluid_numerics_inheritance
    reference_data_validity: preserved

global_reference_exclusions:
  radial_profile_stations_z_over_D: [7.5, 15.0, 30.0, 45.0, 60.0]
  radial_profile_stations_defect_free: true
  Z_profiles_preserved: true
  T_profiles_preserved: true
  species_profiles_preserved: true
  no_defects_in_reacting_inlets: true
  no_defects_on_flame_core: true
```

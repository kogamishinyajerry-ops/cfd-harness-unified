## Deliverable 1 — Engineering brief

### Component picked + bank ID
`case_016_m219_cavity_des_acoustic`

- Component: `E4_m219_weapons_bay_cavity` (bank extension for Phase 3 aeroacoustics; same pattern as case_010’s extension-style bank row)
- Source tier: Tier 1 reference-derived M219 cavity, baked into script rather than runtime-downloaded, following case_006’s resilience pattern
- Reasoning: this is the cleanest first project case for `compressible-DES` + FW-H, and it directly fills the uncovered aeroacoustics / cavity-flow row in the roadmap

### Engineering question
What Rossiter-mode frequencies, floor-pressure SPL peaks, drag increment, and FW-H far-field SPL does an M219 cavity at `M=0.85` produce when the as-installed geometry includes a small loose-debris cube (`D6`) and faceted leading/trailing-edge lip curvature (`D9`)?

### Physics signature
- Solver: `rhoPimpleFoam`
- Turbulence: `kOmegaSSTIDDES` preferred
- Alternate: `SpalartAllmarasDDES`
- Regime: 3D transient compressible cavity flow, `M=0.85`, `U=290 m/s`, `T=273.15 K`, `Re_L ≈ 6e6`
- Acoustics: FW-H porous-surface integration + single far-field observer
- Note from case_006 inheritance: use OpenFOAM-ESI-compatible BCs, not `characteristic*` names from foam-extend (V29)

### Parts inventory
- `region_air` — single fluid region
- Boundary patches: `inflow`, `outflow`, `top_far_field`, `far_field_port`, `far_field_starboard`
- Plate patches: `flat_plate_upstream`, `flat_plate_downstream`, `flat_plate_side_port`, `flat_plate_side_starboard`
- Cavity patches: `cavity_floor`, `cavity_le_wall`, `cavity_te_wall`, `cavity_side_wall_port`, `cavity_side_wall_starboard`
- Defect body: `debris_cube`
- Acoustic helper: `fwh_porous_surface`

### Boundary-condition plan
- `inflow`: `freestream`/`freestreamPressure` family, initialized to `M=0.85`
- `outflow`: `waveTransmissive` on pressure/thermo with `pressureInletOutletVelocity` or `freestream`-style velocity handling
- `top_far_field`, `far_field_port`, `far_field_starboard`: non-reflective far field, implemented with ESI-compatible `waveTransmissive`/`freestream` treatment
- Cavity walls and flat plates: `noSlip`
- Debris: `noSlip`
- Rationale: this explicitly avoids case_006 V29’s invalid fork-specific BC names

### Expected metrics
- Rossiter modes 1-4
- Cavity-floor pressure spectra at:
  - `Kulite_05` inferred at `x/L=0.55` → `(279.4, 0.0, -102.0) mm`
  - `Kulite_09` explicit benchmark station at `x/L=0.95` → `(482.6, 0.0, -102.0) mm`
- Published clean-cavity K09 anchors at `M=0.85`: about `142`, `353`, `592`, `813 Hz`; SPL about `141.6`, `146.3`, `143.4`, `130.2 dB`
- Drag increment versus the same plate with cavity replaced by a flush panel
- FW-H far-field SPL at observer `(254.0, 0.0, 8000.0) mm`

### Hypothesized failure modes
- Inherit case_006 V26-V32:
  - CAD defect-dimension self-check omission
  - explicit compressible transient timestep sensitivity
  - BC-name fork mismatch
  - source-cache brittleness
  - advisor-mapping drift
- Inherit case_010 V45-V46:
  - LES/DES-specific transient dictionary and averaging-stack gaps
  - mesh-cost escalation if the cavity shear layer is over-refined globally
- New case_016-specific risks:
  - tonal capture sensitive to LE/TE shear-layer resolution
  - FW-H surface placement too close to under-resolved turbulence
  - FFT window too short for low Rossiter modes
  - acoustic reflection from outer boundaries contaminating SPL
  - `[QUESTIONABLE 2026-05-08]` D6 advisor gap: no landed “extra body in fluid” detector
  - `[QUESTIONABLE 2026-05-08]` D9 advisor gap: no landed curved-surface tessellation-accuracy detector

### Defect injection summary
- `D6`: `10 mm` cube, placed inside cavity at `(320.0, 18.0, -79.0) mm`
- `D9`: LE and TE lip radii are not smooth arcs; each 90° turn is approximated with `16` straight facets
- Reference-data validity: `partial`
  - clean M219 tones remain the baseline anchor
  - direct ±3 dB / ±5% comparison should be interpreted as “defected-case deviation versus clean benchmark,” not strict clean-case parity

### Time-window note
`0.1 s` does not cover 100 cycles of the first Rossiter mode if `f1 ≈ 142 Hz`; it covers about `14` cycles. A true 100-cycle `R1` window is about `0.70 s`. For this case:
- v1 minimum: `0.12 s`
- recommended convergence window: `0.75 s`

### Sub-session estimated effort
`12-14 h`

---

## Deliverable 2 — CAD generation script

```python
#!/usr/bin/env python3
"""case_016_m219_cavity_des_acoustic CAD generator.

Tier-1 reference-derived M219 cavity geometry, baked into script for
determinism and source-resilience. The exported STEP contains:
- one actual fluid body: region_air
- one actual internal obstacle: debris_cube
- thin metadata solids for named patches and FW-H control surface

Patch-tag solids are export helpers only. region_air is the only body
intended for meshing as the fluid region.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

import cadquery as cq


CASE_ID = "case_016_m219_cavity_des_acoustic"
ASSEMBLY_NAME = CASE_ID
DEFAULT_OUT = Path(
    "/Users/Zhuanz/Desktop/case_016_m219_cavity_des_acoustic/inputs/cad_codex_v1.step"
)
PATCH_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

# === M219 geometry (mm) ===
CAVITY_L_MM = 508.0
CAVITY_W_MM = 102.0
CAVITY_D_MM = 102.0

# Exceeds the hard minima:
# - upstream >= 6L
# - downstream >= 4L
# - total domain length >= 30L
UPSTREAM_PLATE_L_MM = 10.0 * CAVITY_L_MM
DOWNSTREAM_PLATE_L_MM = 19.0 * CAVITY_L_MM
SIDE_PLATE_W_MM = 4.0 * CAVITY_W_MM
TOP_FAR_FIELD_H_MM = 12.0 * CAVITY_L_MM

# D9: baseline smooth lip radius, then intentionally faceted.
LE_FILLET_BASELINE_MM = 8.0
TE_FILLET_BASELINE_MM = 8.0
FACET_COUNT_PER_90DEG = 16

# D6: deterministic debris placement.
DEBRIS_SIZE_MM = 10.0
DEBRIS_POSITION_XYZ_MM = (320.0, 18.0, -79.0)

# Helper solids for STEP naming.
PATCH_TAG_THICKNESS_MM = 0.50

# FW-H helper surface extents.
FWH_X_MIN_MM = -0.15 * CAVITY_L_MM
FWH_X_MAX_MM = 1.15 * CAVITY_L_MM
FWH_Y_HALF_MM = 0.80 * CAVITY_W_MM
FWH_Z_MIN_MM = -1.10 * CAVITY_D_MM
FWH_Z_MAX_MM = 0.60 * CAVITY_D_MM

X_MIN_MM = -UPSTREAM_PLATE_L_MM
X_MAX_MM = CAVITY_L_MM + DOWNSTREAM_PLATE_L_MM
Y_HALF_MM = 0.5 * CAVITY_W_MM + SIDE_PLATE_W_MM

PART_NAMES = [
    "region_air",
    "inflow",
    "outflow",
    "top_far_field",
    "far_field_port",
    "far_field_starboard",
    "flat_plate_upstream",
    "flat_plate_downstream",
    "flat_plate_side_port",
    "flat_plate_side_starboard",
    "cavity_floor",
    "cavity_le_wall",
    "cavity_te_wall",
    "cavity_side_wall_port",
    "cavity_side_wall_starboard",
    "debris_cube",
    "fwh_porous_surface",
]


def validate_names() -> None:
    seen = set()
    for name in PART_NAMES:
        if not PATCH_NAME_RE.match(name):
            raise ValueError(f"Invalid name: {name}")
        if name in seen:
            raise ValueError(f"Duplicate name: {name}")
        seen.add(name)


def make_box(x0: float, x1: float, y0: float, y1: float, z0: float, z1: float) -> cq.Shape:
    return (
        cq.Workplane(
            "XY",
            origin=((x0 + x1) * 0.5, (y0 + y1) * 0.5, (z0 + z1) * 0.5),
        )
        .box(x1 - x0, y1 - y0, z1 - z0, centered=True)
        .val()
    )


def arc_points(
    cx: float,
    cz: float,
    radius: float,
    start_deg: float,
    end_deg: float,
    segments: int,
) -> list[tuple[float, float]]:
    pts: list[tuple[float, float]] = []
    for i in range(segments + 1):
        ang = math.radians(start_deg + (end_deg - start_deg) * (i / segments))
        pts.append((cx + radius * math.cos(ang), cz + radius * math.sin(ang)))
    return pts


def cavity_profile_points() -> list[tuple[float, float]]:
    # D9 is real here: the lip radii are piecewise-linear, not smooth arcs.
    pts: list[tuple[float, float]] = [(0.0, 0.0)]

    le_arc = arc_points(
        LE_FILLET_BASELINE_MM,
        0.0,
        LE_FILLET_BASELINE_MM,
        180.0,
        270.0,
        FACET_COUNT_PER_90DEG,
    )
    pts.extend(le_arc[1:])
    pts.append((LE_FILLET_BASELINE_MM, -CAVITY_D_MM))
    pts.append((CAVITY_L_MM - TE_FILLET_BASELINE_MM, -CAVITY_D_MM))

    te_arc = arc_points(
        CAVITY_L_MM - TE_FILLET_BASELINE_MM,
        0.0,
        TE_FILLET_BASELINE_MM,
        270.0,
        360.0,
        FACET_COUNT_PER_90DEG,
    )
    pts.extend(te_arc[1:])
    pts.append((0.0, 0.0))
    return pts


def build_region_air() -> cq.Shape:
    # Main external domain above the plate.
    top_box = make_box(
        X_MIN_MM,
        X_MAX_MM,
        -Y_HALF_MM,
        Y_HALF_MM,
        0.0,
        TOP_FAR_FIELD_H_MM,
    )

    # Cavity pocket below plate plane; union creates one connected fluid region.
    cavity_pocket = (
        cq.Workplane("XZ")
        .polyline(cavity_profile_points())
        .close()
        .extrude(CAVITY_W_MM, both=True)
        .val()
    )

    region_air = top_box.fuse(cavity_pocket)

    # D6 is real here: cut the debris solid out of the fluid region.
    sx, sy, sz = DEBRIS_POSITION_XYZ_MM
    debris = make_box(
        sx - 0.5 * DEBRIS_SIZE_MM,
        sx + 0.5 * DEBRIS_SIZE_MM,
        sy - 0.5 * DEBRIS_SIZE_MM,
        sy + 0.5 * DEBRIS_SIZE_MM,
        sz - 0.5 * DEBRIS_SIZE_MM,
        sz + 0.5 * DEBRIS_SIZE_MM,
    )
    return region_air.cut(debris)


def build_debris_cube() -> cq.Shape:
    sx, sy, sz = DEBRIS_POSITION_XYZ_MM
    return make_box(
        sx - 0.5 * DEBRIS_SIZE_MM,
        sx + 0.5 * DEBRIS_SIZE_MM,
        sy - 0.5 * DEBRIS_SIZE_MM,
        sy + 0.5 * DEBRIS_SIZE_MM,
        sz - 0.5 * DEBRIS_SIZE_MM,
        sz + 0.5 * DEBRIS_SIZE_MM,
    )


def build_patch_tags() -> dict[str, cq.Shape]:
    t = PATCH_TAG_THICKNESS_MM
    w_half = 0.5 * CAVITY_W_MM

    tags = {
        "inflow": make_box(X_MIN_MM, X_MIN_MM + t, -Y_HALF_MM, Y_HALF_MM, 0.0, TOP_FAR_FIELD_H_MM),
        "outflow": make_box(X_MAX_MM - t, X_MAX_MM, -Y_HALF_MM, Y_HALF_MM, 0.0, TOP_FAR_FIELD_H_MM),
        "top_far_field": make_box(X_MIN_MM, X_MAX_MM, -Y_HALF_MM, Y_HALF_MM, TOP_FAR_FIELD_H_MM - t, TOP_FAR_FIELD_H_MM),
        "far_field_port": make_box(X_MIN_MM, X_MAX_MM, -Y_HALF_MM, -Y_HALF_MM + t, 0.0, TOP_FAR_FIELD_H_MM),
        "far_field_starboard": make_box(X_MIN_MM, X_MAX_MM, Y_HALF_MM - t, Y_HALF_MM, 0.0, TOP_FAR_FIELD_H_MM),
        "flat_plate_upstream": make_box(X_MIN_MM, 0.0, -Y_HALF_MM, Y_HALF_MM, 0.0, t),
        "flat_plate_downstream": make_box(CAVITY_L_MM, X_MAX_MM, -Y_HALF_MM, Y_HALF_MM, 0.0, t),
        "flat_plate_side_port": make_box(0.0, CAVITY_L_MM, -Y_HALF_MM, -w_half, 0.0, t),
        "flat_plate_side_starboard": make_box(0.0, CAVITY_L_MM, w_half, Y_HALF_MM, 0.0, t),
        "cavity_floor": make_box(
            LE_FILLET_BASELINE_MM,
            CAVITY_L_MM - TE_FILLET_BASELINE_MM,
            -w_half,
            w_half,
            -CAVITY_D_MM,
            -CAVITY_D_MM + t,
        ),
        "cavity_le_wall": make_box(
            0.0,
            LE_FILLET_BASELINE_MM,
            -w_half,
            w_half,
            -CAVITY_D_MM,
            0.0,
        ),
        "cavity_te_wall": make_box(
            CAVITY_L_MM - TE_FILLET_BASELINE_MM,
            CAVITY_L_MM,
            -w_half,
            w_half,
            -CAVITY_D_MM,
            0.0,
        ),
        "cavity_side_wall_port": make_box(0.0, CAVITY_L_MM, -w_half, -w_half + t, -CAVITY_D_MM, 0.0),
        "cavity_side_wall_starboard": make_box(0.0, CAVITY_L_MM, w_half - t, w_half, -CAVITY_D_MM, 0.0),
        "fwh_porous_surface": make_box(
            FWH_X_MIN_MM,
            FWH_X_MAX_MM,
            -FWH_Y_HALF_MM,
            FWH_Y_HALF_MM,
            FWH_Z_MIN_MM,
            FWH_Z_MAX_MM,
        ),
    }
    return tags


def write_metadata(step_path: Path) -> None:
    metadata = {
        "case_id": CASE_ID,
        "cad_source_tier": "Tier 1 reference-derived public M219 cavity",
        "reference_urls": [
            "https://ntrl.ntis.gov/NTRL/dashboard/searchResults/titleDetail/ADP010729.xhtml",
            "https://www.researchgate.net/publication/329737336_Very-Large_Eddy_Simulations_of_the_M219_Cavity_at_High-Subsonic_and_Supersonic_Conditions",
            "https://link.springer.com/article/10.1007/s42496-024-00240-6",
        ],
        "geometry_mm": {
            "L": CAVITY_L_MM,
            "W": CAVITY_W_MM,
            "D": CAVITY_D_MM,
            "upstream_plate_L": UPSTREAM_PLATE_L_MM,
            "downstream_plate_L": DOWNSTREAM_PLATE_L_MM,
            "side_plate_W_each": SIDE_PLATE_W_MM,
            "top_far_field_H": TOP_FAR_FIELD_H_MM,
        },
        "defects": {
            "D6": {
                "size_mm": DEBRIS_SIZE_MM,
                "position_xyz_mm": DEBRIS_POSITION_XYZ_MM,
            },
            "D9": {
                "facet_count_per_90deg": FACET_COUNT_PER_90DEG,
                "le_fillet_baseline_mm": LE_FILLET_BASELINE_MM,
                "te_fillet_baseline_mm": TE_FILLET_BASELINE_MM,
            },
        },
    }
    meta_path = step_path.with_suffix(".source.json")
    meta_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_assembly() -> cq.Assembly:
    validate_names()

    region_air = build_region_air()
    debris_cube = build_debris_cube()
    patch_tags = build_patch_tags()

    asm = cq.Assembly(name=ASSEMBLY_NAME)
    asm.add(region_air, name="region_air")
    asm.add(debris_cube, name="debris_cube")

    # Named helper solids preserve patch identities in STEP export.
    for name in sorted(patch_tags):
        asm.add(patch_tags[name], name=name)

    return asm


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUT),
        help="Output STEP path",
    )
    args = parser.parse_args()

    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    asm = build_assembly()
    asm.save(str(out_path), exportType="STEP")
    write_metadata(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

---

## Deliverable 3 — STEP file path

`/Users/Zhuanz/Desktop/case_016_m219_cavity_des_acoustic/inputs/cad_codex_v1.step`

Read-only sandbox note: I can provide the deterministic generator and canonical output path here, but I cannot emit the binary STEP artifact from this session.

---

## Deliverable 4 — Parts manifest YAML

```yaml
case_id: case_016_m219_cavity_des_acoustic
cad_source: tier1_reference_derived_m219_baked_into_script
generation_script: scripts/build_cad.py
step_file: /Users/Zhuanz/Desktop/case_016_m219_cavity_des_acoustic/inputs/cad_codex_v1.step
units_in_step: mm

region:
  name: region_air
  type: single_fluid_region

patches:
  - name: inflow
    bc_role: freestream_inlet
    bc_type:
      U: freestream
      p: freestreamPressure
      T: freestream
  - name: outflow
    bc_role: nonreflecting_outlet
    bc_type:
      U: pressureInletOutletVelocity
      p: waveTransmissive
      T: waveTransmissive
  - name: top_far_field
    bc_role: nonreflecting_farfield
    bc_type:
      U: freestream
      p: waveTransmissive
      T: waveTransmissive
  - name: far_field_port
    bc_role: nonreflecting_farfield
    bc_type:
      U: freestream
      p: waveTransmissive
      T: waveTransmissive
  - name: far_field_starboard
    bc_role: nonreflecting_farfield
    bc_type:
      U: freestream
      p: waveTransmissive
      T: waveTransmissive
  - name: flat_plate_upstream
    bc_role: wall
    bc_type:
      U: noSlip
      p: zeroGradient
      T: zeroGradient
  - name: flat_plate_downstream
    bc_role: wall
    bc_type:
      U: noSlip
      p: zeroGradient
      T: zeroGradient
  - name: flat_plate_side_port
    bc_role: wall
    bc_type:
      U: noSlip
      p: zeroGradient
      T: zeroGradient
  - name: flat_plate_side_starboard
    bc_role: wall
    bc_type:
      U: noSlip
      p: zeroGradient
      T: zeroGradient
  - name: cavity_floor
    bc_role: wall
    bc_type:
      U: noSlip
      p: zeroGradient
      T: zeroGradient
  - name: cavity_le_wall
    bc_role: wall
    bc_type:
      U: noSlip
      p: zeroGradient
      T: zeroGradient
    notes: D9 implemented on this lip geometry as 16 facets per 90 degrees
  - name: cavity_te_wall
    bc_role: wall
    bc_type:
      U: noSlip
      p: zeroGradient
      T: zeroGradient
    notes: D9 implemented on this lip geometry as 16 facets per 90 degrees
  - name: cavity_side_wall_port
    bc_role: wall
    bc_type:
      U: noSlip
      p: zeroGradient
      T: zeroGradient
  - name: cavity_side_wall_starboard
    bc_role: wall
    bc_type:
      U: noSlip
      p: zeroGradient
      T: zeroGradient
  - name: debris_cube
    bc_role: internal_wall
    bc_type:
      U: noSlip
      p: zeroGradient
      T: zeroGradient

thermophysics:
  fluid: air
  equation_of_state: perfectGas
  transport: sutherland
  gamma: 1.4
  R: 287.05
  sutherland:
    As: 1.458e-6
    Ts: 110.4

operating_point:
  benchmark: M219_shallow_cavity
  mach: 0.85
  velocity_m_per_s: 290.0
  temperature_K: 273.15
  reynolds_based_on_L: 6.0e6
  altitude_reference: benchmark_equivalent_high_subsonic_tunnel_condition

iddes_config:
  preferred_model: kOmegaSSTIDDES
  alternate_model: SpalartAllmarasDDES
  dt_s: 2.0e-5
  sample_rate_hz: 50000
  cfl_target_max: 1.0
  notes:
    - case_010 LES inheritance: use 2nd-order transient schemes and explicit averaging/post-processing stack
    - case_006 inheritance: avoid invalid characteristic* BC names on OpenFOAM-ESI

fwh_config:
  surface_name: fwh_porous_surface
  surface_box_mm:
    x_min: -76.2
    x_max: 584.2
    y_min: -81.6
    y_max: 81.6
    z_min: -112.2
    z_max: 61.2
  observer_xyz_mm: [254.0, 0.0, 8000.0]
  observer_definition: 8 m above cavity center at 90 degree elevation
  sample_rate_hz: 50000
  acquisition_window_s_min: 0.12
  recommended_long_window_s: 0.75
  note: 0.75 s is needed for about 100 cycles of the first Rossiter mode near 142 Hz

pressure_probes:
  - name: Kulite_05
    xyz_mm: [279.4, 0.0, -102.0]
    source_status: inferred_from_10_probe_centerline_layout
  - name: Kulite_09
    xyz_mm: [482.6, 0.0, -102.0]
    source_status: explicit_x_over_L_0p95_benchmark_station

reference_data:
  clean_cavity_k09_targets:
    rossiter_hz: [142.0, 353.0, 592.0, 813.0]
    spl_db: [141.6, 146.3, 143.4, 130.2]
  theory_check:
    rossiter_heller_hz_approx: [157.0, 381.0, 605.0, 829.0]
    note: theory band is for sanity checking; experimental anchors remain primary
  reference_data_validity: partial
  references:
    - https://ntrl.ntis.gov/NTRL/dashboard/searchResults/titleDetail/ADP010729.xhtml
    - https://www.researchgate.net/publication/329737336_Very-Large_Eddy_Simulations_of_the_M219_Cavity_at_High-Subsonic_and_Supersonic_Conditions
    - https://link.springer.com/article/10.1007/s42496-024-00240-6

patch_naming_check:
  - all names match ^[A-Za-z][A-Za-z0-9_]*$
  - no duplicate names
  - no spaces or hyphens
```

---

## Deliverable 5 — Defect manifest YAML

```yaml
case_id: case_016_m219_cavity_des_acoustic
reference_data_validity: partial

defects:
  - defect_id: D6
    title: floating_debris_cube_in_cavity
    status: "[QUESTIONABLE 2026-05-08]"
    geometry:
      body_name: debris_cube
      size_mm: 10.0
      center_xyz_mm: [320.0, 18.0, -79.0]
      clearances_mm:
        x_to_le: 315.0
        x_to_te: 183.0
        y_to_starboard_wall: 28.0
        y_to_port_wall: 64.0
        z_to_floor: 18.0
    intent: stray assembly debris inside resolved flow region
    expected_advisor_to_catch: none_landed
    advisor_gap_vfinding: extra_body_in_fluid_detection_missing
    verification_pending: manual body-count plus bbox and point-to-wall clearance check in FreeCAD
    to_resolve: land a dedicated extra-body-in-fluid advisor and validate on at least two cases

  - defect_id: D9
    title: faceted_le_te_lip_curvature
    status: "[QUESTIONABLE 2026-05-08]"
    geometry:
      target_patches: [cavity_le_wall, cavity_te_wall]
      baseline_radius_mm: 8.0
      facets_per_90deg: 16
      segment_angle_deg: 5.625
    intent: over-aggressive curvature simplification at the acoustic-production lip
    expected_advisor_to_catch: none_landed
    advisor_gap_vfinding: curved_surface_tessellation_accuracy_detection_missing
    verification_pending: manual facet-count and chord-length comparison against the baseline radius
    to_resolve: land a tessellation-accuracy advisor and validate on at least two curved-surface cases

manual_checks:
  - confirm region_air remains a single connected fluid body after debris subtraction
  - confirm debris_cube exists as a separate solid and is excluded from region_air
  - confirm LE and TE each contain exactly 16 straight segments over 90 degrees
  - confirm all names match ^[A-Za-z][A-Za-z0-9_]*$
```

**Sources**
- M219 geometry, Kulite layout, and benchmark criteria: https://ntrl.ntis.gov/NTRL/dashboard/searchResults/titleDetail/ADP010729.xhtml
- Shallow/deep M219 behavior and Rossiter-formula context: https://www.researchgate.net/publication/329737336_Very-Large_Eddy_Simulations_of_the_M219_Cavity_at_High-Subsonic_and_Supersonic_Conditions
- Standard M219 clean-cavity tone anchors used here for K09 comparison: https://link.springer.com/article/10.1007/s42496-024-00240-6
- IDDES-scale timestep/cell-count precedent for M219-type cavity work: https://www.parcfd.org/2019/program/serv.php?No=1090

Key inference note: `Kulite_05` at `x/L=0.55` is inferred from the published 10-probe centerline layout; `Kulite_09` at `x/L=0.95` is explicitly benchmarked. The `0.75 s` recommended acoustic window is my calculation from the published `~142 Hz` first Rossiter mode.

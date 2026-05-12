## Deliverable 1 — Engineering brief

- **Case ID:** `case_020_porous_media_filter_darcy_forchheimer`
- **Component picked:** HEPA terminal filter cassette in a rounded-rectangle HVAC housing.
- **Bank/source ID:** solver-class-adjacent to component-bank `A3` internal duct/manifold archetype; strategic slot is Phase 4 `case_020` porous-media row. Tier 1 ERCOFTAC porous-filter CAD was not found in the curated catalog or public check, so this is a **Tier 3 parametric fallback**.
- **Reasoning:** it stays inside `simpleFoam` + single fluid region, gives a realistic porous insert + plenum topology, and makes D9/D10 both physically meaningful.

- **Engineering question:** what are `Δp_filter`, downstream flow uniformity, and bypass fraction at `U_face = 2.5 m/s` for an as-installed HEPA cassette with a faceted housing corner (D9) and a 1.0 mm open edge-seal slit (D10)?

- **Physics signature:** steady incompressible RANS (`simpleFoam`), air at standard conditions, `Re_housing ≈ 3.3e4`, Darcy-Forchheimer porous source in `cellZone porous_zone_filter_element`, anisotropic tensor with streamwise resistance lower than cross-stream resistance.

- **Parts inventory:**
  - `region_fluid`: single fluid body
  - `porous_zone_filter_element`: porous cellZone marker
  - `inlet`
  - `outlet`
  - `housing_wall`
  - `filter_element_face_upstream`
  - `filter_element_face_downstream`
  - `filter_edge_seal`
  - `filter_edge_open_d10`

- **BC plan:**
  - `inlet`: `flowRateInletVelocity`, set from `U_face = 2.5 m/s`
  - `outlet`: pressure outlet, `p=0`
  - `housing_wall`: `noSlip`
  - `filter_element_face_upstream` / `filter_element_face_downstream`: internal porous-zone faces; drag comes from `fvOptions`
  - `filter_edge_seal`: `noSlip`
  - `filter_edge_open_d10`: leak path opening bounded by wall surfaces around the slit

- **Expected metrics:**
  - `Δp_filter`
  - outlet uniformity `σ_U / U_mean`
  - bypass flow through `D10` as `% of total flow`
  - streamwise vs cross-stream porous-zone flux split

- **Hypothesized failure modes:**
  - case_003 inheritance: steady incompressible-RANS residual plateau / recirculation sensitivity in plenums
  - new: porous-source sign convention error flips drag direction
  - new: wrong `coordinateSystem` basis rotates anisotropic tensor
  - new: D10 bypass depresses predicted `Δp` and worsens outlet uniformity
  - new: D9 facet edges create local separation / non-smooth wall shear
  - new: D10 advisor-gap, since no landed open-shell detector exists

- **Defect injection summary:**
  - `D9`: housing corner curvature replaced by `16` facets per `90°`
  - `D10`: `1.0 mm` slit at one filter-frame corner, connecting upstream and downstream plenums
  - verification:
    - D9: compare faceted corner chord set against smooth `R=18 mm` reference
    - D10: measure clear slit width and confirm continuous leak path through seal thickness

- **Estimated effort:** `8h`

## Deliverable 2 — CAD generation script

```python
#!/usr/bin/env python3
"""case_020 porous media filter CAD generator."""

from __future__ import annotations

import argparse
from pathlib import Path
import cadquery as cq

CASE_ID = "case_020_porous_media_filter_darcy_forchheimer"
DEFAULT_OUT = "/Users/Zhuanz/Desktop/case_020_porous_media_filter/inputs/cad_codex_v1.step"

# Geometry, mm
housing_L = 360.0
housing_W = 220.0
housing_H = 180.0
housing_corner_R = 18.0
filter_W = 150.0
filter_H = 130.0
filter_element_thickness = 32.0
filter_x_center = housing_L / 2.0
seal_frame_width = 14.0
patch_thickness = 0.6

# Defects
d9_facet_count_per_90deg = 16
d9_target_surface = "housing_corner_curve"
d10_gap_size_mm = 1.0
d10_corner_index = 0  # 0 = top-left when viewed downstream

# Porous coefficients for fvOptions metadata
d_streamwise = 2.0e7   # 1/m^2
d_cross = 4.0e8        # 1/m^2
f_Forchheimer = 2500.0 # 1/m

PATCH_NAMES = [
    "region_fluid",
    "porous_zone_filter_element",
    "inlet",
    "outlet",
    "housing_wall",
    "filter_element_face_upstream",
    "filter_element_face_downstream",
    "filter_edge_seal",
    "filter_edge_open_d10",
]

def rounded_rect_points(w: float, h: float, r: float, n: int):
    import math
    pts = []
    corners = [
        ( w / 2 - r,  h / 2 - r, 0.0),
        (-w / 2 + r,  h / 2 - r, math.pi / 2),
        (-w / 2 + r, -h / 2 + r, math.pi),
        ( w / 2 - r, -h / 2 + r, 3 * math.pi / 2),
    ]
    for cy, cz, a0 in corners:
        for i in range(n + 1):
            a = a0 + i * (math.pi / 2) / n
            pts.append((cy + r * math.cos(a), cz + r * math.sin(a)))
    return pts

def yz_profile(w: float, h: float, r: float, n: int) -> cq.Workplane:
    pts = rounded_rect_points(w, h, r, n)
    return cq.Workplane("YZ").polyline(pts).close()

def box_at(x0, x1, y0, y1, z0, z1):
    return (
        cq.Workplane("XY")
        .box(x1 - x0, y1 - y0, z1 - z0, centered=False)
        .translate((x0, y0, z0))
    )

def build():
    validate_names()

    # D9: faceted rounded-rectangle duct section.
    duct = yz_profile(housing_W, housing_H, housing_corner_R, d9_facet_count_per_90deg).extrude(housing_L)

    x0 = filter_x_center - filter_element_thickness / 2.0
    x1 = filter_x_center + filter_element_thickness / 2.0

    porous_zone = box_at(
        x0, x1,
        -filter_W / 2.0, filter_W / 2.0,
        -filter_H / 2.0, filter_H / 2.0,
    )

    # Seal ring blocks bypass around the porous insert.
    outer_ring = box_at(
        x0, x1,
        -(filter_W / 2.0 + seal_frame_width), filter_W / 2.0 + seal_frame_width,
        -(filter_H / 2.0 + seal_frame_width), filter_H / 2.0 + seal_frame_width,
    )
    inner_ring = porous_zone
    seal_ring = outer_ring.cut(inner_ring)

    # D10: remove one small corner segment from the seal ring to create a leak slit.
    slit = box_at(
        x0, x1,
        -(filter_W / 2.0 + seal_frame_width),
        -(filter_W / 2.0 + seal_frame_width) + d10_gap_size_mm,
        filter_H / 2.0 - 12.0,
        filter_H / 2.0 + seal_frame_width,
    )
    seal_ring_defected = seal_ring.cut(slit)

    region_fluid = duct.cut(seal_ring_defected)

    inlet = yz_profile(housing_W, housing_H, housing_corner_R, d9_facet_count_per_90deg).extrude(patch_thickness)
    outlet = yz_profile(housing_W, housing_H, housing_corner_R, d9_facet_count_per_90deg).extrude(patch_thickness).translate((housing_L - patch_thickness, 0, 0))

    housing_wall = (
        cq.Workplane("XY")
        .box(housing_L, housing_W + 2 * patch_thickness, housing_H + 2 * patch_thickness)
        .cut(cq.Workplane("XY").box(housing_L + 1.0, housing_W, housing_H))
    )

    filter_element_face_upstream = box_at(
        x0 - patch_thickness, x0,
        -filter_W / 2.0, filter_W / 2.0,
        -filter_H / 2.0, filter_H / 2.0,
    )
    filter_element_face_downstream = box_at(
        x1, x1 + patch_thickness,
        -filter_W / 2.0, filter_W / 2.0,
        -filter_H / 2.0, filter_H / 2.0,
    )

    filter_edge_seal = seal_ring_defected
    filter_edge_open_d10 = slit

    asm = cq.Assembly(name=CASE_ID)
    asm.add(region_fluid, name="region_fluid")
    asm.add(porous_zone, name="porous_zone_filter_element")
    asm.add(inlet, name="inlet")
    asm.add(outlet, name="outlet")
    asm.add(housing_wall, name="housing_wall")
    asm.add(filter_element_face_upstream, name="filter_element_face_upstream")
    asm.add(filter_element_face_downstream, name="filter_element_face_downstream")
    asm.add(filter_edge_seal, name="filter_edge_seal")
    asm.add(filter_edge_open_d10, name="filter_edge_open_d10")
    return asm

def validate_names():
    import re
    rx = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
    if len(PATCH_NAMES) != len(set(PATCH_NAMES)):
        raise ValueError("Duplicate patch names")
    for name in PATCH_NAMES:
        if not rx.match(name):
            raise ValueError(f"Invalid patch name: {name}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    asm = build()
    asm.save(str(out), exportType="STEP")
    print(f"Wrote {out}")

if __name__ == "__main__":
    main()
```

## Deliverable 3 — STEP file path

`/Users/Zhuanz/Desktop/case_020_porous_media_filter/inputs/cad_codex_v1.step`

## Deliverable 4 — Parts manifest

```yaml
case_id: case_020_porous_media_filter_darcy_forchheimer
cad_source:
  tier: tier3_parametric_fallback
  justification: >
    No public Tier 1 ERCOFTAC porous-filter CAD entry was identified in the
    curated catalog or public source check; geometry is a deterministic
    HEPA cassette fallback.
generation_script: scripts/build_cad.py
step_file: inputs/cad_codex_v1.step
units_in_step: mm
region: region_fluid
cellZones:
  - name: porous_zone_filter_element
    model: DarcyForchheimer
    coordinate_frame:
      origin_mm: [180.0, 0.0, 0.0]
      e1_streamwise: [1.0, 0.0, 0.0]
      e2_cross: [0.0, 1.0, 0.0]
      e3_cross: [0.0, 0.0, 1.0]
    d_streamwise_inv_m2: 2.0e7
    d_cross_inv_m2: 4.0e8
    f_Forchheimer_inv_m: 2500.0
    thickness_mm: 32.0
patches:
  - name: inlet
    bc_type: flowRateInletVelocity
  - name: outlet
    bc_type: pressureOutlet
  - name: housing_wall
    bc_type: noSlip
  - name: filter_element_face_upstream
    bc_type: porous_internal_interface
  - name: filter_element_face_downstream
    bc_type: porous_internal_interface
  - name: filter_edge_seal
    bc_type: noSlip
  - name: filter_edge_open_d10
    bc_type: leak_path_wall_bounded_opening
thermophysics:
  fluid: air
  rho_kg_m3: 1.20
  mu_Pa_s: 1.8e-5
application:
  type: HEPA_terminal_filter
  operating_face_velocity_m_s: 2.5
  housing_Re: 3.3e4
  target_metrics:
    - pressure_drop_delta_p_filter
    - outlet_uniformity_sigma_u_over_u_mean
    - bypass_fraction_d10
    - anisotropic_flux_split
reference:
  pressure_drop_source: Camfil Absolute DG H13 product data
  published_dp_ref_Pa: 250
  published_condition: 3400 m3/h through 610x610 mm filter (~2.54 m/s face velocity)
  uniformity_reference: >
    Inferred engineering baseline from the same geometry with D9/D10 disabled;
    acceptance target is defected-case outlet uniformity within 0.05 of sealed smooth control.
patch_naming_check:
  - all names match ^[A-Za-z][A-Za-z0-9_]*$
  - no duplicate names
  - no spaces or hyphens
```

## Deliverable 5 — Defect manifest

```yaml
case_id: case_020_porous_media_filter_darcy_forchheimer
defects:
  - id: D9
    name: faceted_curve
    target_surface: housing_corner_curve
    facet_count_per_90deg: 16
    smooth_reference_radius_mm: 18.0
    expected_advisor_to_catch: NONE
    advisor_gap_flag: true
    manual_verification: >
      Compare the corner against the smooth R18 reference; each 90-degree arc is
      represented by 16 straight facets, so the curve is intentionally faceted.
  - id: D10
    name: open_edge_seal_slit
    target_location: top_left_filter_frame_corner_viewed_downstream
    gap_size_mm: 1.0
    expected_advisor_to_catch: NONE
    first_injection_in_batch: true
    advisor_gap_v_finding: true
    manual_verification: >
      Measure the clear slit width at the filter-edge seal; expected opening is
      1.0 mm and must connect upstream and downstream plenums continuously.
knowledge_status:
  d9: open
  d10: open
notes:
  - D10 is the final uncovered defect category in the 011-020 batch.
  - D9 and D10 should both be carried into harvest 003 as advisor-gap evidence unless a detector lands first.
```

**Sources**

- [case_020_codex_request.md](/Users/Zhuanz/Desktop/cfd-harness-unified/.planning/methodology/kickoff/case_020_codex_request.md)
- [codex_case_design_protocol.md](/Users/Zhuanz/Desktop/cfd-harness-unified/.planning/methodology/codex_case_design_protocol.md)
- [case_003_codex_response.md](/Users/Zhuanz/Desktop/cfd-harness-unified/.planning/methodology/kickoff/case_003_codex_response.md)
- OpenFOAM explicit porosity docs: https://doc.openfoam.com/2312/tools/processing/numerics/fvoptions/sources/rtm/explicitPorosity/
- OpenFOAM `DarcyForchheimer` API: https://www.openfoam.com/documentation/guides/latest/api/classFoam_1_1porosityModels_1_1DarcyForchheimer.html
- Camfil Absolute DG H13 data: https://www.camfil.com/en/products/epa-hepa-and-ulpa-filters/compact-filters-%28box-type%29/absolute-c-d/absolute-dg-_-32488

I could not materialize the STEP artifact in this turn because the workspace is read-only, so deliverable 3 is the canonical target path rather than a written file.

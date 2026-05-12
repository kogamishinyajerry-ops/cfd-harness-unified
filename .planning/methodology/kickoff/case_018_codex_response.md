Read-only sandbox, so these are the five deliverables inline.

## Deliverable 1 — Engineering brief

**Component picked:** Stairmand high-efficiency cyclone separator, Phase 4 separator slot (no direct core-bank row; roadmap-backed custom industrial separator).  
**Reasoning:** first true 3D swirl-dominant separator in the fleet, extends case_008’s Lagrangian pipeline into a cyclone/PVC regime, and hits a high-value dust-collection archetype.

**Engineering question:** what is the `d50` cut-off and `η(d_p)` curve for a Stairmand cyclone at industrial inlet loading, and how much do a floating D6 debris cube and swirl-core precession shift `Δp` / collection efficiency?

**Physics signature:** `pimpleFoam` transient + RSM (`LaunderGibsonRSTM`) + `kinematicCloud` one-way coupled, `Re_D ≈ 3.3e5` at `D=250 mm`, `U_inlet=20 m/s`, swirl number `S ~ 1-3`, particle Stokes number spanning `0.01-1.0` over `1-50 μm`.

**Parts inventory:** `region_air` fluid volume, `debris_cube_d6` floating defect body, logical patches `inlet_tangential`, `overflow_outlet`, `underflow_outlet`, `cyclone_walls`.

**BC plan:** `inlet_tangential: flowRateInletVelocity` or fixed `U` tangent to the barrel; `overflow_outlet: pressureOutlet`; `underflow_outlet: pressureOutlet`; `cyclone_walls: noSlip`; particle walls `rebound` baseline, outlets `escape`.

**Expected metrics:** `S = ∫ U_θ U_z r dA / (R ∫ U_z² dA)`, `d50` cut size, `η(d_p)` at `1, 2, 3, 5, 8, 15, 30 μm`, `Δp_inlet-overflow`, vortex-core trajectory / PVC precession.

**Hypothesized failure modes:** case_008 V36/V37 inheritance on Lagrangian plumbing; RSM convergence slower than k-ε; PVC under-captured below convergence threshold; particle injection plane sensitivity; wall rebound vs escape shifts fine-dust `η`; D6 debris perturbs swirl number and underflow split.

**Defect injection summary:** one required defect only: D6 floating cube `10-30 mm` inside the collection chamber; advisor gap is expected (`NONE` / manual body-count + bbox check).

**Sub-session estimated effort:** `10-12h`.

**Sources used:**  
`https://www.researchgate.net/publication/364102715_Experimental_Analysis_of_Dual_Inlet_Cyclone_Separator`  
`https://www.sciencedirect.com/science/article/pii/S0032591017305338`  
`https://www.mdpi.com/2076-3417/11/12/5342`  
`https://www.mdpi.com/2674-0516/2/3/38`

## Deliverable 2 — CAD generation script

```python
#!/usr/bin/env python3
"""case_018_stairmand_cyclone_separator CAD generator.

Single fluid-region Stairmand cyclone volume plus one floating D6 debris cube.
Designed by Codex per cfd-harness-unified case-design protocol.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import cadquery as cq


CASE_ID = "case_018_stairmand_cyclone_separator"
DEFAULT_OUT = Path("inputs/cad_codex_v1.step")
PATCH_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

# === Stairmand geometry (public literature ratios) ===
D_CYCLONE_MM = 250.0  # 200-300 mm hard constraint satisfied
INLET_H_FACTOR = 0.5
INLET_W_FACTOR = 0.2
BODY_H_FACTOR = 1.5
CONE_H_FACTOR = 2.5
VORTEX_FINDER_D_FACTOR = 0.5
VORTEX_FINDER_L_FACTOR = 0.5
UNDERFLOW_D_FACTOR = 0.4

# === Construction tolerances for clean fusing ===
INLET_OVERLAP_MM = 1.0
PIPE_OVERLAP_MM = 1.0

# === D6 defect ===
DEBRIS_SIZE_MM = 20.0
DEBRIS_POSITION_XYZ_MM = (20.0, 0.0, -280.0)

BODY_NAMES = ["region_air", "debris_cube_d6"]
PATCH_NAMES = [
    "inlet_tangential",
    "overflow_outlet",
    "underflow_outlet",
    "cyclone_walls",
]


def validate_names() -> None:
    seen = set()
    for name in BODY_NAMES + PATCH_NAMES:
        if not PATCH_NAME_RE.match(name):
            raise ValueError(f"Invalid OpenFOAM-safe name: {name}")
        if name in seen:
            raise ValueError(f"Duplicate name: {name}")
        seen.add(name)


def mm(v: float) -> float:
    return float(v)


def box(center: tuple[float, float, float], size: tuple[float, float, float]) -> cq.Shape:
    return cq.Workplane("XY", origin=center).box(
        size[0], size[1], size[2], centered=True
    ).val()


def frustum(z_top: float, height: float, r_top: float, r_bottom: float) -> cq.Shape:
    # Use a lofted frustum rather than a faceted approximation.
    return (
        cq.Workplane("XY", origin=(0.0, 0.0, z_top))
        .circle(r_top)
        .workplane(offset=-height)
        .circle(r_bottom)
        .loft(combine=True, ruled=True)
        .val()
    )


def fuse_all(shapes: list[cq.Shape]) -> cq.Shape:
    # Sequential fuse avoids the Compound-of-Faces pattern that caused V16/V24 issues.
    fused = shapes[0]
    for shp in shapes[1:]:
        fused = fused.fuse(shp)
    return fused


def build_region_air() -> cq.Shape:
    body_h = BODY_H_FACTOR * D_CYCLONE_MM
    cone_h = CONE_H_FACTOR * D_CYCLONE_MM
    inlet_h = INLET_H_FACTOR * D_CYCLONE_MM
    inlet_w = INLET_W_FACTOR * D_CYCLONE_MM
    inlet_l = 0.50 * D_CYCLONE_MM
    vf_d = VORTEX_FINDER_D_FACTOR * D_CYCLONE_MM
    vf_insert = VORTEX_FINDER_L_FACTOR * D_CYCLONE_MM
    underflow_d = UNDERFLOW_D_FACTOR * D_CYCLONE_MM
    underflow_l = 0.50 * D_CYCLONE_MM

    barrel = cq.Workplane("XY", origin=(0.0, 0.0, 0.0)).circle(D_CYCLONE_MM / 2.0).extrude(body_h).val()
    cone = frustum(0.0, cone_h, D_CYCLONE_MM / 2.0, underflow_d / 2.0)

    # Tangential inlet duct, with slight overlap into the barrel to guarantee a single fused body.
    inlet_center = (
        -0.5 * D_CYCLONE_MM - 0.5 * inlet_w + INLET_OVERLAP_MM,
        -0.5 * inlet_l,
        body_h - 0.5 * inlet_h,
    )
    inlet = box(inlet_center, (inlet_w, inlet_l, inlet_h))

    # Vortex finder insertion only, capped at the overflow outlet plane.
    vortex_finder = (
        cq.Workplane("XY", origin=(0.0, 0.0, body_h))
        .circle(vf_d / 2.0)
        .extrude(-(vf_insert + PIPE_OVERLAP_MM))
        .val()
    )

    # Underflow dust-leg stub, again slightly overlapped for clean fusion.
    underflow = (
        cq.Workplane("XY", origin=(0.0, 0.0, -cone_h))
        .circle(underflow_d / 2.0)
        .extrude(-(underflow_l + PIPE_OVERLAP_MM))
        .val()
    )

    # One connected fluid-region solid: barrel + cone + inlet + vortex finder + underflow stub.
    return fuse_all([barrel, cone, inlet, vortex_finder, underflow])


def build_debris_cube() -> cq.Shape:
    return box(DEBRIS_POSITION_XYZ_MM, (DEBRIS_SIZE_MM, DEBRIS_SIZE_MM, DEBRIS_SIZE_MM))


def build_assembly() -> cq.Assembly:
    asm = cq.Assembly(name=CASE_ID)
    asm.add(build_region_air(), name="region_air")
    asm.add(build_debris_cube(), name="debris_cube_d6")
    return asm


def main() -> int:
    validate_names()

    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="STEP output path")
    args = parser.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    asm = build_assembly()
    asm.save(str(out), exportType="STEP")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## Deliverable 3 — STEP file path

`/Users/Zhuanz/Desktop/case_018_stairmand_cyclone_separator/inputs/cad_codex_v1.step`

## Deliverable 4 — Parts manifest

```yaml
case_id: case_018_stairmand_cyclone_separator
cad_source: tier1_stairmand_high_efficiency_geometry (public literature, cadquery-generated)
generation_script: scripts/build_cad.py
step_file: /Users/Zhuanz/Desktop/case_018_stairmand_cyclone_separator/inputs/cad_codex_v1.step
units_in_step: mm

region:
  name: region_air
  role: fluid_volume

patches:
  - name: inlet_tangential
    bc_type: flowRateInletVelocity
    role: velocity_inlet
    U_inlet_m_s: 20
  - name: overflow_outlet
    bc_type: pressureOutlet
    role: pressure_outlet
    p_gauge_Pa: 0
  - name: underflow_outlet
    bc_type: pressureOutlet
    role: pressure_outlet
    p_gauge_Pa: 0
  - name: cyclone_walls
    bc_type: noSlip
    role: wall

bodies:
  - name: region_air
    role: fluid_region
  - name: debris_cube_d6
    role: defect_body

thermophysics:
  fluid: air_standard
  rho_kg_m3: 1.225
  mu_Pa_s: 1.8e-05
  T_ref_K: 300

particle:
  rho_p_kg_m3: 2650
  size_distribution:
    type: log_normal
    d_gm_um: 10
    gsd: 2.0
    span_um: [1, 50]
  mass_loading_g_m3: [10, 50]
  parcel_count: 5000
  wall_model: rebound
  outlet_model: escape

cyclone_operating_point:
  D_mm: 250
  U_inlet_m_s: 20
  Re_D: 333000
  swirl_number_target: 1.5
  d50_target_um: 4.0
  delta_p_target_kPa: [1.5, 2.5]

rsm_config:
  model: LaunderGibsonRSTM
  rationale: swirl-dominant cyclone flow is strongly anisotropic; RSM keeps Reynolds-stress tensor physics that k-epsilon / k-omega-SST smear out
  relaxation_factors:
    U: 0.3
    p: 0.2
    R: 0.35
    epsilon: 0.5

reference:
  geometry: Stairmand high-efficiency cyclone ratios (Stairmand 1951, reproduced in modern literature)
  citations:
    - https://www.researchgate.net/publication/364102715_Experimental_Analysis_of_Dual_Inlet_Cyclone_Separator
    - https://www.sciencedirect.com/science/article/pii/S0032591017305338
    - https://www.mdpi.com/2076-3417/11/12/5342
    - https://www.mdpi.com/2674-0516/2/3/38

patch_naming_check:
  - all names match ^[A-Za-z][A-Za-z0-9_]*$
  - no duplicate names
  - no spaces or hyphens
```

## Deliverable 5 — Defect manifest

```yaml
case_id: case_018_stairmand_cyclone_separator
defect_count: 1

defects:
  - id: D6
    status: QUESTIONABLE
    status_date: 2026-05-08
    description: floating 20 mm debris cube inside the collection chamber
    location:
      bodies_involved: [region_air, debris_cube_d6]
      coords_mm: [20.0, 0.0, -280.0]
      clearance_note: "placed in the lower cone / collection chamber, away from the inlet plane"
    measurement:
      claimed_size_mm: 20.0
      verification_command: "FreeCADCmd -c scripts/verify_d6_body_count.py"
    expected_advisor_to_catch: NONE
    advisor_gap_note: "no LANDED advisor for extra-body-in-fluid; manual FreeCAD body-count + bbox check required"
    hypothesized_v_series_match: "new stray-body / separator-ingest finding; compare to case_016 only if landed"
    reference_data_validity: preserved
```



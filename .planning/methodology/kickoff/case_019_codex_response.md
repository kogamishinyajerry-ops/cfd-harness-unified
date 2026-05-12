## Deliverable 1 — Engineering brief

- Component: Kenics static mixer, bank anchor `case_019_kenics_static_mixer` (Phase 4 queue row; Tier-3 fallback because no clean public STEP was found).
- Why: process-industry classic for RTD/COV and pressure-drop, and it cleanly extends case_003 to scalar transport.
- Question: what are RTD `F(t)`, outlet `COV`, and `Δp` for an 8-element Kenics mixer at `Re=3200` with a D2 over-dense 3rd element?
- Physics: `simpleFoam` steady flow + passive-scalar transport on the converged flow field; water, `Re=3200`, transitional RANS, `Sc_t=0.7`, passive scalar `T` as tracer.
- Parts: `region_fluid`, `mixer_element_1..8`, `pipe_inlet`, `pipe_outlet`, `pipe_wall`.
- BC plan: inlet `flowRateInletVelocity` (step tracer `T=1`), outlet `pressureOutlet`/`zeroGradient T`, walls `noSlip`/`zeroGradient T`.
- Expected metrics: outlet RTD `F(t)`, outlet `COV`, per-element and total `Δp`, scalar-field mixing map + `Q`-criterion.
- Failure modes: case_003 incompressible-RANS inheritance, V17/A3 redundancy gap on D2, scalar convergence slower than `U`, transitional stability near `Re≈2300`, curved-element meshing, `COV` time-window sensitivity.
- Defect: D2 on element 3, baseline ~5k tris, target 80k tris; expected advisor `geometry_surgery.decimate_to_tier`, status still `[QUESTIONABLE]` pending case_005/case_009 evidence.
- Effort: 8h.
- Sources: [Sulzer static mixers](https://www.sulzer.com/en/products/static-mixers), [Kenics 180° twist / L/D=1.5](https://www.sciencedirect.com/science/article/pii/S1385894798001454), [Kenics mixer flow structure](https://www.sciencedirect.com/science/article/pii/S1385894797000132), [COV/aspect-ratio study](https://www.mdpi.com/2227-9717/9/3/464).

## Deliverable 2 — CAD generation script
```python
#!/usr/bin/env python3
"""case_019_kenics_static_mixer · CAD generator (CadQuery)."""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path

import cadquery as cq

CASE_ID = "case_019_kenics_static_mixer"
PATCH_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

D_PIPE_MM = 80.0
N_ELEMENTS = 8
L_ELEMENT_FACTOR = 1.5
TWIST_ANGLE_DEG = 180.0
ROTATION_BETWEEN_ELEMENTS_DEG = 90.0
ELEMENT_THICKNESS_MM = 1.5
L_UPSTREAM_FACTOR = 3.0
L_DOWNSTREAM_FACTOR = 5.0

NOMINAL_SECTION_SLICES = 24
D2_TARGET_ELEMENT_INDEX = 3
D2_SECTION_SLICES = 240
D2_BASELINE_TRI_COUNT = 5000
D2_TARGET_TRI_COUNT = 80000

PART_NAMES = ["region_fluid"] + [f"mixer_element_{i}" for i in range(1, N_ELEMENTS + 1)]


def validate_names() -> None:
    seen = set()
    for name in PART_NAMES:
        if not PATCH_NAME_RE.match(name):
            raise ValueError(f"Invalid name: {name}")
        if name in seen:
            raise ValueError(f"Duplicate name: {name}")
        seen.add(name)


def pipe_radius_mm() -> float:
    return 0.5 * D_PIPE_MM


def element_length_mm() -> float:
    return L_ELEMENT_FACTOR * D_PIPE_MM


def total_length_mm() -> float:
    return (L_UPSTREAM_FACTOR + N_ELEMENTS * L_ELEMENT_FACTOR + L_DOWNSTREAM_FACTOR) * D_PIPE_MM


def build_element(index: int, n_slices: int) -> cq.Shape:
    """Thin sliced ribbon approximating a 180° Kenics helical element."""
    z0 = L_UPSTREAM_FACTOR * D_PIPE_MM + (index - 1) * element_length_mm()
    length = element_length_mm()
    r_center = 0.30 * D_PIPE_MM
    ribbon_width = 0.40 * D_PIPE_MM
    slice_len = length / n_slices

    slices = []
    for s in range(n_slices):
        frac = (s + 0.5) / n_slices
        z = z0 + frac * length
        theta = (index - 1) * ROTATION_BETWEEN_ELEMENTS_DEG + TWIST_ANGLE_DEG * frac
        x = r_center * math.cos(math.radians(theta))
        y = r_center * math.sin(math.radians(theta))

        # More slices on the defect element intentionally inflate tessellation density.
        piece = (
            cq.Workplane("XY")
            .box(slice_len * 0.98, ribbon_width, ELEMENT_THICKNESS_MM, centered=True)
            .rotate((0, 0, 0), (0, 0, 1), theta + 90.0)
            .translate((x, y, z))
            .val()
        )
        slices.append(piece)

    return cq.Compound.makeCompound(slices)


def build() -> cq.Assembly:
    validate_names()

    fluid = cq.Workplane("XY").circle(pipe_radius_mm()).extrude(total_length_mm())
    elements: list[cq.Shape] = []

    for i in range(1, N_ELEMENTS + 1):
        n_slices = D2_SECTION_SLICES if i == D2_TARGET_ELEMENT_INDEX else NOMINAL_SECTION_SLICES
        element = build_element(i, n_slices)
        elements.append(element)
        # Cut each mixer element out of the fluid body to create the single fluid region.
        fluid = fluid.cut(element)

    asm = cq.Assembly(name=CASE_ID)
    asm.add(fluid.val(), name="region_fluid")
    for i, element in enumerate(elements, 1):
        asm.add(element, name=f"mixer_element_{i}")
    return asm


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        default="/Users/Zhuanz/Desktop/case_019_kenics_static_mixer/inputs/cad_codex_v1.step",
    )
    args = parser.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    build().save(str(out), exportType="STEP")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## Deliverable 3 — STEP file path

- Target: `/Users/Zhuanz/Desktop/case_019_kenics_static_mixer/inputs/cad_codex_v1.step`

## Deliverable 4 — Parts manifest
```yaml
case_id: case_019_kenics_static_mixer
cad_source: Tier 3 parametric CadQuery fallback; informed by Sulzer public static-mixer pages and Kenics literature
generation_script: scripts/build_cad.py
step_file: inputs/cad_codex_v1.step
units_in_step: mm

region: region_fluid

patches:
  - name: pipe_inlet
    bc_type: flowRateInletVelocity
    scalar_T_bc: fixedValue_1_step
  - name: pipe_outlet
    bc_type: pressureOutlet
    scalar_T_bc: zeroGradient
  - name: pipe_wall
    bc_type: noSlip
    scalar_T_bc: zeroGradient
  - name: mixer_element_1
    bc_type: wall_noSlip
    scalar_T_bc: zeroGradient
  - name: mixer_element_2
    bc_type: wall_noSlip
    scalar_T_bc: zeroGradient
  - name: mixer_element_3
    bc_type: wall_noSlip
    scalar_T_bc: zeroGradient
  - name: mixer_element_4
    bc_type: wall_noSlip
    scalar_T_bc: zeroGradient
  - name: mixer_element_5
    bc_type: wall_noSlip
    scalar_T_bc: zeroGradient
  - name: mixer_element_6
    bc_type: wall_noSlip
    scalar_T_bc: zeroGradient
  - name: mixer_element_7
    bc_type: wall_noSlip
    scalar_T_bc: zeroGradient
  - name: mixer_element_8
    bc_type: wall_noSlip
    scalar_T_bc: zeroGradient

thermophysics:
  fluid: water_newtonian
  reference_temperature_K: 293.15
  rho_kg_m3: 998.2
  mu_Pa_s: 1.00e-3
  nu_m2_s: 1.00e-6

scalar_transport:
  field_name: T
  passive_scalar: true
  Sc_t: 0.7
  D_molecular_m2_s: 1.0e-9
  injection_method: step
  RTD_definition: F(t) = C_out(t) / C_in

mixer_operating_point:
  D_pipe_mm: 80
  N_elements: 8
  L_element_factor: 1.5
  twist_angle_deg: 180
  rotation_between_elements_deg: 90
  Re: 3200
  U_bulk_m_s: 0.040
  Q_m3_s: 2.01e-4
  inlet_profile: uniform_or_developed_profile

reference_targets:
  COV_target: "<= 0.05 typical; compare within ±15% to literature correlation"
  delta_p_target: "compare within ±15% to Kenics correlation"
  reference_sources:
    - https://www.sulzer.com/en/products/static-mixers
    - https://www.sciencedirect.com/science/article/pii/S1385894798001454
    - https://www.sciencedirect.com/science/article/pii/S1385894797000132
    - https://www.mdpi.com/2227-9717/9/3/464
```

## Deliverable 5 — Defect manifest
```yaml
case_id: case_019_kenics_static_mixer

defects:
  - id: D2_over_dense_triangulation
    target_element_index: 3
    baseline_tessellation_tri_count: 5000
    target_tessellation_tri_count: 80000
    expected_advisor: geometry_surgery.decimate_to_tier
    status: "[QUESTIONABLE 2026-05-08]: A3 is landed, but D2 redundancy-vs-decimation behavior still depends on case_005 V17 and case_009 D2."
    expected_if_case_009_confirms_A3: PASS
    expected_if_V17_remains_partial: PARTIAL + flag A3_v2
    verification_notes:
      - "Only one mixer element is overloaded."
      - "All other elements remain nominal."
      - "This is the under-utilized D2 stress-test for Phase 4 #3."
```

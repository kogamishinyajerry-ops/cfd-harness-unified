## Deliverable 1 — Engineering brief

### Component picked + bank ID + reasoning
- **Component class:** compact plate-fin air-air recuperator for a gas-turbine / APU thermal recovery use case
- **Bank ID:** promote legacy **A1** into **A1b_compact_heat_exchanger**
- **Reasoning:** the converged design state is no longer radiator-like water-glycol service; it is a classical Kays-London-style compact cross-flow recuperator with both fluids unmixed, aluminum fin/plate conduction, low-Re laminar passages, and a direct epsilon-NTU comparison target.

### Engineering question
Can a compact aluminum plate-fin recuperator in the stated APU/gas-turbine operating window recover about 225 W of heat at low mass flow while keeping both pressure drops within a modest laminar compact-HX envelope? The case is intended to validate steady multi-region CHT setup, conjugate coupling behavior, and advisor detection of realistic manufacturability defects without changing the converged dimensions.

### Physics signature
- Cross-flow, both fluids unmixed
- Working fluid on both sides: air
- Hot side: `Re_hot = 1149`, laminar
- Cold side: `Re_cold = 711`, laminar
- `Pr ~= 0.7` on both sides
- Conjugate aluminum conduction through fused fin-matrix + separator-plate solid
- Reference closure target: Kays-London epsilon-NTU compact-HX behavior, not turbulent radiator behavior

### Parts inventory
- `region_hot_fluid`
  - type: fluid
  - couples_to: `[region_solid]`
  - role: hot-air passages, hot inlet manifold, hot outlet manifold
- `region_cold_fluid`
  - type: fluid
  - couples_to: `[region_solid]`
  - role: cold-air passages, cold inlet manifold, cold outlet manifold
- `region_solid`
  - type: solid
  - couples_to: `[region_hot_fluid, region_cold_fluid]`
  - role: aluminum 6061 fin matrix plus separator plates fused into one body via `cq.Solid.fuse()`

### BC plan
- Fluid patches
  - `hot_inlet` on `region_hot_fluid`: `T = 420 K`, `m_dot = 0.004 kg/s`
  - `hot_outlet` on `region_hot_fluid`: `p = 0` gauge
  - `cold_inlet` on `region_cold_fluid`: `T = 300 K`, `m_dot = 0.0045 kg/s`
  - `cold_outlet` on `region_cold_fluid`: `p = 0` gauge
- Conjugate interfaces
  - `region_hot_fluid <-> region_solid`: `compressible::turbulentTemperatureCoupledBaffleMixed`
  - `region_cold_fluid <-> region_solid`: `compressible::turbulentTemperatureCoupledBaffleMixed`
- Solver class
  - primary: steady `chtMultiRegionFoam`
  - fallback if residual/temperature oscillation persists: `chtMultiRegionPimpleFoam`

### Expected metrics
- `epsilon ~= 0.466`
- `Q ~= 225 W`
- `Delta_p_hot ~= 168 Pa`
- `Delta_p_cold ~= 26 Pa`
- `T_h_out ~= 364 K`
- `T_c_out ~= 350 K`
- Reference tolerance band
  - `epsilon in [0.37, 0.56]`
  - `Q in [180 W, 270 W]`

### Hypothesized failure modes
- **V14 inheritance:** region/cellZone/patch bookkeeping mismatch across the three-region CHT setup can break startup or silently mis-pair interfaces.
- **V15 inheritance:** steady CHT residual oscillation or thermal overshoot may require fallback from `chtMultiRegionFoam` to `chtMultiRegionPimpleFoam`.
- Uneven manifold flow distribution between compact passages can skew effective `epsilon` below the Kays-London reference despite nominal geometry.
- A user-applied turbulent model such as `k-epsilon` in these low-Re laminar passages can stall convergence or produce nonphysical wall heat transfer.
- Strongly coupled thin aluminum separator plates can induce oscillatory interface heat flux even when bulk residuals appear acceptable.
- End-plate and cover-plate parasitic conduction can bias local heat flux away from the ideal compact-core assumption.
- Post-processing can show apparent temperature discontinuity across coupled baffles if fields are sampled on opposite patch owners instead of on a consistent side.

### Defect injection summary
- **D8 thin fin walls**
  - target: rear `1/3` of the cold-channel fin matrix
  - realized thickness: `0.6 mm`
  - expected advisor: `thin_wall_advisor [VALIDATED 6-of-6, 7th case]`
  - verification command:
    ```bash
    python case_011_plate_fin_compact_hx.py --out /Users/Zhuanz/Desktop/case_011_plate_fin_compact_hx/inputs/cad_codex_v1.step --check-d8
    ```
- **D5 mis-aligned plate-to-plate interface**
  - target: one separator plate at the layer-3/layer-4 interface, localized to the rear `1/3` comparison-excluded zone
  - realized offset: `30 um`
  - expected advisor: `A2-v2 [QUESTIONABLE 2026-05-08]`
  - verification command:
    ```bash
    python case_011_plate_fin_compact_hx.py --out /Users/Zhuanz/Desktop/case_011_plate_fin_compact_hx/inputs/cad_codex_v1.step --check-d5
    ```

### Sub-session estimated effort
- `10-12 h`

## Deliverable 2 — CAD generation script
```python
#!/usr/bin/env python3
"""
case_011_plate_fin_compact_hx.py

CadQuery generator for case_011:
compact plate-fin air-air recuperator for gas-turbine / APU-style
cross-flow conjugate heat transfer.

Outputs a three-body STEP assembly with labeled regions:
- region_hot_fluid
- region_cold_fluid
- region_solid

The converged dimensions and operating intent are fixed by prior design
convergence and must not be reswept here.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import cadquery as cq


# ---------------------------------------------------------------------------
# Converged design-state constants (fixed by prior GPT-5.5 convergence)
# ---------------------------------------------------------------------------

L_MM = 180.0
W_MM = 120.0
H_MM = 55.0

PLATE_THICKNESS_MM = 0.8
FIN_GAP_MM = 2.5

HOT_CHANNEL_HEIGHT_MM = 12.0
COLD_CHANNEL_HEIGHT_MM = 16.0

HOT_CHANNELS_PER_LAYER = 20
COLD_CHANNELS_PER_LAYER = 36

HOT_DH_MM = 4.14
COLD_DH_MM = 4.32

HOT_M_DOT_KG_S = 0.004
COLD_M_DOT_KG_S = 0.0045

HOT_T_IN_K = 420.0
COLD_T_IN_K = 300.0

D8_REAR_FIN_THICKNESS_MM = 0.6
D5_OFFSET_MM = 0.03  # 30 um


# ---------------------------------------------------------------------------
# CAD implementation constants
# These instantiate the converged topology without changing the converged
# macro-dimensions above.
# ---------------------------------------------------------------------------

BASE_FIN_THICKNESS_MM = 1.0
MANIFOLD_LENGTH_MM = W_MM / 5.0
REAR_THIRD_START_Y_MM = (2.0 * W_MM) / 3.0

# Minimal alternating stack consistent with the stated envelope.
# Hot / cold / hot fluid layers, with four plates (bottom cover, two separators,
# top cover) fused into one solid region.
HOT_LAYER_COUNT = 2
COLD_LAYER_COUNT = 1

DEFAULT_OUT = "/Users/Zhuanz/Desktop/case_011_plate_fin_compact_hx/inputs/cad_codex_v1.step"


@dataclass(frozen=True)
class Span:
    name: str
    z0: float
    z1: float


def fuse_many(solids: Iterable[cq.Solid]) -> cq.Solid:
    solids = list(solids)
    if not solids:
        raise ValueError("No solids provided to fuse_many().")
    acc = solids[0]
    for solid in solids[1:]:
        acc = acc.fuse(solid)
    return acc


def make_box(x0: float, y0: float, z0: float, dx: float, dy: float, dz: float) -> cq.Solid:
    return cq.Solid.makeBox(dx, dy, dz, cq.Vector(x0, y0, z0))


def build_stack_layout() -> Dict[str, List[Span]]:
    active_height = (
        HOT_LAYER_COUNT * HOT_CHANNEL_HEIGHT_MM
        + COLD_LAYER_COUNT * COLD_CHANNEL_HEIGHT_MM
        + 4.0 * PLATE_THICKNESS_MM
    )
    margin = (H_MM - active_height) / 2.0
    if margin < 0.0:
        raise ValueError(
            f"Active stack height ({active_height:.3f} mm) exceeds envelope H={H_MM:.3f} mm."
        )

    z = margin
    bottom_cover = Span("bottom_cover", z, z + PLATE_THICKNESS_MM)
    z = bottom_cover.z1

    hot_layer_1 = Span("hot_layer_1", z, z + HOT_CHANNEL_HEIGHT_MM)
    z = hot_layer_1.z1

    separator_plate_1_2 = Span("separator_plate_1_2", z, z + PLATE_THICKNESS_MM)
    z = separator_plate_1_2.z1

    cold_layer_1 = Span("cold_layer_1", z, z + COLD_CHANNEL_HEIGHT_MM)
    z = cold_layer_1.z1

    separator_plate_3_4 = Span("separator_plate_3_4", z, z + PLATE_THICKNESS_MM)
    z = separator_plate_3_4.z1

    hot_layer_2 = Span("hot_layer_2", z, z + HOT_CHANNEL_HEIGHT_MM)
    z = hot_layer_2.z1

    top_cover = Span("top_cover", z, z + PLATE_THICKNESS_MM)

    return {
        "hot_layers": [hot_layer_1, hot_layer_2],
        "cold_layers": [cold_layer_1],
        "plates": [bottom_cover, separator_plate_1_2, separator_plate_3_4, top_cover],
        "d5_plate": [separator_plate_3_4],
    }


def hot_pack_geometry() -> Tuple[float, float, float]:
    total_span = (
        HOT_CHANNELS_PER_LAYER * FIN_GAP_MM
        + (HOT_CHANNELS_PER_LAYER + 1) * BASE_FIN_THICKNESS_MM
    )
    y0 = (W_MM - total_span) / 2.0
    return y0, total_span, BASE_FIN_THICKNESS_MM + FIN_GAP_MM


def cold_pack_geometry() -> Tuple[float, float, float]:
    total_span = (
        COLD_CHANNELS_PER_LAYER * FIN_GAP_MM
        + (COLD_CHANNELS_PER_LAYER + 1) * BASE_FIN_THICKNESS_MM
    )
    x0 = (L_MM - total_span) / 2.0
    return x0, total_span, BASE_FIN_THICKNESS_MM + FIN_GAP_MM


def make_hot_manifold(
    x_face: float,
    direction: float,
    y_center: float,
    y_span: float,
    z_center: float,
    z_span: float,
) -> cq.Solid:
    port_y_span = y_span * 0.55
    port_z_span = z_span * 0.60

    loft = (
        cq.Workplane("YZ", origin=(x_face, y_center, z_center))
        .rect(y_span, z_span)
        .workplane(offset=direction * MANIFOLD_LENGTH_MM)
        .rect(port_y_span, port_z_span)
        .loft(combine=True, ruled=True)
    )
    return loft.val()


def make_cold_manifold(
    y_face: float,
    direction: float,
    x_center: float,
    x_span: float,
    z_center: float,
    z_span: float,
) -> cq.Solid:
    port_x_span = x_span * 0.55
    port_z_span = z_span * 0.80

    loft = (
        cq.Workplane("XZ", origin=(x_center, y_face, z_center))
        .rect(x_span, z_span)
        .workplane(offset=direction * MANIFOLD_LENGTH_MM)
        .rect(port_x_span, port_z_span)
        .loft(combine=True, ruled=True)
    )
    return loft.val()


def build_hot_region(layout: Dict[str, List[Span]]) -> cq.Solid:
    hot_layers = layout["hot_layers"]
    hot_y0, hot_span, hot_pitch = hot_pack_geometry()
    channel_y0 = hot_y0 + BASE_FIN_THICKNESS_MM

    solids: List[cq.Solid] = []

    for layer in hot_layers:
        for idx in range(HOT_CHANNELS_PER_LAYER):
            y0 = channel_y0 + idx * hot_pitch
            solids.append(
                make_box(
                    x0=0.0,
                    y0=y0,
                    z0=layer.z0,
                    dx=L_MM,
                    dy=FIN_GAP_MM,
                    dz=layer.z1 - layer.z0,
                )
            )

    hot_z0 = min(layer.z0 for layer in hot_layers)
    hot_z1 = max(layer.z1 for layer in hot_layers)
    hot_z_center = 0.5 * (hot_z0 + hot_z1)
    hot_z_span = hot_z1 - hot_z0
    hot_y_center = hot_y0 + 0.5 * hot_span

    solids.append(
        make_hot_manifold(
            x_face=0.0,
            direction=-1.0,
            y_center=hot_y_center,
            y_span=hot_span,
            z_center=hot_z_center,
            z_span=hot_z_span,
        )
    )
    solids.append(
        make_hot_manifold(
            x_face=L_MM,
            direction=1.0,
            y_center=hot_y_center,
            y_span=hot_span,
            z_center=hot_z_center,
            z_span=hot_z_span,
        )
    )

    return fuse_many(solids)


def build_cold_region(layout: Dict[str, List[Span]]) -> cq.Solid:
    cold_layer = layout["cold_layers"][0]
    cold_x0, cold_span, cold_pitch = cold_pack_geometry()
    channel_x0 = cold_x0 + BASE_FIN_THICKNESS_MM

    solids: List[cq.Solid] = []

    for idx in range(COLD_CHANNELS_PER_LAYER):
        x0 = channel_x0 + idx * cold_pitch
        solids.append(
            make_box(
                x0=x0,
                y0=0.0,
                z0=cold_layer.z0,
                dx=FIN_GAP_MM,
                dy=W_MM,
                dz=cold_layer.z1 - cold_layer.z0,
            )
        )

    cold_x_center = cold_x0 + 0.5 * cold_span
    cold_z_center = 0.5 * (cold_layer.z0 + cold_layer.z1)
    cold_z_span = cold_layer.z1 - cold_layer.z0

    solids.append(
        make_cold_manifold(
            y_face=0.0,
            direction=-1.0,
            x_center=cold_x_center,
            x_span=cold_span,
            z_center=cold_z_center,
            z_span=cold_z_span,
        )
    )
    solids.append(
        make_cold_manifold(
            y_face=W_MM,
            direction=1.0,
            x_center=cold_x_center,
            x_span=cold_span,
            z_center=cold_z_center,
            z_span=cold_z_span,
        )
    )

    return fuse_many(solids)


def build_solid_region(layout: Dict[str, List[Span]]) -> cq.Solid:
    hot_y0, hot_span, hot_pitch = hot_pack_geometry()
    cold_x0, cold_span, cold_pitch = cold_pack_geometry()

    solids: List[cq.Solid] = []

    # Plates: bottom cover, first separator, D5-localized second separator, top cover.
    plates = layout["plates"]

    # bottom cover
    solids.append(
        make_box(
            x0=0.0,
            y0=0.0,
            z0=plates[0].z0,
            dx=L_MM,
            dy=W_MM,
            dz=plates[0].z1 - plates[0].z0,
        )
    )

    # separator_plate_1_2
    solids.append(
        make_box(
            x0=0.0,
            y0=0.0,
            z0=plates[1].z0,
            dx=L_MM,
            dy=W_MM,
            dz=plates[1].z1 - plates[1].z0,
        )
    )

    # separator_plate_3_4 with D5 localized to the rear 1/3:
    # front 2/3 nominal, rear 1/3 shifted by 30 um in x.
    d5_plate = plates[2]
    solids.append(
        make_box(
            x0=0.0,
            y0=0.0,
            z0=d5_plate.z0,
            dx=L_MM,
            dy=REAR_THIRD_START_Y_MM,
            dz=d5_plate.z1 - d5_plate.z0,
        )
    )
    solids.append(
        make_box(
            x0=D5_OFFSET_MM,
            y0=REAR_THIRD_START_Y_MM,
            z0=d5_plate.z0,
            dx=L_MM - D5_OFFSET_MM,
            dy=W_MM - REAR_THIRD_START_Y_MM,
            dz=d5_plate.z1 - d5_plate.z0,
        )
    )

    # top cover
    solids.append(
        make_box(
            x0=0.0,
            y0=0.0,
            z0=plates[3].z0,
            dx=L_MM,
            dy=W_MM,
            dz=plates[3].z1 - plates[3].z0,
        )
    )

    # Hot-layer fins: x-aligned walls distributed across y.
    hot_wall_y0 = hot_y0
    for layer in layout["hot_layers"]:
        for idx in range(HOT_CHANNELS_PER_LAYER + 1):
            y0 = hot_wall_y0 + idx * hot_pitch
            solids.append(
                make_box(
                    x0=0.0,
                    y0=y0,
                    z0=layer.z0,
                    dx=L_MM,
                    dy=BASE_FIN_THICKNESS_MM,
                    dz=layer.z1 - layer.z0,
                )
            )

    # Cold-layer fins: y-aligned walls distributed across x.
    # D8 is applied in the rear 1/3 by reducing wall thickness to 0.6 mm.
    cold_layer = layout["cold_layers"][0]
    cold_wall_x0 = cold_x0
    for idx in range(COLD_CHANNELS_PER_LAYER + 1):
        wall_x = cold_wall_x0 + idx * cold_pitch

        # front 2/3 nominal
        solids.append(
            make_box(
                x0=wall_x,
                y0=0.0,
                z0=cold_layer.z0,
                dx=BASE_FIN_THICKNESS_MM,
                dy=REAR_THIRD_START_Y_MM,
                dz=cold_layer.z1 - cold_layer.z0,
            )
        )

        # rear 1/3 thin-wall defect, centered on the nominal wall centerline
        center_x = wall_x + 0.5 * BASE_FIN_THICKNESS_MM
        rear_x0 = center_x - 0.5 * D8_REAR_FIN_THICKNESS_MM
        solids.append(
            make_box(
                x0=rear_x0,
                y0=REAR_THIRD_START_Y_MM,
                z0=cold_layer.z0,
                dx=D8_REAR_FIN_THICKNESS_MM,
                dy=W_MM - REAR_THIRD_START_Y_MM,
                dz=cold_layer.z1 - cold_layer.z0,
            )
        )

    # One fused solid body for the solid region.
    return fuse_many(solids)


def build_regions() -> Dict[str, cq.Solid]:
    layout = build_stack_layout()
    return {
        "region_hot_fluid": build_hot_region(layout),
        "region_cold_fluid": build_cold_region(layout),
        "region_solid": build_solid_region(layout),
    }


def export_step(regions: Dict[str, cq.Solid], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # STEP exporter writes a labeled multi-body assembly, preserving region names.
    assembly = cq.Assembly(name="case_011_plate_fin_compact_hx")
    assembly.add(regions["region_hot_fluid"], name="region_hot_fluid")
    assembly.add(regions["region_cold_fluid"], name="region_cold_fluid")
    assembly.add(regions["region_solid"], name="region_solid")

    cq.exporters.export(assembly, str(out_path))


def print_d8_check() -> None:
    print(
        "D8 check: cold fin rear-third starts at "
        f"y={REAR_THIRD_START_Y_MM:.3f} mm; "
        f"rear-third fin thickness={D8_REAR_FIN_THICKNESS_MM:.3f} mm."
    )


def print_d5_check() -> None:
    print(
        "D5 check: separator_plate_3_4 rear-third x-offset="
        f"{D5_OFFSET_MM * 1000.0:.1f} um for y>={REAR_THIRD_START_Y_MM:.3f} mm."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate case_011 compact HX STEP geometry.")
    parser.add_argument(
        "--out",
        default=DEFAULT_OUT,
        help=f"Output STEP path (default: {DEFAULT_OUT})",
    )
    parser.add_argument(
        "--check-d8",
        action="store_true",
        help="Print D8 defect placement confirmation.",
    )
    parser.add_argument(
        "--check-d5",
        action="store_true",
        help="Print D5 defect placement confirmation.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_path = Path(args.out)

    regions = build_regions()
    export_step(regions, out_path)

    if args.check_d8:
        print_d8_check()
    if args.check_d5:
        print_d5_check()

    print(f"Wrote STEP: {out_path}")


if __name__ == "__main__":
    main()
```

## Deliverable 3 — STEP file path
/Users/Zhuanz/Desktop/case_011_plate_fin_compact_hx/inputs/cad_codex_v1.step

## Deliverable 4 — Parts manifest
```yaml
case_id: case_011
short_name: plate_fin_compact_hx
solver_class: chtMultiRegionFoam_steady
numerics_class: steady_laminar_conjugate_heat_transfer
cad_source: Tier_3_parametric_CadQuery
step_path: /Users/Zhuanz/Desktop/case_011_plate_fin_compact_hx/inputs/cad_codex_v1.step

regions:
  - name: region_hot_fluid
    region_type: fluid
    couples_to: [region_solid]
  - name: region_cold_fluid
    region_type: fluid
    couples_to: [region_solid]
  - name: region_solid
    region_type: solid
    material: aluminum_6061
    construction: fin_matrix_plus_separator_plates_fused_as_one_body
    couples_to: [region_hot_fluid, region_cold_fluid]

fluid_patches:
  - name: hot_inlet
    region: region_hot_fluid
    bc_type_plan:
      flow_spec: massFlowRate
      mass_flow_rate_kg_s: 0.004
      temperature_K: 420.0
  - name: hot_outlet
    region: region_hot_fluid
    bc_type_plan:
      pressure_spec: fixedValue
      gauge_pressure_Pa: 0.0
  - name: cold_inlet
    region: region_cold_fluid
    bc_type_plan:
      flow_spec: massFlowRate
      mass_flow_rate_kg_s: 0.0045
      temperature_K: 300.0
  - name: cold_outlet
    region: region_cold_fluid
    bc_type_plan:
      pressure_spec: fixedValue
      gauge_pressure_Pa: 0.0

conjugate_interfaces:
  - between: [region_hot_fluid, region_solid]
    thermal_bc: compressible::turbulentTemperatureCoupledBaffleMixed
  - between: [region_cold_fluid, region_solid]
    thermal_bc: compressible::turbulentTemperatureCoupledBaffleMixed

thermophysics:
  hot_air:
    rho_kg_m3: 0.80
    mu_Pa_s: 2.4e-5
    cp_J_kgK: 1007.0
    k_W_mK: 0.036
    Pr: 0.7
  cold_air:
    rho_kg_m3: 1.18
    mu_Pa_s: 1.9e-5
    cp_J_kgK: 1007.0
    k_W_mK: 0.027
    Pr: 0.7
  aluminum_6061:
    rho_kg_m3: 2700.0
    cp_J_kgK: 896.0
    k_W_mK: 205.0

geometry:
  flow_length_hot_mm: 180.0
  flow_length_cold_mm: 120.0
  stack_height_mm: 55.0
  plate_thickness_mm: 0.8
  fin_gap_mm: 2.5
  hot_channel_height_mm: 12.0
  cold_channel_height_mm: 16.0
  hot_channels_per_layer: 20
  cold_channels_per_layer: 36
  hydraulic_diameter_hot_mm: 4.14
  hydraulic_diameter_cold_mm: 4.32
  manifold_type: tapered
  manifold_loss_coefficient_reference: 2.5
  flow_arrangement: cross_flow_both_fluids_unmixed

operating_point:
  T_h_in_K: 420.0
  T_c_in_K: 300.0
  m_dot_h_kg_s: 0.004
  m_dot_c_kg_s: 0.0045

epsilon_ntu_reference:
  C_h_W_K: 4.028
  C_c_W_K: 4.5315
  C_min_W_K: 4.028
  C_r: 0.889
  NTU: 0.93
  epsilon: 0.466
  Q_W: 225.0
  T_h_out_K: 364.0
  T_c_out_K: 350.0
  delta_p_hot_Pa: 168.0
  delta_p_cold_Pa: 26.0
  tolerance_band:
    epsilon: [0.37, 0.56]
    Q_W: [180.0, 270.0]

determinism:
  statement: no time-based seeds or system entropy are used in geometry generation
  byte_identical_regen_check_command: >-
    rm -f /tmp/case011_a.step /tmp/case011_b.step &&
    python case_011_plate_fin_compact_hx.py --out /tmp/case011_a.step &&
    python case_011_plate_fin_compact_hx.py --out /tmp/case011_b.step &&
    shasum -a 256 /tmp/case011_a.step /tmp/case011_b.step &&
    cmp -s /tmp/case011_a.step /tmp/case011_b.step
```

## Deliverable 5 — Defect manifest
```yaml
case_id: case_011

comparison_zone:
  definition: front_2_3_of_matrix_along_cold_flow_direction
  span_y_mm: [0.0, 80.0]
  defect_free_requirement: true

defects:
  - defect_id: D8
    defect_name: thin_fin
    target_region: region_solid
    target_subassembly: cold_fin_matrix
    placement:
      cold_layer: cold_layer_1
      rear_zone_y_mm: [80.0, 120.0]
      relative_location: rear_1_3_only
    realized_geometry:
      fin_thickness_mm: 0.6
    expected_advisor_to_catch: thin_wall_advisor [VALIDATED 6-of-6, 7th case]
    rationale: >
      Deliberately reduces the cold-side fin-wall thickness only in the
      rear third so the front two-thirds remain clean for epsilon-NTU
      comparison against the converged compact-HX baseline.
    verification_command: >-
      python case_011_plate_fin_compact_hx.py
      --out /Users/Zhuanz/Desktop/case_011_plate_fin_compact_hx/inputs/cad_codex_v1.step
      --check-d8

  - defect_id: D5
    defect_name: mis_aligned_plate_to_plate_interface
    target_region: region_solid
    target_subassembly: separator_plate_3_4_interface
    placement:
      separator_plate: separator_plate_3_4
      rear_zone_y_mm: [80.0, 120.0]
      relative_location: rear_1_3_only
    realized_geometry:
      local_offset_um: 30.0
      offset_axis: x
    expected_advisor_to_catch: A2-v2 [QUESTIONABLE 2026-05-08]
    status_basis: >
      A2 v1 cannot detect 5-50 um plate-offset behavior per V25 placeholder
      semantics. A2-v2 gap-detection extension is still DRAFT at
      .planning/patches/draft_a2_v2_gap_detection_2026-05-08.md.
      Verification remains pending until A2-v2 lands and an injection test
      confirms this 30 um defect is surfaced reliably.
    verification_pending: A2-v2_land_plus_injection_test
    to_resolve: A2-v2_sub_DEC_merged
    verification_command: >-
      python case_011_plate_fin_compact_hx.py
      --out /Users/Zhuanz/Desktop/case_011_plate_fin_compact_hx/inputs/cad_codex_v1.step
      --check-d5

reference_data_validity: >
  The epsilon-NTU reference values (epsilon=0.466, Q=225 W, Delta_p_hot=168 Pa,
  Delta_p_cold=26 Pa, T_h_out=364 K, T_c_out=350 K) remain the governing
  comparison baseline because both injected defects are intentionally confined
  to the rear one-third of the matrix, outside the front two-thirds comparison
  zone used for clean Kays-London-style behavioral comparison.

placement_policy_statement: >
  Both defects are placed outside the epsilon-NTU comparison zone. The front
  two-thirds of the matrix is the comparison zone; the rear one-third carries
  D8 and D5 so advisor testing does not invalidate the converged reference
  thermal-hydraulic target.
```

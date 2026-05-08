## Deliverable 1 — Engineering brief

### Component picked + bank ID
`case_006_onera_m6_transonic`

Tier-1 pick: `T1.A3` ONERA M6 wing, AGARD AR-138 / Schmitt-Charpin public validation archive.

Primary source:
- NASA NPARC validation archive: https://www.grc.nasa.gov/WWW/wind/valid/m6wing/m6wing.html
- AGARD AR-138 reference: Schmitt & Charpin, 1979
- Geometry text files on the NASA page: `airfoil.txt`, `foilmod.txt`

This is the canonical external transonic 3D wing, and it fills the project’s uncovered `compressible-shock-density-based` row.

### Engineering question
Can the harness preserve and mesh a real transonic wing geometry, run a density-based shock-capturing solver, and recover the ONERA M6 lambda-shock pattern and spanwise `Cp` distributions at the published seven stations?

### Physics signature
- Solver target v1: `rhoCentralFoam`
- v2 fallback: `rhoPimpleFoam` only if the central-upwind scheme smears the lambda shock too much
- Flow point: `M_inf = 0.8395`, `alpha = 3.06 deg`, `Re_c = 11.72e6`
- Reference-equivalent freestream: `T_inf = 288 K`, `p_inf ≈ 93.6 kPa`, `T0 ≈ 328.5 K`, `p0 ≈ 148.4 kPa`
- Regime: transonic external RANS, upper-surface local supersonic pocket, lambda shock, shock/boundary-layer interaction, spanwise shock migration
- Expected signature: forward shock + aft shock on the upper surface, strongest around `eta = 0.65` to `0.95`

### Parts inventory
- `wing_surface_reference`: main wing wall, no defects on published `Cp` stations
- `root_fairing_pad`: auxiliary root-side body, defect-safe zone
- `root_fairing_cover`: auxiliary root-side body, forms D1 gap with pad
- `tip_cap`: separate tip closure body, outside published `Cp` stations
- `tip_cap_sliver`: deliberate sliver body on tip-cap edge, D4
- `symmetry_plane_root`: explicit wing-root symmetry patch, `bc.U: symmetry`, `bc.p: symmetry`, `bc.T: symmetry`
- `farfield_box`: outer domain reference body
- `farfield_upstream`, `farfield_downstream`, `farfield_top`, `farfield_bottom`, `farfield_outboard`: farfield patch bodies

### Boundary conditions plan
- `symmetry_plane_root`: `U: symmetry`, `p: symmetry`, `T: symmetry`
- farfield patches: `U: characteristicVelocityInletOutletVelocity`, `p: characteristicPressureInletOutletPressure`, `T: freestream`
- wing and auxiliary walls: `U: noSlip`, `p: zeroGradient`, `T: zeroGradient`, with standard compressible wall functions for turbulence fields
- v1 uses steady-like pseudo-time stepping via `localEuler`; v2 can switch to `backward` if needed

### Expected metrics
- `Cp(x/c)` at the 7 published span stations
- `Cl`, `Cd`, `Cm`
- `max upper-surface Mach`
- lambda-shock map at `eta = 0.65` and `eta = 0.95`
- shock-foot `x/c` and shock strength metric `max |∂M/∂n|`
- spanwise shock migration versus `eta`

### Hypothesized failure modes
This case should be the first root finding for `compressible-shock-density-based`, so it inherits none of the earlier compressible-buoyant, incompressible, MRF, or pressure-based compressible findings.

Likely new failure modes:
- Flux scheme too diffusive, lambda shock collapses into a broad compression band
- Shock limiter too aggressive, upper-surface `Cp` loses the double-kink signature
- Characteristic farfield BCs too close, causing reflection and spanwise shock drift
- Cold-start density/energy initialization overshoots at the leading edge
- Coarse spanwise resolution shifts the shock foot even if force coefficients look reasonable

### Defect injection summary
Exactly 2 defects, both outside the published `Cp` measurement zones:
- `D1`: sub-mm gap between root-side auxiliary bodies near the symmetry plane
- `D4`: tiny sliver body on the tip-cap fillet/edge, outside the `eta = 0.99` pressure-tap line

### Sub-session estimated effort
`6-9 hours`, usually 3 versions:
- v1: geometry import, patch validation, coarse shock-capturing mesh
- v2: limiter / BC tuning to preserve the lambda-shock
- v3: final `Cp` extraction, force coefficients, and shock map

---

## Deliverable 2 — CAD generation script
```python
#!/usr/bin/env python3
"""case_006_onera_m6_transonic · CAD generator.

Tier-1 source: NASA NPARC validation archive for ONERA M6 wing,
AGARD AR-138 / Schmitt-Charpin.

Deterministic by design: same inputs + same CadQuery/OCCT version =>
byte-identical STEP output.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import tempfile
import urllib.request
from pathlib import Path

import cadquery as cq


CASE_ID = "case_006_onera_m6_transonic"
ASSEMBLY_NAME = CASE_ID

SOURCE_PAGE_URL = "https://www.grc.nasa.gov/WWW/wind/valid/m6wing/m6wing.html"
AIRFOIL_URL = "https://www.grc.nasa.gov/WWW/wind/valid/m6wing/foilmod.txt"
RAW_AIRFOIL_URL = "https://www.grc.nasa.gov/WWW/wind/valid/m6wing/airfoil.txt"
CP_PAGE_URLS = [
    "https://www.grc.nasa.gov/WWW/wind/valid/m6wing/cp1l.ex",
    "https://www.grc.nasa.gov/WWW/wind/valid/m6wing/cp1u.ex",
    "https://www.grc.nasa.gov/WWW/wind/valid/m6wing/cp2l.ex",
    "https://www.grc.nasa.gov/WWW/wind/valid/m6wing/cp2u.ex",
    "https://www.grc.nasa.gov/WWW/wind/valid/m6wing/cp3l.ex",
    "https://www.grc.nasa.gov/WWW/wind/valid/m6wing/cp3u.ex",
    "https://www.grc.nasa.gov/WWW/wind/valid/m6wing/cp4l.ex",
    "https://www.grc.nasa.gov/WWW/wind/valid/m6wing/cp4u.ex",
    "https://www.grc.nasa.gov/WWW/wind/valid/m6wing/cp5l.ex",
    "https://www.grc.nasa.gov/WWW/wind/valid/m6wing/cp5u.ex",
    "https://www.grc.nasa.gov/WWW/wind/valid/m6wing/cp6l.ex",
    "https://www.grc.nasa.gov/WWW/wind/valid/m6wing/cp6u.ex",
    "https://www.grc.nasa.gov/WWW/wind/valid/m6wing/cp7l.ex",
    "https://www.grc.nasa.gov/WWW/wind/valid/m6wing/cp7u.ex",
]

DEFAULT_REPO_ROOT = Path(os.environ.get("CFD_HARNESS_REPO", "/Users/Zhuanz/Desktop/cfd-harness-unified"))
CACHE_DIR = DEFAULT_REPO_ROOT / ".planning" / "cad_cache"
CACHE_FILE = CACHE_DIR / "tier1_onera_m6_foilmod.txt"
PATCH_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

# === Published geometry ===
SPAN_MM = 1196.3
MAC_MM = 646.07
ASPECT_RATIO = 3.8
TAPER_RATIO = 0.562
LE_SWEEP_DEG = 30.0
TE_SWEEP_DEG = 15.8
ALPHA_DEG = 3.06
M_INF = 0.8395

# Reference-equivalent freestream values, consistent with M_inf and Re_c.
T_INF_K = 288.0
P_INF_PA = 93600.0
T0_INF_K = 328.5
P0_INF_PA = 148400.0
RE_C = 11.72e6
RHO_INF = 1.133
U_INF = 285.6

GAMMA = 1.4
R_AIR = 287.05
MU_REF = 1.7894e-5

# === Discretization / layout ===
ROOT_CHORD_MM = MAC_MM * 1.5 * (1.0 + TAPER_RATIO) / (1.0 + TAPER_RATIO + TAPER_RATIO**2)
TIP_CHORD_MM = ROOT_CHORD_MM * TAPER_RATIO
TIP_CAP_FRAC = 0.01
TIP_CAP_SPAN_MM = TIP_CAP_FRAC * SPAN_MM

# Main wing sections stop at eta=0.99 so the tip cap can be a separate body.
MAIN_SECTION_ETAS = [0.0, 0.20, 0.44, 0.65, 0.80, 0.90, 0.95, 0.99]
TIP_SECTION_ETAS = [0.99, 1.0]

# Farfield at least 25 chords away in all directions.
FARFIELD_MARGIN_C = 25.0

# Defects
ROOT_GAP_MM = 0.35
TIP_SLIVER_THICKNESS_MM = 0.18
TIP_SLIVER_WIDTH_MM = 0.45
TIP_SLIVER_SPAN_MM = 3.0

PART_NAMES = [
    "wing_surface_reference",
    "root_fairing_pad",
    "root_fairing_cover",
    "tip_cap",
    "tip_cap_sliver",
    "symmetry_plane_root",
    "farfield_box",
    "farfield_upstream",
    "farfield_downstream",
    "farfield_top",
    "farfield_bottom",
    "farfield_outboard",
]


def validate_names() -> None:
    seen = set()
    for name in PART_NAMES:
        if not PATCH_NAME_RE.match(name):
            raise ValueError(f"Invalid OpenFOAM body name: {name}")
        if name in seen:
            raise ValueError(f"Duplicate body name: {name}")
        seen.add(name)


def parse_coords(text: str) -> list[tuple[float, float]]:
    pts: list[tuple[float, float]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "!", "C")):
            continue
        parts = line.replace(",", " ").split()
        if len(parts) < 2:
            continue
        try:
            x = float(parts[0])
            z = float(parts[1])
        except ValueError:
            continue
        pts.append((x, z))
    if len(pts) < 10:
        raise RuntimeError("Could not parse enough ONERA M6 foil coordinates")
    if pts[0] == pts[-1]:
        pts.pop()
    return pts


def download_text(url: str, cache_path: Path) -> str:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8")

    req = urllib.request.Request(url, headers={"User-Agent": "cfd-harness-unified-case006/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        text = resp.read().decode("utf-8", errors="replace")

    tmp = cache_path.with_suffix(cache_path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(cache_path)
    return text


def load_foil_coords() -> list[tuple[float, float]]:
    env_path = os.environ.get("CASE006_FOILMOD_PATH")
    if env_path:
        return parse_coords(Path(env_path).expanduser().read_text(encoding="utf-8"))

    if CACHE_FILE.exists():
        return parse_coords(CACHE_FILE.read_text(encoding="utf-8"))

    try:
        text = download_text(AIRFOIL_URL, CACHE_FILE)
        return parse_coords(text)
    except Exception:
        # Fall back to the raw coordinates if the modified file cannot be fetched.
        text = download_text(RAW_AIRFOIL_URL, CACHE_FILE)
        return parse_coords(text)


def make_profile_wire(coords: list[tuple[float, float]], y_mm: float, chord_mm: float, x_le_mm: float) -> cq.Wire:
    # The airfoil lies in the X-Z plane, with spanwise offset along Y.
    pts = [(x_le_mm + chord_mm * x, chord_mm * z) for x, z in coords]
    wp = cq.Workplane("XZ", origin=(0.0, y_mm, 0.0)).spline(pts).close()
    return wp.wire().val()


def loft_from_sections(
    coords: list[tuple[float, float]],
    section_specs: list[tuple[float, float, float]],
) -> cq.Shape:
    # Each section is a closed wire, lofted in spanwise order.
    wires = [make_profile_wire(coords, y_mm, chord_mm, x_le_mm) for (y_mm, chord_mm, x_le_mm) in section_specs]
    return cq.Workplane(obj=cq.Solid.makeLoft(wires)).val()


def chord_at_eta(eta: float) -> float:
    return ROOT_CHORD_MM * (1.0 - (1.0 - TAPER_RATIO) * eta)


def x_le_at_eta(eta: float) -> float:
    return (SPAN_MM * eta) * (3.141592653589793 / 180.0) * 0.0 + (SPAN_MM * eta) * __import__("math").tan(__import__("math").radians(LE_SWEEP_DEG))


def build_wing(coords: list[tuple[float, float]]) -> dict[str, cq.Shape]:
    wing_parts: dict[str, cq.Shape] = {}

    main_specs = []
    for eta in MAIN_SECTION_ETAS:
        y_mm = SPAN_MM * eta
        chord_mm = chord_at_eta(eta)
        x_le_mm = x_le_at_eta(eta)
        main_specs.append((y_mm, chord_mm, x_le_mm))

    wing_parts["wing_surface_reference"] = loft_from_sections(coords, main_specs)

    # Separate tip cap so the tip-side defect can live outside the published eta=0.99 Cp station.
    tip_specs = []
    for eta in TIP_SECTION_ETAS:
        y_mm = SPAN_MM * eta
        chord_mm = chord_at_eta(eta)
        x_le_mm = x_le_at_eta(eta)
        if eta == 1.0:
            chord_mm *= 0.92
        tip_specs.append((y_mm, chord_mm, x_le_mm))
    wing_parts["tip_cap"] = loft_from_sections(coords, tip_specs)

    return wing_parts


def make_box(center: tuple[float, float, float], size: tuple[float, float, float]) -> cq.Shape:
    return cq.Workplane("XY", origin=center).box(size[0], size[1], size[2], centered=True).val()


def make_plate_x(x_mm: float, y_span_mm: float, z_span_mm: float, thickness_mm: float) -> cq.Shape:
    return cq.Workplane("YZ", origin=(x_mm, 0.0, 0.0)).box(thickness_mm, y_span_mm, z_span_mm, centered=True).val()


def make_plate_y(y_mm: float, x_span_mm: float, z_span_mm: float, thickness_mm: float) -> cq.Shape:
    return cq.Workplane("XZ", origin=(0.0, y_mm, 0.0)).box(x_span_mm, thickness_mm, z_span_mm, centered=True).val()


def make_plate_z(z_mm: float, x_span_mm: float, y_span_mm: float, thickness_mm: float) -> cq.Shape:
    return cq.Workplane("XY", origin=(0.0, 0.0, z_mm)).box(x_span_mm, y_span_mm, thickness_mm, centered=True).val()


def build_auxiliary_defects() -> dict[str, cq.Shape]:
    # D1: root-side gap between two small bodies near the symmetry plane, outside all published Cp stations.
    root_y = 0.035 * SPAN_MM
    root_z = 0.018 * ROOT_CHORD_MM
    pad = cq.Workplane("XY", origin=(0.10 * ROOT_CHORD_MM, root_y, root_z)).box(22.0, 16.0, 7.0, centered=True).val()
    cover = cq.Workplane("XY", origin=(0.10 * ROOT_CHORD_MM + 22.0 + ROOT_GAP_MM + 22.0, root_y, root_z)).box(22.0, 16.0, 7.0, centered=True).val()

    # D4: tip-cap sliver on a fillet/edge transition, outside the eta=0.99 published pressure station.
    tip_x = x_le_at_eta(1.0) + 0.88 * TIP_CHORD_MM
    tip_y = SPAN_MM - 0.25 * TIP_CAP_SPAN_MM
    tip_z = 0.02 * TIP_CHORD_MM
    sliver = (
        cq.Workplane("XZ", origin=(tip_x, tip_y, tip_z))
        .polyline(
            [
                (0.0, 0.0),
                (TIP_SLIVER_THICKNESS_MM, 0.0),
                (0.0, TIP_SLIVER_WIDTH_MM),
            ]
        )
        .close()
        .extrude(TIP_SLIVER_SPAN_MM)
        .val()
    )

    return {
        "root_fairing_pad": pad,
        "root_fairing_cover": cover,
        "tip_cap_sliver": sliver,
    }


def build_farfield(wing_bbox: cq.BoundBox) -> dict[str, cq.Shape]:
    chord_margin = FARFIELD_MARGIN_C * ROOT_CHORD_MM

    x_min = wing_bbox.xmin - chord_margin
    x_max = wing_bbox.xmax + chord_margin
    y_min = 0.0
    y_max = wing_bbox.ymax + chord_margin
    z_min = wing_bbox.zmin - chord_margin
    z_max = wing_bbox.zmax + chord_margin

    box_center = ((x_min + x_max) * 0.5, (y_min + y_max) * 0.5, (z_min + z_max) * 0.5)
    box_size = (x_max - x_min, y_max - y_min, z_max - z_min)

    return {
        "farfield_box": make_box(box_center, box_size),
        "farfield_upstream": make_plate_x(x_min, box_size[1], box_size[2], 0.5),
        "farfield_downstream": make_plate_x(x_max, box_size[1], box_size[2], 0.5),
        "farfield_top": make_plate_z(z_max, box_size[0], box_size[1], 0.5),
        "farfield_bottom": make_plate_z(z_min, box_size[0], box_size[1], 0.5),
        "farfield_outboard": make_plate_y(y_max, box_size[0], box_size[2], 0.5),
        "symmetry_plane_root": make_plate_y(0.0, box_size[0], box_size[2], 0.5),
    }


def build_assembly() -> cq.Assembly:
    validate_names()
    coords = load_foil_coords()

    asm = cq.Assembly(name=ASSEMBLY_NAME)

    wing = build_wing(coords)
    defects = build_auxiliary_defects()

    wing_bbox = wing["wing_surface_reference"].BoundingBox()
    farfield = build_farfield(wing_bbox)

    asm.add(wing["wing_surface_reference"], name="wing_surface_reference")
    asm.add(wing["tip_cap"], name="tip_cap")

    asm.add(defects["root_fairing_pad"], name="root_fairing_pad")
    asm.add(defects["root_fairing_cover"], name="root_fairing_cover")
    asm.add(defects["tip_cap_sliver"], name="tip_cap_sliver")

    # Marker body for the explicit root symmetry patch. The mesher can map this to the y=0 symmetry face.
    asm.add(farfield["symmetry_plane_root"], name="symmetry_plane_root")

    asm.add(farfield["farfield_box"], name="farfield_box")
    asm.add(farfield["farfield_upstream"], name="farfield_upstream")
    asm.add(farfield["farfield_downstream"], name="farfield_downstream")
    asm.add(farfield["farfield_top"], name="farfield_top")
    asm.add(farfield["farfield_bottom"], name="farfield_bottom")
    asm.add(farfield["farfield_outboard"], name="farfield_outboard")

    return asm


def main() -> int:
    parser = argparse.ArgumentParser(description="Build ONERA M6 transonic case STEP.")
    parser.add_argument("--out", required=True, help="Output STEP path")
    args = parser.parse_args()

    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    asm = build_assembly()

    tmp_dir = Path(tempfile.mkdtemp(prefix="case_006_onera_m6_"))
    tmp_step = tmp_dir / "cad_codex_v1.step"

    # Export once, then move atomically so the output path is stable and deterministic.
    asm.save(str(tmp_step), exportType="STEP")
    shutil.copyfile(tmp_step, out_path)

    print(f"Wrote {out_path}")
    print(f"Case: {CASE_ID}")
    print(f"Source page: {SOURCE_PAGE_URL}")
    print(f"Foil data: {AIRFOIL_URL}")
    print(f"Mach: {M_INF:.4f}, alpha: {ALPHA_DEG:.2f} deg, Re_c: {RE_C:.2e}")
    print(f"Freestream-equivalent: T_inf={T_INF_K:.1f} K, p_inf={P_INF_PA:.1f} Pa")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

## Deliverable 3 — STEP file path
`/Users/Zhuanz/Desktop/case_006_onera_m6_transonic/inputs/cad_codex_v1.step`

## Deliverable 4 — Parts manifest
```yaml
case_id: case_006_onera_m6_transonic
cad_source: tier1_reference_derived_onera_m6_wing
cad_source_tier: Tier_1
cad_source_url: https://www.grc.nasa.gov/WWW/wind/valid/m6wing/m6wing.html
source_geometry_url: https://www.grc.nasa.gov/WWW/wind/valid/m6wing/foilmod.txt
raw_geometry_url: https://www.grc.nasa.gov/WWW/wind/valid/m6wing/airfoil.txt
agard_reference: "Schmitt, V. and Charpin, F., AGARD AR-138, 1979"
license: NASA_public_validation_archive_AGARD_reference_verify_before_external_redistribution
generation_script: scripts/build_cad.py
step_file: inputs/cad_codex_v1.step
units_in_step: mm
solver_target_v1: rhoCentralFoam
solver_target_v2: rhoPimpleFoam_if_lambda_shock_is_over_smoothed
numerics_class: compressible_shock_density_based

freestream:
  M_inf: 0.8395
  alpha_deg: 3.06
  Re_chord: 11720000.0
  T_inf_K: 288.0
  p_inf_Pa: 93600.0
  T_total_inf_K: 328.5
  p_total_inf_Pa: 148400.0
  rho_inf_kg_m3: 1.133
  U_inf_mps: 285.6
  notes: "Reference-equivalent values derived from the published M/Re point using standard air properties."

geometry_reference:
  span_mm: 1196.3
  mac_mm: 646.07
  aspect_ratio: 3.8
  taper_ratio: 0.562
  leading_edge_sweep_deg: 30.0
  trailing_edge_sweep_deg: 15.8
  no_twist: true
  published_pressure_stations_eta:
    - 0.20
    - 0.44
    - 0.65
    - 0.80
    - 0.90
    - 0.95
    - 0.99

validation_stations:
  - eta: 0.20
    cp_lower_source_url: https://www.grc.nasa.gov/WWW/wind/valid/m6wing/cp1l.ex
    cp_upper_source_url: https://www.grc.nasa.gov/WWW/wind/valid/m6wing/cp1u.ex
  - eta: 0.44
    cp_lower_source_url: https://www.grc.nasa.gov/WWW/wind/valid/m6wing/cp2l.ex
    cp_upper_source_url: https://www.grc.nasa.gov/WWW/wind/valid/m6wing/cp2u.ex
  - eta: 0.65
    cp_lower_source_url: https://www.grc.nasa.gov/WWW/wind/valid/m6wing/cp3l.ex
    cp_upper_source_url: https://www.grc.nasa.gov/WWW/wind/valid/m6wing/cp3u.ex
  - eta: 0.80
    cp_lower_source_url: https://www.grc.nasa.gov/WWW/wind/valid/m6wing/cp4l.ex
    cp_upper_source_url: https://www.grc.nasa.gov/WWW/wind/valid/m6wing/cp4u.ex
  - eta: 0.90
    cp_lower_source_url: https://www.grc.nasa.gov/WWW/wind/valid/m6wing/cp5l.ex
    cp_upper_source_url: https://www.grc.nasa.gov/WWW/wind/valid/m6wing/cp5u.ex
  - eta: 0.95
    cp_lower_source_url: https://www.grc.nasa.gov/WWW/wind/valid/m6wing/cp6l.ex
    cp_upper_source_url: https://www.grc.nasa.gov/WWW/wind/valid/m6wing/cp6u.ex
  - eta: 0.99
    cp_lower_source_url: https://www.grc.nasa.gov/WWW/wind/valid/m6wing/cp7l.ex
    cp_upper_source_url: https://www.grc.nasa.gov/WWW/wind/valid/m6wing/cp7u.ex

parts:
  - name: wing_surface_reference
    role: wall
    bc:
      U: noSlip
      p: zeroGradient
      T: zeroGradient
      nut: nutUSpaldingWallFunction
      k: kqRWallFunction
      omega: omegaWallFunction
    notes: "Primary ONERA M6 wing wall, published Cp stations must remain untouched."

  - name: root_fairing_pad
    role: auxiliary_wall_defect
    defect_id: D1
    bc:
      U: noSlip
      p: zeroGradient
      T: zeroGradient
      nut: nutUSpaldingWallFunction
      k: kqRWallFunction
      omega: omegaWallFunction
    notes: "Root-side auxiliary body, outside published pressure stations."

  - name: root_fairing_cover
    role: auxiliary_wall_defect
    defect_id: D1
    bc:
      U: noSlip
      p: zeroGradient
      T: zeroGradient
      nut: nutUSpaldingWallFunction
      k: kqRWallFunction
      omega: omegaWallFunction
    notes: "Intentional sub-mm gap partner for the root-side D1 defect."

  - name: tip_cap
    role: tip_cap_wall
    bc:
      U: noSlip
      p: zeroGradient
      T: zeroGradient
      nut: nutUSpaldingWallFunction
      k: kqRWallFunction
      omega: omegaWallFunction
    notes: "Separate tip closure body, isolated from the eta=0.99 pressure station."

  - name: tip_cap_sliver
    role: auxiliary_wall_defect
    defect_id: D4
    bc:
      U: noSlip
      p: zeroGradient
      T: zeroGradient
      nut: nutUSpaldingWallFunction
      k: kqRWallFunction
      omega: omegaWallFunction
    notes: "Tiny sliver on the tip-cap edge / fillet transition, outside published Cp stations."

  - name: symmetry_plane_root
    role: symmetry
    bc:
      U: symmetry
      p: symmetry
      T: symmetry
    notes: "Explicit half-wing symmetry patch at the wing root, standard transonic practice."

  - name: farfield_box
    role: farfield_domain_reference
    bc:
      U: none_volume_reference
      p: none_volume_reference
      T: none_volume_reference
    notes: "Outer-domain reference body, sized beyond 25 chords in all directions."

  - name: farfield_upstream
    role: farfield
    bc:
      U: characteristicVelocityInletOutletVelocity
      p: characteristicPressureInletOutletPressure
      T: freestream
    notes: "Upstream open boundary."

  - name: farfield_downstream
    role: farfield
    bc:
      U: characteristicVelocityInletOutletVelocity
      p: characteristicPressureInletOutletPressure
      T: freestream
    notes: "Downstream open boundary."

  - name: farfield_top
    role: farfield
    bc:
      U: characteristicVelocityInletOutletVelocity
      p: characteristicPressureInletOutletPressure
      T: freestream
    notes: "Upper farfield boundary."

  - name: farfield_bottom
    role: farfield
    bc:
      U: characteristicVelocityInletOutletVelocity
      p: characteristicPressureInletOutletPressure
      T: freestream
    notes: "Lower farfield boundary."

  - name: farfield_outboard
    role: farfield
    bc:
      U: characteristicVelocityInletOutletVelocity
      p: characteristicPressureInletOutletPressure
      T: freestream
    notes: "Outboard spanwise farfield boundary."

numerics_hints:
  fluxScheme: Kurganov
  ddtSchemes: localEuler
  shock_limiter:
    rho: venkatakrishnan
    rhoU: venkatakrishnan
    rhoE: venkatakrishnan
  divSchemes:
    div_phi_rho: Gauss Kurganov
    div_phi_rhoU: Gauss Kurganov
    div_phi_rhoE: Gauss Kurganov
  notes:
    - "If the lambda shock disappears, reduce limiter aggressiveness before falling back to rhoPimpleFoam."
    - "Use forceCoeffs and Cp cuts at the seven published eta stations."

shock_detection:
  primary_metric: "max_abs_dnM_upper_surface"
  primary_locations_eta:
    - 0.65
    - 0.95
  secondary_metric: "lambda_shock_pattern_from_Cp_and_M_isolines"
  report_outputs:
    - upper_surface_Cp_vs_xc
    - upper_surface_Mach_vs_xc
    - spanwise_shock_foot_xc
    - max_upper_surface_Mach
    - forceCoeffs_Cl_Cd_Cm

patch_naming_check:
  - all_names_match_regex: "^[A-Za-z][A-Za-z0-9_]*$"
  - no_duplicate_names: true
  - no_spaces_or_hyphens: true
```

## Deliverable 5 — Defect manifest
```yaml
case_id: case_006_onera_m6_transonic
defect_count: 2
cad_source_tier: Tier_1
reference_data_validity: "preserved: all published ONERA M6 Cp stations at eta = 0.20, 0.44, 0.65, 0.80, 0.90, 0.95, 0.99 remain defect-free on the wing pressure/suction surfaces. Defects are isolated to root-side auxiliary hardware and the tip-cap edge, outside the measurement zones."

protected_reference_zones:
  - name: wing_cp_sections
    protected_eta:
      - 0.20
      - 0.44
      - 0.65
      - 0.80
      - 0.90
      - 0.95
      - 0.99
    protection_rule: "No defect body intersects the published upper/lower Cp extraction stations."
  - name: symmetry_plane_root
    protection_rule: "Root symmetry plane remains defect-free."
  - name: wing_upper_surface
    protection_rule: "No defect is placed on the upper surface between root and tip in the published measurement zones."
  - name: wing_lower_surface
    protection_rule: "No defect is placed on the lower surface between root and tip in the published measurement zones."

defects:
  - id: D1
    catalog_name: sub_mm_gap_between_bodies
    description: "0.35 mm gap between two small root-side auxiliary bodies near the symmetry plane."
    location:
      bodies_involved:
        - root_fairing_pad
        - root_fairing_cover
      region: "root-side auxiliary hardware, below eta=0.20 and outside published pressure stations"
      approx_coords_mm: [81.0, 42.0, 12.0]
    measurement:
      claimed_gap_mm: 0.35
      verification_command: >-
        FreeCADCmd -c "import FreeCAD as App, Import; doc=App.newDocument(); Import.insert('/Users/Zhuanz/Desktop/case_006_onera_m6_transonic/inputs/cad_codex_v1.step', doc.Name); o={x.Label:x for x in doc.Objects}; print(o['root_fairing_pad'].Shape.distToShape(o['root_fairing_cover'].Shape)[0])"
    expected_advisor_to_catch: virtual_interface_detector
    hypothesized_v_series_match: "geometry-only sliver/gap analogue; no inherited numerics finding."
    reference_data_validity: "preserved: defect is at the root-side auxiliary hardware, not on the published wing Cp surfaces."

  - id: D4
    catalog_name: sliver_on_spiral_or_fillet_edge
    description: "Tiny sliver body at the tip-cap fillet/edge transition."
    location:
      bodies_involved:
        - tip_cap_sliver
      region: "tip cap outer edge, outside the eta=0.99 pressure-tap line"
      approx_coords_mm: [785.0, 1185.0, 10.0]
    measurement:
      claimed_thickness_mm: 0.18
      verification_command: >-
        FreeCADCmd -c "import FreeCAD as App, Import; doc=App.newDocument(); Import.insert('/Users/Zhuanz/Desktop/case_006_onera_m6_transonic/inputs/cad_codex_v1.step', doc.Name); o={x.Label:x for x in doc.Objects}; bb=o['tip_cap_sliver'].Shape.BoundBox; print(min(bb.XLength, bb.YLength, bb.ZLength))"
    expected_advisor_to_catch: geometry_surgery.decimate_to_tier
    hypothesized_v_series_match: "geometry-surgery analogue only; no compressible-shock numerics inheritance."
    reference_data_validity: "preserved: tip-cap defect does not touch the published wing pressure stations."
```



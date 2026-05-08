## Deliverable 1 — Engineering brief

### Component picked + bank ID

**Case ID:** `case_005_rae_m2129_sduct`

**Component:** RAE M2129 circular S-duct intake diffuser, full 360 deg internal flow path with outlet plenum and explicit AIP post-processing plane.

**Bank/source IDs:**
- Public CAD/source catalog: `T1.I1` RAE M2129 S-duct.
- Component-bank class: internal compressible diffuser, promoted from Lane-A industrial roster.
- Source page: https://www.grc.nasa.gov/WWW/wind/valid/sduct/sduct02/sduct02.html
- No-vane tutorial/source context: https://www.grc.nasa.gov/WWW/wind/valid/M2129tutorial/tutorial.html
- NTRS reference: https://ntrs.nasa.gov/citations/20040021333
- Source status: NASA/WIND public validation archive plus AGARD/RAE reference geometry. The archive provides grids/reports, not a clean STEP, so this is **Tier-1 reference-derived CadQuery STEP**, not Tier-3 invented geometry.

This fills the uncovered **compressible-RANS internal diffuser** row with the canonical UAV/cruise-missile style S-duct intake, not the Lane-B Sajben validation diffuser.

### Engineering question

Can the harness ingest a reference-derived industrial S-duct STEP, configure `rhoSimpleFoam` with compressible total-pressure/total-temperature inlet physics, and report AIP recovery/distortion metrics without corrupting the published AIP and centerline measurement zones?

### Physics signature

- Solver target v1: `rhoSimpleFoam`
- v2 fallback: `rhoPimpleFoam` only if residuals or AIP pressure recovery show shock-induced unsteadiness
- Flow model: compressible RANS, `kOmegaSST`
- Thermo: perfect-gas air, `gamma = 1.4`, `R = 287.05 J/kg/K`, `Pr = 0.72`
- Reference total temperature: `T0 = 288 K`
- Reference inlet total pressure: `p0 = 101325 Pa`
- Outlet reference static pressure: `p_back = 85000 Pa`
- Pressure ratio: `p_back / p0 ≈ 0.839`
- Target throat Mach: `M ≈ 0.70-0.78`
- Target AIP Mach: `M ≈ 0.40-0.60`
- Strong-shock exclusion: no design point above `M = 1.3`; v1 should be shock-free or weak-shock only
- Reynolds number: `Re_D ≈ 1.5e6-2.0e6` based on throat/AIP diameter
- Regime: turbulent internal diffuser flow, adverse pressure gradient, secondary-flow distortion, possible separation after the first bend

### Parts inventory

- `stationary_domain`: fluid-volume reference for the duct plus outlet plenum
- `duct_wall_reference`: primary adiabatic no-slip duct wall
- `inlet`: compressible total-pressure inlet, `p: totalPressure`, `T: totalTemperature`
- `outlet`: compressible outlet, `p: waveTransmissive` with fixed-pressure fallback
- `aip_plane_marker`: non-fluid marker for AIP; actual post-processing uses cutting plane `AIP`
- `inlet_flange_ring`: external auxiliary flange wall, participates in D1
- `inlet_flange_cover`: external auxiliary flange cover, participates in D1
- `throat_liner_overdense`: D2 over-dense triangular wall-overlay body near throat, outside centerline and AIP measurement zones

### Boundary conditions plan

- `inlet`: `U: pressureInletOutletVelocity`, `p: totalPressure p0=101325 Pa`, `T: totalTemperature T0=288 K`
- `outlet`: `U: zeroGradient`, `p: waveTransmissive fieldInf=85000 Pa`; fallback `fixedValue p=85000 Pa`, `T: inletOutlet`
- walls: `U: noSlip`, `p: zeroGradient`, `T: zeroGradient` adiabatic, compressible wall functions for `mut`, `alphat`, `k`, `omega`
- `aip_plane_marker`: excluded from mesh as a marker; use cutting plane at `x=489.458 mm`, center `[489.458, 0, 137.16]`, normal `[1, 0, 0]`
- initialization: seed `U`, `p`, and `T` from 1D isentropic estimates; avoid zero-field cold start for the first compressible case

### Expected metrics

- AIP Mach map
- AIP total-pressure recovery: `PR = areaAverage(p0_AIP) / p0_inlet`
- DC60 distortion coefficient from the worst 60 degree sector at AIP
- Centerline static pressure coefficient versus axial station
- Area-averaged AIP Mach and mass-flow consistency
- Wall y+ histogram and separation footprint after the first bend
- Residuals, density bounds, energy-equation stability, and outlet wave reflection behavior
- Advisor detection result for D1 and D2

### Hypothesized failure modes

This is a new **compressible-RANS** numerics root. It inherits none of the compressible-buoyant findings `V3-V13/V15`, and none of the incompressible or MRF findings from case_003/case_004.

Predicted new findings:
- Compressible BC writer may lack `totalPressure`, `totalTemperature`, `waveTransmissive`, and `pressureInletOutletVelocity`.
- `thermophysicalProperties` generation may be missing or assume incompressible transport.
- Absolute pressure versus gauge pressure confusion may make `rhoSimpleFoam` compute nonphysical density.
- Zero initial fields may cause first-iteration Mach or temperature spikes; this should become a compressible-RANS initialization playbook item.
- Outlet `waveTransmissive` may reflect in steady SIMPLE; fallback is fixed absolute pressure, not solver-class escalation.
- D2 may force geometry-surgery decimation before snappyHexMesh.
- D1 may create local sliver cells if auxiliary exterior hardware is retained in mesh.

### Defect injection summary

Exactly two defects:

- `D1`: 0.35 mm axial gap between `inlet_flange_ring` and `inlet_flange_cover`, external to the flow path and upstream of reference measurement zones.
- `D2`: `throat_liner_overdense`, a 102400-triangle wall-overlay body near the throat, offset into the solid side so centerline and AIP reference zones remain geometrically clean.

Reference-data validity: AIP plane and centerline remain defect-free. Use AIP Mach/recovery/distortion and centerline pressure comparisons as reference-informed metrics; report that auxiliary CAD defects are outside those measurement zones.

### Sub-session estimated effort

Estimated effort: **5-8 hours**, likely 3 versions:
- v1: CAD regeneration, STEP/name validation, defect measurement
- v2: compressible BC/thermo writer setup and coarse `rhoSimpleFoam`
- v3: AIP DC60 post-processing, y+ correction, pressure-ratio adjustment; `rhoPimpleFoam` only if weak-shock unsteadiness persists

## Deliverable 2 — CAD generation script

```python
#!/usr/bin/env python3
"""case_005_rae_m2129_sduct CAD generator.

Tier-1 reference-derived source:
- RAE M2129 S-duct via NASA/WIND validation archive.
- The public archive provides grids/reports, not a clean STEP, so this
  script regenerates a deterministic STEP from published dimensions and
  caches the NASA archive for provenance.

Designed by Codex per cfd-harness-unified case-design protocol.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import os
import re
import shutil
import sys
import tempfile
import urllib.request
from pathlib import Path

import cadquery as cq


CASE_ID = "case_005_rae_m2129_sduct"
ASSEMBLY_NAME = CASE_ID

SOURCE_PAGE_URL = "https://www.grc.nasa.gov/WWW/wind/valid/sduct/sduct02/sduct02.html"
SOURCE_ARCHIVE_URL = "https://www.grc.nasa.gov/WWW/wind/valid/sduct/sduct02/sduct02.tar.gz"
TUTORIAL_PAGE_URL = "https://www.grc.nasa.gov/WWW/wind/valid/M2129tutorial/tutorial.html"
NTRS_REFERENCE_URL = "https://ntrs.nasa.gov/citations/20040021333"
SOURCE_CACHE_NAME = "tier1_rae_m2129_sduct02_nasa_wind.tar.gz"
SOURCE_SHA256 = ""

DEFAULT_REPO_ROOT = Path(os.environ.get("CFD_HARNESS_REPO", "/Users/Zhuanz/Desktop/cfd-harness-unified"))
PATCH_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

# === Reference-derived geometry dimensions ===
INCH_TO_MM = 25.4
INLET_X_MM = -80.0
THROAT_X_MM = 0.0
AIP_X_MM = 19.27 * INCH_TO_MM
OUTLET_X_MM = 610.0

THROAT_DIAMETER_MM = 5.06 * INCH_TO_MM
AIP_DIAMETER_MM = 6.00 * INCH_TO_MM
DUCT_OFFSET_MM = 5.40 * INCH_TO_MM

THROAT_RADIUS_MM = 0.5 * THROAT_DIAMETER_MM
AIP_RADIUS_MM = 0.5 * AIP_DIAMETER_MM
PLENUM_RADIUS_MM = 95.0

DUCT_WALL_THICKNESS_MM = 3.0
BOUNDARY_PATCH_THICKNESS_MM = 1.0
BOOLEAN_MARGIN_MM = 2.0

# === Flow reference values for manifest consistency ===
P_TOTAL_INLET_PA = 101325.0
T_TOTAL_INLET_K = 288.0
P_BACK_PA = 85000.0
TARGET_AIP_MACH = 0.50

# === D1: external inlet flange gap ===
DEFECT_GAP_MM = 0.35
FLANGE_INNER_RADIUS_MM = THROAT_RADIUS_MM + DUCT_WALL_THICKNESS_MM + 4.0
FLANGE_OUTER_RADIUS_MM = FLANGE_INNER_RADIUS_MM + 30.0
FLANGE_RING_LENGTH_MM = 10.0
FLANGE_COVER_LENGTH_MM = 6.0

# === D2: over-dense triangular throat liner overlay ===
D2_X0_MM = 8.0
D2_X1_MM = 42.0
D2_AXIAL_DIVS = 160
D2_THETA_DIVS = 320
D2_RADIUS_OFFSET_OUTWARD_MM = 0.15

PART_NAMES = [
    "stationary_domain",
    "duct_wall_reference",
    "inlet",
    "outlet",
    "aip_plane_marker",
    "inlet_flange_ring",
    "inlet_flange_cover",
    "throat_liner_overdense",
]


def validate_patch_names() -> None:
    seen: set[str] = set()
    for name in PART_NAMES:
        if not PATCH_NAME_RE.match(name):
            raise ValueError(f"Invalid OpenFOAM patch/body name: {name}")
        if name in seen:
            raise ValueError(f"Duplicate patch/body name: {name}")
        seen.add(name)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_candidates(script_dir: Path, explicit_source: str | None) -> list[Path]:
    candidates: list[Path] = []
    if explicit_source:
        candidates.append(Path(explicit_source).expanduser())
    env_source = os.environ.get("CASE005_SOURCE_ARCHIVE")
    if env_source:
        candidates.append(Path(env_source).expanduser())
    candidates.append(script_dir.parent / "inputs" / "cache" / SOURCE_CACHE_NAME)
    candidates.append(DEFAULT_REPO_ROOT / ".planning" / "cad_cache" / SOURCE_CACHE_NAME)
    return candidates


def download_reference_archive(target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")

    req = urllib.request.Request(
        SOURCE_ARCHIVE_URL,
        headers={"User-Agent": f"cfd-harness-unified-{CASE_ID}/1.0"},
    )
    with urllib.request.urlopen(req, timeout=120) as response, tmp.open("wb") as f:
        shutil.copyfileobj(response, f)

    if SOURCE_SHA256 and sha256_file(tmp) != SOURCE_SHA256:
        tmp.unlink(missing_ok=True)
        raise RuntimeError("Downloaded M2129 archive SHA256 did not match SOURCE_SHA256")

    tmp.replace(target)
    return target


def resolve_reference_archive(
    script_dir: Path,
    explicit_source: str | None,
    require: bool,
) -> Path | None:
    for candidate in source_candidates(script_dir, explicit_source):
        if candidate.exists():
            if SOURCE_SHA256 and sha256_file(candidate) != SOURCE_SHA256:
                raise RuntimeError(f"Cached source hash mismatch: {candidate}")
            return candidate

    try:
        return download_reference_archive(script_dir.parent / "inputs" / "cache" / SOURCE_CACHE_NAME)
    except Exception as exc:
        if require:
            raise
        print(f"Warning: Tier-1 archive cache fetch failed: {exc}", file=sys.stderr)
        return None


def smoothstep(s: float) -> float:
    s = max(0.0, min(1.0, s))
    return s * s * (3.0 - 2.0 * s)


def centerline_z_mm(x_mm: float) -> float:
    if x_mm <= THROAT_X_MM:
        return 0.0
    if x_mm >= AIP_X_MM:
        return DUCT_OFFSET_MM
    return DUCT_OFFSET_MM * smoothstep((x_mm - THROAT_X_MM) / (AIP_X_MM - THROAT_X_MM))


def radius_mm(x_mm: float) -> float:
    if x_mm <= THROAT_X_MM:
        return THROAT_RADIUS_MM
    if x_mm <= AIP_X_MM:
        s = smoothstep((x_mm - THROAT_X_MM) / (AIP_X_MM - THROAT_X_MM))
        return THROAT_RADIUS_MM + (AIP_RADIUS_MM - THROAT_RADIUS_MM) * s

    s = smoothstep((x_mm - AIP_X_MM) / (OUTLET_X_MM - AIP_X_MM))
    return AIP_RADIUS_MM + (PLENUM_RADIUS_MM - AIP_RADIUS_MM) * s


def loft_station_xs() -> list[float]:
    stations = [
        INLET_X_MM,
        THROAT_X_MM,
        55.0,
        110.0,
        170.0,
        245.0,
        320.0,
        395.0,
        455.0,
        AIP_X_MM,
        535.0,
        OUTLET_X_MM,
    ]
    return sorted(set(stations))


def section_wire(x_mm: float, radius_offset_mm: float = 0.0) -> cq.Wire:
    center = cq.Vector(x_mm, 0.0, centerline_z_mm(x_mm))
    normal = cq.Vector(1.0, 0.0, 0.0)
    return cq.Wire.makeCircle(radius_mm(x_mm) + radius_offset_mm, center, normal)


def make_lofted_volume(radius_offset_mm: float = 0.0) -> cq.Shape:
    wires = [section_wire(x, radius_offset_mm) for x in loft_station_xs()]

    # Lofting circular stations captures the M2129 diffusing S-duct centerline.
    return cq.Solid.makeLoft(wires, ruled=False)


def cylinder_along_x(radius_mm_: float, length_mm: float, center_x_mm: float, center_z_mm: float) -> cq.Shape:
    start_x = center_x_mm - 0.5 * length_mm
    return (
        cq.Workplane("YZ", origin=(start_x, 0.0, center_z_mm))
        .circle(radius_mm_)
        .extrude(length_mm)
        .val()
    )


def annular_cylinder_along_x(
    inner_radius_mm: float,
    outer_radius_mm: float,
    length_mm: float,
    center_x_mm: float,
    center_z_mm: float,
) -> cq.Shape:
    outer = cylinder_along_x(outer_radius_mm, length_mm, center_x_mm, center_z_mm)
    inner = cylinder_along_x(
        inner_radius_mm,
        length_mm + 2.0 * BOOLEAN_MARGIN_MM,
        center_x_mm,
        center_z_mm,
    )

    # Boolean cut makes a real annular flange/ring body, not a visual-only marker.
    return outer.cut(inner)


def make_boundary_disk(x_mm: float, radius: float, name: str) -> cq.Shape:
    del name
    return cylinder_along_x(
        radius,
        BOUNDARY_PATCH_THICKNESS_MM,
        x_mm,
        centerline_z_mm(x_mm),
    )


def build_duct_wall() -> cq.Shape:
    outer = make_lofted_volume(DUCT_WALL_THICKNESS_MM)
    inner = make_lofted_volume(0.0)

    # Subtract the fluid volume from the outer loft to create a finite wall solid.
    return outer.cut(inner)


def build_aip_marker() -> cq.Shape:
    center_z = centerline_z_mm(AIP_X_MM)
    inner_radius = AIP_RADIUS_MM + DUCT_WALL_THICKNESS_MM + 0.75
    outer_radius = inner_radius + 5.0

    # The AIP marker is an exterior ring so it does not block the flow volume.
    return annular_cylinder_along_x(
        inner_radius,
        outer_radius,
        1.5,
        AIP_X_MM,
        center_z,
    )


def build_flange_defect() -> tuple[cq.Shape, cq.Shape]:
    center_z = centerline_z_mm(INLET_X_MM)
    ring_center_x = INLET_X_MM - 0.5 * FLANGE_RING_LENGTH_MM
    cover_center_x = (
        ring_center_x
        - 0.5 * FLANGE_RING_LENGTH_MM
        - DEFECT_GAP_MM
        - 0.5 * FLANGE_COVER_LENGTH_MM
    )

    inlet_flange_ring = annular_cylinder_along_x(
        FLANGE_INNER_RADIUS_MM,
        FLANGE_OUTER_RADIUS_MM,
        FLANGE_RING_LENGTH_MM,
        ring_center_x,
        center_z,
    )

    # D1: the cover is intentionally separated from the flange by 0.35 mm.
    inlet_flange_cover = annular_cylinder_along_x(
        FLANGE_INNER_RADIUS_MM,
        FLANGE_OUTER_RADIUS_MM,
        FLANGE_COVER_LENGTH_MM,
        cover_center_x,
        center_z,
    )
    return inlet_flange_ring, inlet_flange_cover


def cylindrical_point(x_mm: float, theta_rad: float, radial_offset_mm: float) -> cq.Vector:
    r = radius_mm(x_mm) + radial_offset_mm
    return cq.Vector(
        x_mm,
        r * math.cos(theta_rad),
        centerline_z_mm(x_mm) + r * math.sin(theta_rad),
    )


def triangle_face(p0: cq.Vector, p1: cq.Vector, p2: cq.Vector) -> cq.Face:
    wire = cq.Wire.makePolygon([p0, p1, p2, p0])
    return cq.Face.makeFromWires(wire)


def build_overdense_liner() -> cq.Shape:
    faces: list[cq.Face] = []
    for i in range(D2_AXIAL_DIVS):
        x0 = D2_X0_MM + (D2_X1_MM - D2_X0_MM) * i / D2_AXIAL_DIVS
        x1 = D2_X0_MM + (D2_X1_MM - D2_X0_MM) * (i + 1) / D2_AXIAL_DIVS
        for j in range(D2_THETA_DIVS):
            t0 = math.tau * j / D2_THETA_DIVS
            t1 = math.tau * (j + 1) / D2_THETA_DIVS

            p00 = cylindrical_point(x0, t0, D2_RADIUS_OFFSET_OUTWARD_MM)
            p10 = cylindrical_point(x1, t0, D2_RADIUS_OFFSET_OUTWARD_MM)
            p11 = cylindrical_point(x1, t1, D2_RADIUS_OFFSET_OUTWARD_MM)
            p01 = cylindrical_point(x0, t1, D2_RADIUS_OFFSET_OUTWARD_MM)

            # D2: deliberately split every quad into triangles to mimic over-dense export.
            faces.append(triangle_face(p00, p10, p11))
            faces.append(triangle_face(p00, p11, p01))

    return cq.Compound.makeCompound(faces)


def build() -> cq.Assembly:
    validate_patch_names()

    stationary_domain = make_lofted_volume(0.0)
    duct_wall_reference = build_duct_wall()
    inlet = make_boundary_disk(INLET_X_MM, radius_mm(INLET_X_MM), "inlet")
    outlet = make_boundary_disk(OUTLET_X_MM, radius_mm(OUTLET_X_MM), "outlet")
    aip_plane_marker = build_aip_marker()
    inlet_flange_ring, inlet_flange_cover = build_flange_defect()
    throat_liner_overdense = build_overdense_liner()

    asm = cq.Assembly(name=ASSEMBLY_NAME)
    asm.add(stationary_domain, name="stationary_domain")
    asm.add(duct_wall_reference, name="duct_wall_reference")
    asm.add(inlet, name="inlet")
    asm.add(outlet, name="outlet")
    asm.add(aip_plane_marker, name="aip_plane_marker")
    asm.add(inlet_flange_ring, name="inlet_flange_ring")
    asm.add(inlet_flange_cover, name="inlet_flange_cover")
    asm.add(throat_liner_overdense, name="throat_liner_overdense")
    return asm


def canonicalize_step(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="ignore")
    replacement = (
        "FILE_NAME('case_005_rae_m2129_sduct.step',"
        "'1970-01-01T00:00:00',"
        "('cfd-harness-unified'),"
        "('Codex'),"
        "'OpenCASCADE',"
        "'CadQuery',"
        "'none');"
    )
    text = re.sub(r"FILE_NAME\s*\(.*?\);", replacement, text, count=1, flags=re.S)
    text = text.replace(str(path), "case_005_rae_m2129_sduct.step")
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="Output STEP path")
    parser.add_argument("--source-archive", default=None, help="Optional cached NASA/WIND M2129 archive")
    parser.add_argument(
        "--require-reference-cache",
        action="store_true",
        help="Fail if the Tier-1 source archive cannot be cached.",
    )
    args = parser.parse_args()

    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    script_dir = Path(__file__).resolve().parent
    reference_archive = resolve_reference_archive(
        script_dir,
        args.source_archive,
        args.require_reference_cache,
    )

    asm = build()

    # Export through a temporary file so failed writes never leave a partial STEP.
    with tempfile.TemporaryDirectory(dir=str(out_path.parent)) as tmpdir:
        tmp_step = Path(tmpdir) / "case_005_rae_m2129_sduct.step"
        asm.save(str(tmp_step), exportType="STEP")
        canonicalize_step(tmp_step)
        shutil.copyfile(tmp_step, out_path)

    print(f"Wrote {out_path}")
    print(f"Case: {CASE_ID}")
    print(f"Tier-1 source page: {SOURCE_PAGE_URL}")
    print(f"Tutorial page: {TUTORIAL_PAGE_URL}")
    print(f"NTRS reference: {NTRS_REFERENCE_URL}")
    print(f"Tier-1 archive cache: {reference_archive if reference_archive else 'not cached'}")
    print(f"D2 intended triangle faces: {2 * D2_AXIAL_DIVS * D2_THETA_DIVS}")
    print(f"AIP center mm: [{AIP_X_MM:.3f}, 0.0, {centerline_z_mm(AIP_X_MM):.3f}]")
    print(f"p0 inlet Pa: {P_TOTAL_INLET_PA:.1f}; T0 inlet K: {T_TOTAL_INLET_K:.1f}; p_back Pa: {P_BACK_PA:.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

## Deliverable 3 — STEP file path

`/Users/Zhuanz/Desktop/case_005_rae_m2129_sduct/inputs/cad_codex_v1.step`

## Deliverable 4 — Parts manifest

```yaml
case_id: case_005_rae_m2129_sduct
cad_source: tier1_reference_derived_rae_m2129_sduct
cad_source_tier: Tier_1
cad_source_url: https://www.grc.nasa.gov/WWW/wind/valid/sduct/sduct02/sduct02.html
source_archive_url: https://www.grc.nasa.gov/WWW/wind/valid/sduct/sduct02/sduct02.tar.gz
tutorial_url: https://www.grc.nasa.gov/WWW/wind/valid/M2129tutorial/tutorial.html
ntrs_reference_url: https://ntrs.nasa.gov/citations/20040021333
license: NASA_public_validation_archive_AGARD_reference_verify_before_external_redistribution
generation_script: scripts/build_cad.py
step_file: inputs/cad_codex_v1.step
units_in_step: mm
solver_target_v1: rhoSimpleFoam
solver_target_v2: rhoPimpleFoam_only_if_shock_induced_unsteadiness_or_oscillatory_residuals
numerics_class: compressible_RANS_internal_diffuser

thermophysics:
  equation_of_state: perfectGas
  gamma: 1.4
  R_J_kgK: 287.05
  Cp_J_kgK: 1004.5
  Pr: 0.72
  mu_ref_Pa_s: 1.7894e-05
  T_ref_k: 288.0
  turbulence_model: kOmegaSST

reference_conditions:
  p_total_inlet_pa: 101325.0
  T_total_inlet_k: 288.0
  p_back_pa: 85000.0
  pressure_ratio_p_back_over_p0: 0.839
  target_throat_mach: "0.70 to 0.78"
  target_aip_mach: "0.40 to 0.60"
  strong_shock_limit_mach: 1.3

geometry_reference:
  throat_diameter_mm: 128.524
  aip_diameter_mm: 152.4
  aip_x_mm: 489.458
  duct_offset_mm: 137.16
  outlet_x_mm: 610.0
  full_duct_360deg: true
  symmetry_patches: []

cutting_planes:
  - name: AIP
    role: aip_plane
    purpose: DC60_recovery_and_Mach_map_postprocessing
    origin_xyz_mm: [489.458, 0.0, 137.16]
    normal_xyz: [1.0, 0.0, 0.0]
    radius_mm: 76.2
    exclude_from_mesh: true

parts:
  - name: stationary_domain
    role: stationary_fluid_domain
    contains: duct_plus_outlet_plenum
    bc:
      U: none_volume_reference
      p: none_volume_reference
      T: none_volume_reference
    notes: "Fluid-volume reference for internal meshing; not a boundary patch."

  - name: duct_wall_reference
    role: wall_adiabatic
    bc:
      U: noSlip
      p: zeroGradient
      T: zeroGradient
      mut: mutkWallFunction
      alphat: compressible::alphatWallFunction
      k: kqRWallFunction
      omega: omegaWallFunction
    notes: "Primary S-duct wall. Reference centerline and AIP geometry preserved."

  - name: inlet
    role: compressible_total_pressure_inlet
    p_total_inlet_pa: 101325.0
    T_total_inlet_k: 288.0
    bc:
      U: pressureInletOutletVelocity
      p: totalPressure
      T: totalTemperature
      mut: calculated
      alphat: calculated
      k: fixedValue
      omega: fixedValue
    notes: "New compressible inlet BC family for this project."

  - name: outlet
    role: compressible_wave_transmissive_outlet
    p_back_pa: 85000.0
    bc:
      U: zeroGradient
      p: waveTransmissive
      T: inletOutlet
      mut: calculated
      alphat: calculated
      k: inletOutlet
      omega: inletOutlet
    fallback_bc:
      p: fixedValue
      p_value_pa: 85000.0
      reason: "Use fixed absolute pressure if waveTransmissive is unstable or unavailable in the local rhoSimpleFoam setup."
    notes: "Primary plan exercises waveTransmissive; fixedValue p is allowed fallback."

  - name: aip_plane_marker
    role: aip_plane_marker
    bc:
      U: none_postprocessing_marker_exclude_from_mesh
      p: none_postprocessing_marker_exclude_from_mesh
      T: none_postprocessing_marker_exclude_from_mesh
    cutting_plane_name: AIP
    notes: "Exterior annular marker only; actual AIP analysis uses cutting_planes.AIP."

  - name: inlet_flange_ring
    role: auxiliary_wall_defect
    defect_id: D1
    bc:
      U: noSlip
      p: zeroGradient
      T: zeroGradient
      mut: mutkWallFunction
      alphat: compressible::alphatWallFunction
      k: kqRWallFunction
      omega: omegaWallFunction
    notes: "External inlet flange body. Keep out of AIP and centerline reference zones."

  - name: inlet_flange_cover
    role: auxiliary_wall_defect
    defect_id: D1
    bc:
      U: noSlip
      p: zeroGradient
      T: zeroGradient
      mut: mutkWallFunction
      alphat: compressible::alphatWallFunction
      k: kqRWallFunction
      omega: omegaWallFunction
    notes: "External cover offset from inlet_flange_ring by 0.35 mm."

  - name: throat_liner_overdense
    role: auxiliary_wall_defect_overdense_overlay
    defect_id: D2
    expected_face_count: 102400
    mesh_preprocess: "Run geometry_surgery decimation or drop as duplicate wall overlay after advisor logs D2."
    bc_if_retained:
      U: noSlip
      p: zeroGradient
      T: zeroGradient
      mut: mutkWallFunction
      alphat: compressible::alphatWallFunction
      k: kqRWallFunction
      omega: omegaWallFunction
    notes: "Over-dense triangular throat-wall overlay offset 0.15 mm into solid side; not on centerline or AIP."

postprocessing:
  required_metrics:
    - AIP_Mach_map
    - AIP_total_pressure_recovery_PR
    - DC60_distortion_coefficient
    - centerline_static_pressure
    - mass_flow_balance
    - residual_density_temperature_bounds
  dc60_definition: "(areaAvg_p0_AIP - worst_60deg_sector_avg_p0) / areaAvg_dynamic_pressure_AIP"

patch_naming_check:
  - all_names_match_regex: "^[A-Za-z][A-Za-z0-9_]*$"
  - no_duplicate_names: true
  - no_spaces_or_hyphens: true
```

## Deliverable 5 — Defect manifest

```yaml
case_id: case_005_rae_m2129_sduct
defect_count: 2
cad_source_tier: Tier_1
reference_data_validity: "preserved: AIP cutting plane and centerline pressure line are defect-free. Defects are exterior flange hardware and wall-offset throat tessellation overlay, not measurement-zone geometry."
protected_reference_zones:
  - name: centerline_pressure_line
    protection_rule: "No defect body intersects the duct centerline y=0, z=centerline_z(x)."
  - name: AIP
    x_mm: 489.458
    protection_rule: "No defect body lies within the AIP measurement disk or within +/-5 mm of the AIP station."

defects:
  - id: D1
    catalog_name: sub_mm_gap_between_bodies
    description: "0.35 mm axial gap between inlet_flange_ring and inlet_flange_cover on the external inlet flange."
    location:
      bodies_involved:
        - inlet_flange_ring
        - inlet_flange_cover
      region: "external inlet flange, upstream of throat and outside internal centerline/AIP reference zones"
      approx_coords_mm: [-90.35, 94.3, 0.0]
    measurement:
      claimed_gap_mm: 0.35
      verification_command: >-
        FreeCADCmd -c "import FreeCAD as App, Import; doc=App.newDocument(); Import.insert('/Users/Zhuanz/Desktop/case_005_rae_m2129_sduct/inputs/cad_codex_v1.step', doc.Name); o={x.Label:x for x in doc.Objects}; print(o['inlet_flange_ring'].Shape.distToShape(o['inlet_flange_cover'].Shape)[0])"
    expected_advisor_to_catch: virtual_interface_detector_pending_A2
    hypothesized_v_series_match: "Geometry-advisor analogue of V2/V8 only; no compressible-RANS numerics inheritance."
    reference_data_validity: "preserved: external flange defect does not touch AIP or centerline."

  - id: D2
    catalog_name: over_dense_triangulation
    description: "throat_liner_overdense is a 102400-triangle wall-overlay body where an analytic sleeve would suffice."
    location:
      bodies_involved:
        - throat_liner_overdense
      region: "near-throat wall overlay from x=8 mm to x=42 mm, offset 0.15 mm into the solid side"
      approx_x_range_mm: [8.0, 42.0]
      approx_radius_mm: 64.4
    measurement:
      claimed_face_count: 102400
      claimed_triangular_faces: true
      verification_command: >-
        FreeCADCmd -c "import FreeCAD as App, Import; doc=App.newDocument(); Import.insert('/Users/Zhuanz/Desktop/case_005_rae_m2129_sduct/inputs/cad_codex_v1.step', doc.Name); o={x.Label:x for x in doc.Objects}; print(len(o['throat_liner_overdense'].Shape.Faces))"
    expected_advisor_to_catch: geometry_surgery.decimate_to_tier
    hypothesized_v_series_match: "V8-style geometry_surgery trigger for over-dense industrial CAD; no inherited compressible-buoyant or incompressible solver finding."
    reference_data_validity: "preserved: overlay is at the wall and outside AIP; centerline remains geometrically untouched."
```

## Deliverable 1 — Engineering Brief

### Component picked + bank ID

**Case ID:** `case_004_nrel_phase_vi_mrf`

**Component:** NREL Phase VI two-bladed wind-turbine rotor with nacelle/tower context and explicit MRF rotating volume.

**Bank/source IDs:**
- Component-bank class: `D4` marine/open rotor analogue, upgraded to Tier-1 wind-turbine public reference `T1.W1`.
- Public CAD/reference source: NREL Phase VI / UAE rotor.
- Source report: https://www.nrel.gov/docs/fy02osti/29955.pdf
- DOI/source page: https://doi.org/10.2172/15000240
- Secondary benchmark reference: https://exawind.github.io/exawind-benchmarks/exawind/NREL_Phase_VI_Turbine/README.html
- Airfoil coordinate source: https://airfoiltools.com/airfoil/details?airfoil=s809-nr
- License/source status: NREL/DOE public technical report and open benchmark references; verify redistribution rules before publishing derived STEP externally.

This fills the uncovered **rotating machinery / MRF** row with a real, instrumented industrial rotor rather than a generic fan.

### Engineering question

Can the harness ingest a rotating-machinery STEP, preserve a named `rotating_cellzone`, configure `simpleFoam + MRFProperties` correctly, and produce physically sane thrust/torque trends for a public reference rotor while detecting two controlled CAD defects before meshing?

### Physics signature

- Solver target v1: `simpleFoam` + MRF
- v2 fallback: `pimpleFoam` + AMI sliding mesh only if thrust/torque monitors remain oscillatory
- Flow model: incompressible RANS, `kOmegaSST`
- Fluid: air, `nu = 1.5e-5 m2/s`
- Rotor radius: `R = 5.029 m`
- Rotor speed: `72 rpm = 7.539822 rad/s`
- Baseline inflow: `U_inf = 7 m/s`; sweep points: `10 m/s`, `15 m/s`
- Tip speed: about `37.9 m/s`
- Mach estimate: `< 0.13`, acceptable for incompressible baseline
- Reynolds estimate at 80% span: about `0.9e6-1.1e6`
- Regime: rotating turbulent external flow, adverse pressure gradients, radial pressure field, tip vortex, MRF frozen-rotor approximation

Per V-series Pattern 6, this **inherits none** of the compressible-buoyant-RANS findings `V3-V13`/`V15`, and none of case_003 external-RANS findings when they accumulate.

### Parts inventory

- `rotating_cellzone`: explicit MRF volume, **role: rotating_cellzone**
- `stationary_domain`: background wind-tunnel/domain volume, stationary domain reference
- `rotor_blade_A`: rotating wall, blade at 0 deg azimuth
- `rotor_blade_B`: rotating wall, blade at 180 deg azimuth
- `hub_spinner`: rotating wall, hub/spinner body
- `nacelle_body`: stationary wall downstream of rotor
- `tower_body`: stationary wall
- `nacelle_service_cover`: stationary auxiliary wall, participates in D1 gap defect
- `yaw_sensor_shim`: stationary auxiliary wall, D8 thin-shell defect
- `inlet`: velocity inlet
- `outlet`: pressure outlet
- `tunnel_walls`: slip/farfield tunnel side walls

### Boundary conditions plan

- `inlet`: `fixedValue U = (U_inf, 0, 0)`, `zeroGradient p`, fixed turbulence from `I = 0.1-0.5%`
- `outlet`: `zeroGradient U`, `fixedValue p = 0`
- `tunnel_walls`: `slip` or `symmetryPlane` for v1; no tunnel-wall validation claim
- `rotor_blade_A`, `rotor_blade_B`, `hub_spinner`: rotating wall treatment using MRF-consistent `movingWallVelocity` or local OpenFOAM tutorial equivalent
- stationary walls: `noSlip`
- `rotating_cellzone`: not a wall patch; consumed as MRF `cellZone`
- MRF setup: origin `[0, 0, 0]`, axis `[1, 0, 0]`, `omega = 7.539822 rad/s`
- Periodic/cyclicAMI: none in v1 because the full 360 deg two-blade rotor is modeled
- v2 AMI fallback: add `rotor_ami_inner` / `stator_ami_outer` cylindrical interfaces around the same rotating volume

### Expected metrics

- Rotor thrust `Fx`
- Rotor torque `Mx` about the rotation axis
- Power `P = torque * omega`
- `Ct`, `Cq`, `Cp` versus inflow speed
- Rotor-disk pressure-drop/head analogue: `Delta_p_disk` and `H = Delta_p / (rho*g)` versus flow
- MRF audit: cell count in `rotating_cellzone`, rotating-wall patches fully enclosed by zone, omega sign check
- y+ histogram on blades and hub
- residuals, continuity error, thrust/torque monitor stability
- advisor detection result for D1 and D8

### Hypothesized failure modes

- `rotating_cellzone` name mismatch in `MRFProperties` gives a false stationary run with near-zero useful torque.
- MRF zone too short axially can leave blade leading/trailing edges outside the rotating source region.
- Omega sign or axis error reverses torque sign while residuals still look healthy.
- Steady MRF may not represent tower/nacelle interaction; force monitors may require v2 sliding mesh.
- D1 may create sliver cells near the nacelle cover, a V8/V10-style geometry risk, but not an inherited numerics finding.
- D8 should exercise the thin-wall advisor path, again as geometry-advisor coverage rather than inherited solver-class behavior.

### Defect injection summary

Exactly two defects, both outside blade pressure-tap / published measurement zones:

- `D1`: 0.30 mm gap between `nacelle_body` and `nacelle_service_cover`
- `D8`: 0.75 mm thick `yaw_sensor_shim`

Reference-data validity: blade surface geometry and pressure-tap radial stations are untouched. Local blade pressure comparisons remain valid for the reconstructed blade; integrated thrust/torque should be treated as a defected-nacelle configuration, not a strict wind-tunnel parity benchmark.

### Sub-session estimated effort

Estimated effort: **6-10 hours**, likely 3 versions:
- v1: CAD regeneration, STEP/name validation, defect measurement
- v2: coarse MRF mesh and MRFProperties/cellZone audit
- v3: y+ correction, inflow sweep, torque/thrust report; AMI only if MRF force monitors do not settle

## Deliverable 2 — CAD Generation Script

```python
#!/usr/bin/env python3
"""case_004_nrel_phase_vi_mrf CAD generator.

Tier-1 reference-derived source:
- NREL Phase VI / UAE rotor report, NREL/TP-500-29955.
- S809 airfoil coordinates from public NREL/UIUC-derived data.

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


CASE_ID = "case_004_nrel_phase_vi_mrf"
ASSEMBLY_NAME = CASE_ID

SOURCE_PAGE_URL = "https://doi.org/10.2172/15000240"
REFERENCE_REPORT_URL = "https://www.nrel.gov/docs/fy02osti/29955.pdf"
EXAWIND_BENCHMARK_URL = "https://exawind.github.io/exawind-benchmarks/exawind/NREL_Phase_VI_Turbine/README.html"
SOURCE_CACHE_NAME = "tier1_nrel_phase_vi_nrel_tp_500_29955.pdf"
SOURCE_SHA256 = ""

DEFAULT_REPO_ROOT = Path(os.environ.get("CFD_HARNESS_REPO", "/Users/Zhuanz/Desktop/cfd-harness-unified"))
PATCH_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

# === Rotor and MRF parameters ===
ROTOR_RADIUS_MM = 5029.0
ROTOR_DIAMETER_MM = 2.0 * ROTOR_RADIUS_MM
RPM = 72.0
OMEGA_RAD_PER_S = RPM * 2.0 * math.pi / 60.0
ROTATION_AXIS_XYZ = (1.0, 0.0, 0.0)
ROTATION_ORIGIN_MM = (0.0, 0.0, 0.0)

TIP_PITCH_DEG = 3.0
PITCH_AXIS_CHORD_FRAC = 0.30
ROOT_CYL_END_MM = 883.0
AIRFOIL_START_MM = 1257.0

HUB_RADIUS_MM = 360.0
HUB_LENGTH_MM = 820.0
SPINNER_LENGTH_MM = 520.0

ROTATING_ZONE_RADIUS_MM = 1.12 * ROTOR_RADIUS_MM
ROTATING_ZONE_LENGTH_MM = 1800.0
ROTATING_ZONE_CENTER_X_MM = -200.0

# === Stationary hardware ===
NACELLE_X_MM = 1600.0
NACELLE_LENGTH_MM = 1800.0
NACELLE_WIDTH_MM = 900.0
NACELLE_HEIGHT_MM = 820.0

TOWER_X_MM = 1400.0
TOWER_BASE_Z_MM = -7800.0
TOWER_TOP_Z_MM = -370.0
TOWER_BASE_RADIUS_MM = 305.0
TOWER_TOP_RADIUS_MM = 205.0

# D1: controlled sub-mm gap on nacelle side access cover.
DEFECT_GAP_MM = 0.30
SERVICE_COVER_LENGTH_MM = 620.0
SERVICE_COVER_THICKNESS_MM = 35.0
SERVICE_COVER_HEIGHT_MM = 320.0
SERVICE_COVER_Z_MM = 120.0

# D8: controlled sub-mm thin plate.
YAW_SHIM_LENGTH_MM = 320.0
YAW_SHIM_THICKNESS_MM = 0.75
YAW_SHIM_HEIGHT_MM = 220.0

# === Domain sizing ===
DOMAIN_UPSTREAM_DIAMETERS = 3.0
DOMAIN_DOWNSTREAM_DIAMETERS = 6.0
DOMAIN_HALF_WIDTH_MM = 12500.0
DOMAIN_HALF_HEIGHT_MM = 12500.0
DOMAIN_PLATE_THICKNESS_MM = 100.0

PART_NAMES = [
    "rotating_cellzone",
    "stationary_domain",
    "rotor_blade_A",
    "rotor_blade_B",
    "hub_spinner",
    "nacelle_body",
    "tower_body",
    "nacelle_service_cover",
    "yaw_sensor_shim",
    "inlet",
    "outlet",
    "tunnel_walls",
]

# S809 coordinates in Selig order: TE upper -> LE -> TE lower.
S809_COORDS = [
    (1.000000, 0.000000),
    (0.996203, 0.000487),
    (0.985190, 0.002373),
    (0.967844, 0.005960),
    (0.945073, 0.011024),
    (0.917488, 0.017033),
    (0.885293, 0.023458),
    (0.848455, 0.030280),
    (0.807470, 0.037766),
    (0.763042, 0.045974),
    (0.715952, 0.054872),
    (0.667064, 0.064353),
    (0.617331, 0.074214),
    (0.567830, 0.084095),
    (0.519832, 0.093268),
    (0.474243, 0.099392),
    (0.428461, 0.101760),
    (0.382612, 0.101840),
    (0.337260, 0.100070),
    (0.292970, 0.096703),
    (0.250247, 0.091908),
    (0.209576, 0.085851),
    (0.171409, 0.078687),
    (0.136174, 0.070580),
    (0.104263, 0.061697),
    (0.076035, 0.052224),
    (0.051823, 0.042352),
    (0.031910, 0.032299),
    (0.016590, 0.022290),
    (0.006026, 0.012615),
    (0.000658, 0.003723),
    (0.000204, 0.001942),
    (0.000000, -0.000020),
    (0.000213, -0.001794),
    (0.001045, -0.003477),
    (0.001208, -0.003724),
    (0.002398, -0.005266),
    (0.009313, -0.011499),
    (0.023230, -0.020399),
    (0.042320, -0.030269),
    (0.065877, -0.040821),
    (0.093426, -0.051923),
    (0.124111, -0.063082),
    (0.157653, -0.073730),
    (0.193738, -0.083567),
    (0.231914, -0.092442),
    (0.271438, -0.099905),
    (0.311968, -0.105281),
    (0.353370, -0.108181),
    (0.395329, -0.108011),
    (0.438273, -0.104552),
    (0.481920, -0.097347),
    (0.527928, -0.086571),
    (0.576211, -0.073979),
    (0.626092, -0.060644),
    (0.676744, -0.047441),
    (0.727211, -0.035100),
    (0.776432, -0.024204),
    (0.823285, -0.015163),
    (0.866630, -0.008204),
    (0.905365, -0.003363),
    (0.938474, -0.000487),
    (0.965086, 0.000743),
    (0.984478, 0.000775),
    (0.996141, 0.000290),
    (1.000000, 0.000000),
]

# Radius [m], chord [m], twist [deg]. Published Phase VI style station table.
BLADE_STATIONS = [
    (0.508, 0.218, 0.000),
    (0.660, 0.218, 0.000),
    (0.883, 0.183, 0.000),
    (1.008, 0.349, 6.700),
    (1.067, 0.441, 9.900),
    (1.133, 0.544, 13.400),
    (1.257, 0.737, 20.040),
    (1.343, 0.728, 18.074),
    (1.510, 0.711, 14.292),
    (1.648, 0.697, 11.909),
    (1.952, 0.666, 7.979),
    (2.257, 0.636, 5.308),
    (2.343, 0.627, 4.715),
    (2.562, 0.605, 3.425),
    (2.867, 0.574, 2.083),
    (3.172, 0.543, 1.150),
    (3.185, 0.542, 1.115),
    (3.476, 0.512, 0.494),
    (3.781, 0.482, -0.015),
    (4.023, 0.457, -0.381),
    (4.086, 0.451, -0.475),
    (4.391, 0.420, -0.920),
    (4.696, 0.389, -1.352),
    (4.780, 0.381, -1.469),
    (5.000, 0.358, -1.775),
    (5.029, 0.355, -1.815),
]


def validate_patch_names() -> None:
    seen = set()
    for name in PART_NAMES:
        if not PATCH_NAME_RE.match(name):
            raise ValueError(f"Invalid OpenFOAM name: {name}")
        if name in seen:
            raise ValueError(f"Duplicate name: {name}")
        seen.add(name)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve_reference_report(script_dir: Path, require: bool) -> Path | None:
    candidates = [
        script_dir.parent / "inputs" / "cache" / SOURCE_CACHE_NAME,
        DEFAULT_REPO_ROOT / ".planning" / "cad_cache" / SOURCE_CACHE_NAME,
    ]
    for candidate in candidates:
        if candidate.exists():
            if SOURCE_SHA256 and sha256_file(candidate) != SOURCE_SHA256:
                raise RuntimeError(f"Cached report hash mismatch: {candidate}")
            return candidate

    target = candidates[0]
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp")

    try:
        req = urllib.request.Request(
            REFERENCE_REPORT_URL,
            headers={"User-Agent": f"cfd-harness-unified-{CASE_ID}/1.0"},
        )
        with urllib.request.urlopen(req, timeout=120) as response, tmp.open("wb") as f:
            shutil.copyfileobj(response, f)
        if SOURCE_SHA256 and sha256_file(tmp) != SOURCE_SHA256:
            tmp.unlink(missing_ok=True)
            raise RuntimeError("Downloaded reference report SHA256 did not match SOURCE_SHA256")
        tmp.replace(target)
        return target
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        if require:
            raise
        print(f"Warning: Tier-1 report cache fetch failed: {exc}", file=sys.stderr)
        return None


def make_box(dx: float, dy: float, dz: float, center: tuple[float, float, float]) -> cq.Shape:
    return cq.Workplane("XY").box(dx, dy, dz, centered=True).translate(center).val()


def cylinder_along_x(radius: float, length: float, center_x: float) -> cq.Shape:
    start_x = center_x - 0.5 * length
    return cq.Workplane("YZ", origin=(start_x, 0.0, 0.0)).circle(radius).extrude(length).val()


def root_blend_fraction(r_mm: float) -> float:
    if r_mm <= ROOT_CYL_END_MM:
        return 0.0
    if r_mm >= AIRFOIL_START_MM:
        return 1.0
    return (r_mm - ROOT_CYL_END_MM) / (AIRFOIL_START_MM - ROOT_CYL_END_MM)


def blended_section_coords(r_mm: float) -> list[tuple[float, float]]:
    blend = root_blend_fraction(r_mm)
    coords = []
    for x_norm, y_norm in S809_COORDS[:-1]:
        x_centered = x_norm - 0.5
        circle_mag = math.sqrt(max(0.0, 0.25 - x_centered * x_centered))
        circle_y = circle_mag if y_norm >= 0.0 else -circle_mag

        # Blend circular root into the published S809 section through the transition span.
        y_blended = (1.0 - blend) * circle_y + blend * y_norm
        coords.append((x_norm, y_blended))
    return coords


def section_wire(r_m: float, chord_m: float, twist_deg: float) -> cq.Wire:
    r_mm = r_m * 1000.0
    chord_mm = chord_m * 1000.0
    theta = math.radians(twist_deg + TIP_PITCH_DEG)
    ct = math.cos(theta)
    st = math.sin(theta)

    points = []
    for x_norm, y_norm in blended_section_coords(r_mm):
        x_local = (x_norm - PITCH_AXIS_CHORD_FRAC) * chord_mm
        y_local = y_norm * chord_mm

        # Twist about the local radial axis, matching wind-turbine pitch-axis convention.
        x_rot = x_local * ct - y_local * st
        y_rot = x_local * st + y_local * ct
        points.append(cq.Vector(x_rot, y_rot, r_mm))

    points.append(points[0])
    return cq.Wire.makePolygon(points)


def build_blade() -> cq.Shape:
    wires = [section_wire(r_m, chord_m, twist_deg) for r_m, chord_m, twist_deg in BLADE_STATIONS]

    # Loft preserves the tapered/twisted NREL Phase VI blade signature.
    return cq.Solid.makeLoft(wires, ruled=False)


def build_hub_spinner() -> cq.Shape:
    hub = cylinder_along_x(HUB_RADIUS_MM, HUB_LENGTH_MM, 0.0)

    # Spinner cone gives the rotating assembly a realistic upstream nose.
    nose = cq.Solid.makeCone(
        80.0,
        HUB_RADIUS_MM,
        SPINNER_LENGTH_MM,
        cq.Vector(-0.5 * HUB_LENGTH_MM - SPINNER_LENGTH_MM, 0.0, 0.0),
        cq.Vector(1.0, 0.0, 0.0),
    )
    return cq.Compound.makeCompound([hub, nose])


def build_stationary_hardware() -> tuple[cq.Shape, cq.Shape, cq.Shape, cq.Shape]:
    nacelle_body = make_box(
        NACELLE_LENGTH_MM,
        NACELLE_WIDTH_MM,
        NACELLE_HEIGHT_MM,
        (NACELLE_X_MM, 0.0, 0.0),
    )

    tower_height = TOWER_TOP_Z_MM - TOWER_BASE_Z_MM
    tower_body = cq.Solid.makeCone(
        TOWER_BASE_RADIUS_MM,
        TOWER_TOP_RADIUS_MM,
        tower_height,
        cq.Vector(TOWER_X_MM, 0.0, TOWER_BASE_Z_MM),
        cq.Vector(0.0, 0.0, 1.0),
    )

    cover_y = 0.5 * NACELLE_WIDTH_MM + 0.5 * SERVICE_COVER_THICKNESS_MM + DEFECT_GAP_MM

    # D1: the cover is intentionally separated from the nacelle side by 0.30 mm.
    nacelle_service_cover = make_box(
        SERVICE_COVER_LENGTH_MM,
        SERVICE_COVER_THICKNESS_MM,
        SERVICE_COVER_HEIGHT_MM,
        (NACELLE_X_MM, cover_y, SERVICE_COVER_Z_MM),
    )

    # D8: this shim is a real 0.75 mm-thick solid body, outside blade measurement zones.
    yaw_sensor_shim = make_box(
        YAW_SHIM_LENGTH_MM,
        YAW_SHIM_THICKNESS_MM,
        YAW_SHIM_HEIGHT_MM,
        (TOWER_X_MM - 180.0, -0.5 * NACELLE_WIDTH_MM - 40.0, -430.0),
    )
    return nacelle_body, tower_body, nacelle_service_cover, yaw_sensor_shim


def build_zone_and_domain() -> tuple[cq.Shape, cq.Shape, cq.Shape, cq.Shape, cq.Shape]:
    rotating_cellzone = cylinder_along_x(
        ROTATING_ZONE_RADIUS_MM,
        ROTATING_ZONE_LENGTH_MM,
        ROTATING_ZONE_CENTER_X_MM,
    )

    xmin = -DOMAIN_UPSTREAM_DIAMETERS * ROTOR_DIAMETER_MM
    xmax = DOMAIN_DOWNSTREAM_DIAMETERS * ROTOR_DIAMETER_MM
    ymin = -DOMAIN_HALF_WIDTH_MM
    ymax = DOMAIN_HALF_WIDTH_MM
    zmin = -DOMAIN_HALF_HEIGHT_MM
    zmax = DOMAIN_HALF_HEIGHT_MM

    lx = xmax - xmin
    ly = ymax - ymin
    lz = zmax - zmin
    cx = 0.5 * (xmin + xmax)
    cy = 0.0
    cz = 0.0
    t = DOMAIN_PLATE_THICKNESS_MM

    # Stationary domain is a named volume so the sub-session can build background mesh logic.
    stationary_domain = make_box(lx, ly, lz, (cx, cy, cz))

    inlet = make_box(t, ly, lz, (xmin, cy, cz))
    outlet = make_box(t, ly, lz, (xmax, cy, cz))

    top = make_box(lx, ly, t, (cx, cy, zmax))
    bottom = make_box(lx, ly, t, (cx, cy, zmin))
    side_pos = make_box(lx, t, lz, (cx, ymax, cz))
    side_neg = make_box(lx, t, lz, (cx, ymin, cz))
    tunnel_walls = cq.Compound.makeCompound([top, bottom, side_pos, side_neg])

    return rotating_cellzone, stationary_domain, inlet, outlet, tunnel_walls


def build() -> cq.Assembly:
    validate_patch_names()

    blade_a = build_blade()

    # The second blade is generated by a deterministic 180 deg rotation about the MRF axis.
    blade_b = blade_a.rotate((0.0, 0.0, 0.0), ROTATION_AXIS_XYZ, 180.0)

    hub_spinner = build_hub_spinner()
    nacelle_body, tower_body, nacelle_service_cover, yaw_sensor_shim = build_stationary_hardware()
    rotating_cellzone, stationary_domain, inlet, outlet, tunnel_walls = build_zone_and_domain()

    asm = cq.Assembly(name=ASSEMBLY_NAME)
    asm.add(rotating_cellzone, name="rotating_cellzone")
    asm.add(stationary_domain, name="stationary_domain")
    asm.add(blade_a, name="rotor_blade_A")
    asm.add(blade_b, name="rotor_blade_B")
    asm.add(hub_spinner, name="hub_spinner")
    asm.add(nacelle_body, name="nacelle_body")
    asm.add(tower_body, name="tower_body")
    asm.add(nacelle_service_cover, name="nacelle_service_cover")
    asm.add(yaw_sensor_shim, name="yaw_sensor_shim")
    asm.add(inlet, name="inlet")
    asm.add(outlet, name="outlet")
    asm.add(tunnel_walls, name="tunnel_walls")
    return asm


def canonicalize_step(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="ignore")
    replacement = (
        "FILE_NAME('case_004_nrel_phase_vi_mrf.step',"
        "'1970-01-01T00:00:00',"
        "('cfd-harness-unified'),"
        "('Codex'),"
        "'OpenCASCADE',"
        "'CadQuery',"
        "'none');"
    )
    text = re.sub(r"FILE_NAME\s*\(.*?\);", replacement, text, count=1, flags=re.S)
    text = text.replace(str(path), "case_004_nrel_phase_vi_mrf.step")
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="Output STEP path")
    parser.add_argument(
        "--require-reference-cache",
        action="store_true",
        help="Fail if the Tier-1 NREL report cannot be cached.",
    )
    args = parser.parse_args()

    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    script_dir = Path(__file__).resolve().parent
    reference_report = resolve_reference_report(script_dir, args.require_reference_cache)

    asm = build()

    # Export through a local temporary file so failed writes never leave a partial STEP.
    with tempfile.TemporaryDirectory(dir=str(out_path.parent)) as tmpdir:
        tmp_step = Path(tmpdir) / "case_004_nrel_phase_vi_mrf.step"
        asm.save(str(tmp_step), exportType="STEP")
        canonicalize_step(tmp_step)
        shutil.copyfile(tmp_step, out_path)

    print(f"Wrote {out_path}")
    print(f"Case: {CASE_ID}")
    print(f"Omega rad/s: {OMEGA_RAD_PER_S:.9f}")
    print(f"Rotation axis: {ROTATION_AXIS_XYZ}")
    print(f"Tier-1 source page: {SOURCE_PAGE_URL}")
    print(f"Tier-1 report cache: {reference_report if reference_report else 'not cached'}")
    print(f"Secondary benchmark: {EXAWIND_BENCHMARK_URL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

## Deliverable 3 — STEP File Path

`/Users/Zhuanz/Desktop/case_004_nrel_phase_vi_mrf/inputs/cad_codex_v1.step`

## Deliverable 4 — Parts Manifest

```yaml
case_id: case_004_nrel_phase_vi_mrf
cad_source: tier1_reference_derived_nrel_phase_vi
cad_source_tier: Tier_1
cad_source_url: https://www.nrel.gov/docs/fy02osti/29955.pdf
source_page_url: https://doi.org/10.2172/15000240
secondary_benchmark_url: https://exawind.github.io/exawind-benchmarks/exawind/NREL_Phase_VI_Turbine/README.html
airfoil_coordinate_url: https://airfoiltools.com/airfoil/details?airfoil=s809-nr
license: NREL_DOE_public_technical_report_verify_before_external_redistribution
generation_script: scripts/build_cad.py
step_file: inputs/cad_codex_v1.step
units_in_step: mm
solver_target_v1: simpleFoam_plus_MRF
solver_target_v2: pimpleFoam_plus_AMI_sliding_mesh_if_force_oscillation
numerics_class: incompressible_RANS_MRF_rotating_machinery

rotation:
  origin_xyz_mm: [0.0, 0.0, 0.0]
  rotation_axis_xyz: [1.0, 0.0, 0.0]
  omega_rad_per_s: 7.539822369
  rpm: 72.0

periodic_patches: []
cyclic_patches: []
cyclicAMI_patches: []
future_sliding_mesh_interface_names_if_v2:
  - rotor_ami_inner
  - stator_ami_outer

parts:
  - name: rotating_cellzone
    role: rotating_cellzone
    zone_type: MRF
    rotation_origin_xyz_mm: [0.0, 0.0, 0.0]
    rotation_axis_xyz: [1.0, 0.0, 0.0]
    omega_rad_per_s: 7.539822369
    radius_mm: 5632.48
    length_mm: 1800.0
    notes: "Explicit cylindrical cellZone volume; MRFProperties must reference this exact name."

  - name: stationary_domain
    role: stationary_domain
    notes: "Background wind-tunnel/domain volume for stationary mesh construction."

  - name: rotor_blade_A
    role: rotating_wall
    parent_cellzone: rotating_cellzone
    bc:
      U: movingWallVelocity_or_MRF_consistent_noSlip
      p: zeroGradient
      nut: nutkWallFunction
      k: kqRWallFunction
      omega: omegaWallFunction
    notes: "NREL Phase VI blade at 0 degree azimuth; pressure-tap stations untouched."

  - name: rotor_blade_B
    role: rotating_wall
    parent_cellzone: rotating_cellzone
    bc:
      U: movingWallVelocity_or_MRF_consistent_noSlip
      p: zeroGradient
      nut: nutkWallFunction
      k: kqRWallFunction
      omega: omegaWallFunction
    notes: "Second blade generated by 180 degree rotation about x-axis."

  - name: hub_spinner
    role: rotating_wall
    parent_cellzone: rotating_cellzone
    bc:
      U: movingWallVelocity_or_MRF_consistent_noSlip
      p: zeroGradient
    notes: "Hub and upstream spinner compound."

  - name: nacelle_body
    role: stationary_wall
    bc:
      U: noSlip
      p: zeroGradient
    notes: "Downstream nacelle body; participates in D1 only through nearby cover gap."

  - name: tower_body
    role: stationary_wall
    bc:
      U: noSlip
      p: zeroGradient
    notes: "Simplified tapered tower downstream of rotor plane."

  - name: nacelle_service_cover
    role: stationary_wall_auxiliary_defect
    defect_id: D1
    bc:
      U: noSlip
      p: zeroGradient
    notes: "Offset from nacelle_body by 0.30 mm intentional gap."

  - name: yaw_sensor_shim
    role: stationary_wall_auxiliary_defect
    defect_id: D8
    bc:
      U: noSlip
      p: zeroGradient
    notes: "0.75 mm thin shim body outside blade measurement zones."

  - name: inlet
    role: velocity_inlet
    U_inf_mps_baseline: 7.0
    U_inf_mps_sweep: [7.0, 10.0, 15.0]
    turbulence_intensity: "0.1% to 0.5%"
    bc:
      U: fixedValue
      p: zeroGradient

  - name: outlet
    role: pressure_outlet
    p_gauge: 0.0
    bc:
      U: zeroGradient
      p: fixedValue

  - name: tunnel_walls
    role: slip_or_farfield_wall
    bc:
      U: slip
      p: zeroGradient
    notes: "Four side plates grouped as one named compound body."

patch_naming_check:
  - all_names_match_regex: "^[A-Za-z][A-Za-z0-9_]*$"
  - no_duplicate_names: true
  - no_spaces_or_hyphens: true
```

## Deliverable 5 — Defect Manifest

```yaml
case_id: case_004_nrel_phase_vi_mrf
defect_count: 2
cad_source_tier: Tier_1
reference_data_validity: "preserved: no injected defect touches rotor_blade_A or rotor_blade_B; NREL blade pressure-tap radial stations remain geometrically untouched. Integrated thrust/torque should be reported as defected-nacelle configuration, not strict wind-tunnel parity."

defects:
  - id: D1
    catalog_name: sub_mm_gap_between_bodies
    description: "0.30 mm gap between nacelle_body and nacelle_service_cover on the +Y side of the downstream nacelle."
    location:
      bodies_involved:
        - nacelle_body
        - nacelle_service_cover
      region: "downstream nacelle service cover, outside all blade pressure measurement zones"
      approx_coords_mm: [1600.0, 450.15, 120.0]
    measurement:
      claimed_gap_mm: 0.30
      verification_command: "FreeCADCmd -c \"import FreeCAD as App, Import; doc=App.newDocument(); Import.insert('/Users/Zhuanz/Desktop/case_004_nrel_phase_vi_mrf/inputs/cad_codex_v1.step', doc.Name); o={x.Label:x for x in doc.Objects}; print(o['nacelle_body'].Shape.distToShape(o['nacelle_service_cover'].Shape)[0])\""
    expected_advisor_to_catch: virtual_interface_detector
    hypothesized_v_series_match: "V8/V10-style sliver-mesh risk only; no formal inheritance from compressible-buoyant V-series"
    reference_data_validity: "preserved for blade pressure data; defect is on stationary nacelle hardware downstream of rotor disk"

  - id: D8
    catalog_name: sub_mm_thin_shell
    description: "0.75 mm thick yaw_sensor_shim plate mounted near the nacelle/tower junction."
    location:
      bodies_involved:
        - yaw_sensor_shim
      region: "tower/nacelle auxiliary instrumentation area, outside rotor blade measurement zones"
      approx_coords_mm: [1220.0, -490.0, -430.0]
    measurement:
      claimed_thickness_mm: 0.75
      verification_command: "FreeCADCmd -c \"import FreeCAD as App, Import; doc=App.newDocument(); Import.insert('/Users/Zhuanz/Desktop/case_004_nrel_phase_vi_mrf/inputs/cad_codex_v1.step', doc.Name); o={x.Label:x for x in doc.Objects}; bb=o['yaw_sensor_shim'].Shape.BoundBox; print(min(bb.XLength, bb.YLength, bb.ZLength))\""
    expected_advisor_to_catch: thin_wall_advisor
    hypothesized_v_series_match: "V10-style thin-wall advisor coverage only; no inherited incompressible-MRF numerics finding"
    reference_data_validity: "preserved for published blade geometry and pressure-tap regions"
```

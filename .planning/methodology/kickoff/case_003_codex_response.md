## Deliverable 1 — Engineering brief

### Component picked + bank ID

**Case ID:** `case_003_crm_hls_boundary_layer`

**Component:** NASA/AIAA HLPW6 CRM-HLS, a simplified high-lift Common Research Model wing with main element, slat, semi-span flap, and slat brackets.

**Bank/source IDs:**
- Component-bank class: `C3` external aircraft wing/body-junction class, upgraded to Tier-1 public aerospace CAD.
- Public CAD source: `T1.A1/T1.A4` CRM / high-lift public reference family.
- Source page: https://aiaa-hlpw.org/HLPW6/cases
- Direct STP: https://aiaa-hlpw.org/assets/HLPW6/CRM_HLS_HLPW6_TC1.stp
- License/source status: public HLPW/NASA-linked workshop geometry; treat as NASA/HLPW public reference data and verify redistribution rules before publishing derived STEP outside the project.

This fills the uncovered **external high-Re + boundary-layer** row with a real transport-aircraft high-lift component, not an academic single airfoil.

### Engineering question

Can the harness ingest and mesh a public industrial high-lift aircraft STEP, preserve named CFD boundary patches, detect CAD defects before meshing, and obtain a stable incompressible-RANS baseline for separated high-lift external flow?

### Physics signature

- Solver target v1: `simpleFoam`
- v2 fallback: `pimpleFoam` only if steady high-lift separation oscillates too strongly
- Flow model: incompressible RANS, `kOmegaSST`
- Freestream: air at 288 K, `nu = 1.5e-5 m2/s`
- Suggested `U_inf = 55 m/s`, `alpha = 8 deg`
- Mach estimate: `M ≈ 0.16`, acceptable for incompressible baseline
- Reynolds estimate: `Re ≈ 3.7e6` per 1 m reference chord
- Regime: turbulent boundary layer, slat/flap wakes, bracket-induced separation, adverse-pressure-gradient recovery

### Parts inventory

- `airframe_reference`: imported CRM-HLS reference geometry, wall
- `root_mount_pad`: auxiliary root-side model fixture, wall
- `root_mount_cover`: auxiliary fixture cover with intentional sub-mm gap, wall
- `thin_access_plate`: intentionally thin root-side access plate, wall
- `inlet`: upstream domain boundary
- `outlet`: downstream domain boundary
- `symmetry_plane`: inboard computational symmetry boundary
- `farfield_top`: top farfield
- `farfield_bottom`: bottom farfield
- `farfield_outer`: outboard farfield

### Boundary conditions plan

- `inlet`: `fixedValue U = (U*cos(alpha), 0, U*sin(alpha))`, `zeroGradient p`, fixed turbulence values from `I=0.5%`
- `outlet`: `zeroGradient U`, `fixedValue p=0`
- `farfield_*`: `freestreamVelocity` for `U`, `freestreamPressure` for `p`
- `symmetry_plane`: `symmetryPlane`
- all wall patches: `noSlip U`, `zeroGradient p`, high-Re wall functions for `nut`, `k`, `omega`
- y+ target: first production attempt `30 < y+ < 100`; report wall-adjacent coverage before trusting forces

### Expected metrics

- `Cl`, `Cd`, `Cm` from `forceCoeffs`
- sectional `Cp` slices on main element / slat / flap
- y+ histogram and minimum wall-normal spacing
- wake/separation visualization behind slat brackets and flap shoulder
- residual history, continuity error, force monitor stability
- advisor detection result for both injected defects

### Hypothesized failure modes

This incompressible-RANS case inherits **none** of the compressible-buoyant V3-V13/V15 numerics findings.

Expected new or analogous findings:
- STEP source/name preservation may exercise V1-style CAD ingest behavior.
- The D1 root-fixture gap may create sliver cells or local skewness, a V8-style geometry/mesh-quality analogue, not inherited numerics.
- The D8 thin plate should exercise the existing V10-style thin-wall advisor.
- High-lift separated steady RANS may converge to pseudo-steady force oscillation; if so, v2 should switch to transient `pimpleFoam`.

### Defect injection summary

Exactly two defects are injected outside the CRM-HLS wing/slat/flap measurement zones:

- `D1`: 0.35 mm gap between `root_mount_pad` and `root_mount_cover`
- `D8`: 0.80 mm thick `thin_access_plate`

Reference-data validity: geometry of the published wing/slat/flap pressure-section zones is preserved. Integrated force comparison should be treated as defected-geometry-only because the auxiliary root fixtures add small extra wetted area.

### Sub-session estimated effort

Estimated effort: **5-8 hours**, likely 3 versions:
- v1: CAD import, defect verification, coarse external mesh
- v2: boundary-layer refinement and y+ correction
- v3: production `simpleFoam`, or `pimpleFoam` if force monitors oscillate

## Deliverable 2 — CAD generation script

```python
#!/usr/bin/env python3
"""case_003_crm_hls_boundary_layer CAD generator.

Tier-1 source: NASA/AIAA HLPW6 CRM-HLS STP.
Designed by Codex per cfd-harness-unified case-design protocol.
"""

import argparse
import hashlib
import os
import re
import shutil
import sys
import tempfile
import urllib.request
from pathlib import Path

import cadquery as cq


CASE_ID = "case_003_crm_hls_boundary_layer"
ASSEMBLY_NAME = "case_003_crm_hls_boundary_layer"

SOURCE_PAGE_URL = "https://aiaa-hlpw.org/HLPW6/cases"
SOURCE_STEP_URL = "https://aiaa-hlpw.org/assets/HLPW6/CRM_HLS_HLPW6_TC1.stp"
SOURCE_CACHE_NAME = "tier1_crm_hls_hlpw6_tc1.stp"
SOURCE_SHA256 = ""  # Pin after first local cache validation if project policy requires it.

DEFAULT_REPO_ROOT = Path(os.environ.get("CFD_HARNESS_REPO", "/Users/Zhuanz/Desktop/cfd-harness-unified"))
PATCH_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

FREESTREAM_U_MPS = 55.0
ANGLE_OF_ATTACK_DEG = 8.0

DEFECT_GAP_MM = 0.35
THIN_PLATE_THICKNESS_MM = 0.80

ROOT_PAD_LENGTH_FRAC = 0.12
ROOT_PAD_WIDTH_FRAC = 0.025
ROOT_PAD_HEIGHT_FRAC = 0.020
THIN_PLATE_LENGTH_FRAC = 0.18
THIN_PLATE_WIDTH_FRAC = 0.045

UPSTREAM_CHORDS = 5.0
DOWNSTREAM_CHORDS = 10.0
SIDE_CHORDS = 5.0
TOP_CHORDS = 5.0
BOTTOM_CHORDS = 4.0
DOMAIN_PLATE_THICKNESS_FRAC = 0.001
DOMAIN_PLATE_THICKNESS_MIN_MM = 1.0

PART_NAMES = [
    "airframe_reference",
    "root_mount_pad",
    "root_mount_cover",
    "thin_access_plate",
    "inlet",
    "outlet",
    "symmetry_plane",
    "farfield_top",
    "farfield_bottom",
    "farfield_outer",
]


def validate_patch_names() -> None:
    seen = set()
    for name in PART_NAMES:
        if not PATCH_NAME_RE.match(name):
            raise ValueError(f"Invalid OpenFOAM patch name: {name}")
        if name in seen:
            raise ValueError(f"Duplicate patch name: {name}")
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
    env_source = os.environ.get("CASE003_SOURCE_STEP")
    if env_source:
        candidates.append(Path(env_source).expanduser())
    candidates.append(script_dir.parent / "inputs" / "cache" / SOURCE_CACHE_NAME)
    candidates.append(DEFAULT_REPO_ROOT / ".planning" / "cad_cache" / SOURCE_CACHE_NAME)
    return candidates


def download_source(target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")

    # Download only on cache miss so repeated runs use the same Tier-1 input bytes.
    req = urllib.request.Request(
        SOURCE_STEP_URL,
        headers={"User-Agent": "cfd-harness-unified-case003/1.0"},
    )
    with urllib.request.urlopen(req, timeout=120) as response, tmp.open("wb") as f:
        shutil.copyfileobj(response, f)

    if SOURCE_SHA256 and sha256_file(tmp) != SOURCE_SHA256:
        tmp.unlink(missing_ok=True)
        raise RuntimeError("Downloaded CRM-HLS STEP SHA256 did not match SOURCE_SHA256")

    tmp.replace(target)
    return target


def resolve_source_step(script_dir: Path, explicit_source: str | None) -> Path:
    for candidate in source_candidates(script_dir, explicit_source):
        if candidate.exists():
            if SOURCE_SHA256 and sha256_file(candidate) != SOURCE_SHA256:
                raise RuntimeError(f"Cached source hash mismatch: {candidate}")
            return candidate

    local_cache = script_dir.parent / "inputs" / "cache" / SOURCE_CACHE_NAME
    return download_source(local_cache)


def import_reference_shape(source_step: Path) -> cq.Shape:
    # Import the public reference as one named top-level CFD wall body.
    wp = cq.importers.importStep(str(source_step))
    shapes = [obj for obj in wp.objects if hasattr(obj, "BoundingBox")]
    if not shapes:
        return wp.val()
    if len(shapes) == 1:
        return shapes[0]
    return cq.Compound.makeCompound(shapes)


def make_box(dx: float, dy: float, dz: float, center: tuple[float, float, float]) -> cq.Shape:
    return cq.Workplane("XY").box(dx, dy, dz, centered=True).translate(center).val()


def bbox_union(shapes: list[cq.Shape]) -> tuple[float, float, float, float, float, float]:
    boxes = [shape.BoundingBox() for shape in shapes]
    return (
        min(bb.xmin for bb in boxes),
        max(bb.xmax for bb in boxes),
        min(bb.ymin for bb in boxes),
        max(bb.ymax for bb in boxes),
        min(bb.zmin for bb in boxes),
        max(bb.zmax for bb in boxes),
    )


def build_auxiliary_defects(airframe: cq.Shape) -> tuple[cq.Shape, cq.Shape, cq.Shape]:
    bb = airframe.BoundingBox()
    chord = max(bb.xlen, 100.0)
    span = max(bb.ylen, 100.0)
    height = max(bb.zlen, 0.15 * chord, 100.0)

    pad_dx = max(ROOT_PAD_LENGTH_FRAC * chord, 80.0)
    pad_dy = max(ROOT_PAD_WIDTH_FRAC * span, 12.0)
    pad_dz = max(ROOT_PAD_HEIGHT_FRAC * chord, 12.0)

    fixture_x = bb.xmin + 0.16 * chord
    fixture_y = bb.ymin + 0.055 * span
    pad_center_z = bb.zmin - 0.10 * height

    # D1 creates a measured air gap between two root-side fixture bodies.
    root_mount_pad = make_box(pad_dx, pad_dy, pad_dz, (fixture_x, fixture_y, pad_center_z))
    cover_center_z = pad_center_z + pad_dz + DEFECT_GAP_MM
    root_mount_cover = make_box(pad_dx, pad_dy, pad_dz, (fixture_x, fixture_y, cover_center_z))

    plate_dx = max(THIN_PLATE_LENGTH_FRAC * chord, 120.0)
    plate_dy = max(THIN_PLATE_WIDTH_FRAC * span, 25.0)
    plate_center = (
        bb.xmin + 0.34 * chord,
        bb.ymin + 0.10 * span,
        bb.zmin - 0.04 * height,
    )

    # D8 inserts a real sub-mm-thick shell-like body for thin-wall advisor coverage.
    thin_access_plate = make_box(
        plate_dx,
        plate_dy,
        THIN_PLATE_THICKNESS_MM,
        plate_center,
    )
    return root_mount_pad, root_mount_cover, thin_access_plate


def build_domain_patches(wall_shapes: list[cq.Shape], airframe: cq.Shape) -> dict[str, cq.Shape]:
    src_bb = airframe.BoundingBox()
    chord = max(src_bb.xlen, 100.0)
    xmin, xmax, ymin, ymax, zmin, zmax = bbox_union(wall_shapes)

    domain_xmin = xmin - UPSTREAM_CHORDS * chord
    domain_xmax = xmax + DOWNSTREAM_CHORDS * chord
    domain_ymin = ymin - SIDE_CHORDS * chord
    domain_ymax = ymax + SIDE_CHORDS * chord
    domain_zmin = zmin - BOTTOM_CHORDS * chord
    domain_zmax = zmax + TOP_CHORDS * chord

    lx = domain_xmax - domain_xmin
    ly = domain_ymax - domain_ymin
    lz = domain_zmax - domain_zmin
    t = max(DOMAIN_PLATE_THICKNESS_MIN_MM, DOMAIN_PLATE_THICKNESS_FRAC * chord)
    cy = 0.5 * (domain_ymin + domain_ymax)
    cz = 0.5 * (domain_zmin + domain_zmax)
    cx = 0.5 * (domain_xmin + domain_xmax)

    # Boundary plates are explicit named bodies so the CFD role manifest is deterministic.
    return {
        "inlet": make_box(t, ly, lz, (domain_xmin, cy, cz)),
        "outlet": make_box(t, ly, lz, (domain_xmax, cy, cz)),
        "symmetry_plane": make_box(lx, t, lz, (cx, domain_ymin, cz)),
        "farfield_top": make_box(lx, ly, t, (cx, cy, domain_zmax)),
        "farfield_bottom": make_box(lx, ly, t, (cx, cy, domain_zmin)),
        "farfield_outer": make_box(lx, t, lz, (cx, domain_ymax, cz)),
    }


def build(source_step: Path) -> cq.Assembly:
    validate_patch_names()

    airframe = import_reference_shape(source_step)

    # Auxiliary bodies carry the intentional CAD defects outside CRM-HLS measurement zones.
    root_mount_pad, root_mount_cover, thin_access_plate = build_auxiliary_defects(airframe)
    wall_shapes = [airframe, root_mount_pad, root_mount_cover, thin_access_plate]

    # Farfield patches are generated from the post-defect bounding box.
    domain = build_domain_patches(wall_shapes, airframe)

    asm = cq.Assembly(name=ASSEMBLY_NAME)
    asm.add(airframe, name="airframe_reference")
    asm.add(root_mount_pad, name="root_mount_pad")
    asm.add(root_mount_cover, name="root_mount_cover")
    asm.add(thin_access_plate, name="thin_access_plate")
    for name in ["inlet", "outlet", "symmetry_plane", "farfield_top", "farfield_bottom", "farfield_outer"]:
        asm.add(domain[name], name=name)
    return asm


def canonicalize_step(path: Path) -> None:
    text = path.read_text(errors="ignore")

    # Normalize volatile STEP header metadata so same inputs produce byte-identical output.
    replacement = (
        "FILE_NAME('case_003_crm_hls_boundary_layer.step',"
        "'1970-01-01T00:00:00',"
        "('cfd-harness-unified'),"
        "('Codex'),"
        "'OpenCASCADE',"
        "'CadQuery',"
        "'none');"
    )
    text = re.sub(r"FILE_NAME\s*\(.*?\);", replacement, text, count=1, flags=re.S)
    text = text.replace(str(path), "case_003_crm_hls_boundary_layer.step")
    path.write_text(text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="Output STEP path")
    parser.add_argument("--source-step", default=None, help="Optional already-downloaded CRM-HLS source STEP")
    args = parser.parse_args()

    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    script_dir = Path(__file__).resolve().parent
    source_step = resolve_source_step(script_dir, args.source_step)

    asm = build(source_step)

    # Export to a temporary path first so failed writes never leave a partial canonical STEP.
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_step = Path(tmpdir) / "case_003_crm_hls_boundary_layer.step"
        asm.save(str(tmp_step), exportType="STEP")
        canonicalize_step(tmp_step)
        shutil.copyfile(tmp_step, out_path)

    print(f"Wrote {out_path}")
    print(f"Tier-1 source: {source_step}")
    print(f"Source page: {SOURCE_PAGE_URL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

## Deliverable 3 — STEP file path

`/Users/Zhuanz/Desktop/case_003_crm_hls_boundary_layer/inputs/cad_codex_v1.step`

## Deliverable 4 — Parts manifest

```yaml
case_id: case_003_crm_hls_boundary_layer
cad_source: tier1_public_reference_hlpw6_crm_hls
cad_source_url: https://aiaa-hlpw.org/assets/HLPW6/CRM_HLS_HLPW6_TC1.stp
source_page_url: https://aiaa-hlpw.org/HLPW6/cases
license: NASA_HLPW_public_workshop_geometry_verify_before_external_redistribution
generation_script: scripts/build_cad.py
step_file: inputs/cad_codex_v1.step
units_in_step: mm
solver_target_v1: simpleFoam
numerics_class: incompressible_RANS_external_high_Re
parts:
  - name: airframe_reference
    role: wall_airframe
    bc:
      U: noSlip
      p: zeroGradient
      nut: nutkWallFunction
      k: kqRWallFunction
      omega: omegaWallFunction
    notes: "Imported CRM-HLS reference geometry flattened to one named CFD wall body."

  - name: root_mount_pad
    role: wall_auxiliary_fixture
    bc:
      U: noSlip
      p: zeroGradient
    notes: "Root-side auxiliary fixture body participating in D1."

  - name: root_mount_cover
    role: wall_auxiliary_fixture
    bc:
      U: noSlip
      p: zeroGradient
    notes: "Offset from root_mount_pad by 0.35 mm intentional D1 gap."

  - name: thin_access_plate
    role: wall_auxiliary_fixture
    bc:
      U: noSlip
      p: zeroGradient
    notes: "0.80 mm thin plate for D8 thin-wall detection."

  - name: inlet
    role: velocity_inlet
    U_inf_mps: 55.0
    alpha_deg: 8.0
    p: zeroGradient

  - name: outlet
    role: pressure_outlet
    p_gauge: 0
    U: zeroGradient

  - name: symmetry_plane
    role: symmetry
    bc: symmetryPlane

  - name: farfield_top
    role: farfield
    bc:
      U: freestreamVelocity
      p: freestreamPressure

  - name: farfield_bottom
    role: farfield
    bc:
      U: freestreamVelocity
      p: freestreamPressure

  - name: farfield_outer
    role: farfield
    bc:
      U: freestreamVelocity
      p: freestreamPressure

patch_naming_check:
  - all_names_match_regex: "^[A-Za-z][A-Za-z0-9_]*$"
  - no_duplicate_names: true
  - no_spaces_or_hyphens: true
```

## Deliverable 5 — Defect manifest

```yaml
case_id: case_003_crm_hls_boundary_layer
defect_count: 2
cad_source_tier: Tier_1
reference_data_validity: "partial: published CRM-HLS wing/slat/flap geometry zones are untouched; integrated force comparison is defected-geometry-only."
defects:
  - id: D1
    catalog_name: sub_mm_gap_between_bodies
    description: "0.35 mm gap between two root-side auxiliary fixture bodies that should be mated."
    location:
      bodies_involved:
        - root_mount_pad
        - root_mount_cover
      region: "inboard root-side auxiliary fixture, outside wing/slat/flap pressure-section zones"
      coords_mm: "programmatic: x=source_xmin+0.16*source_xlen, y=source_ymin+0.055*source_ylen, z=below source_zmin"
    measurement:
      claimed_gap_mm: 0.35
      verification_command: "FreeCADCmd -c \"import FreeCAD as App, Import; doc=App.newDocument(); Import.insert('/Users/Zhuanz/Desktop/case_003_crm_hls_boundary_layer/inputs/cad_codex_v1.step', doc.Name); o={x.Label:x for x in doc.Objects}; print(o['root_mount_pad'].Shape.distToShape(o['root_mount_cover'].Shape)[0])\""
    expected_advisor_to_catch: virtual_interface_detector
    hypothesized_v_series_match: "no inherited compressible finding; V8-style mesh-skewness/sliver analogue if snappyHexMesh resolves the 0.35 mm gap poorly"
    reference_data_validity: "preserved for local published wing/slat/flap geometry; do not use integrated force parity as benchmark"

  - id: D8
    catalog_name: sub_mm_thin_shell
    description: "0.80 mm thick access plate near the inboard root fixture."
    location:
      bodies_involved:
        - thin_access_plate
      region: "inboard root-side auxiliary fixture, outside published wing/slat/flap measurement sections"
      coords_mm: "programmatic: x=source_xmin+0.34*source_xlen, y=source_ymin+0.10*source_ylen, z=below source_zmin"
    measurement:
      claimed_thickness_mm: 0.80
      verification_command: "FreeCADCmd -c \"import FreeCAD as App, Import; doc=App.newDocument(); Import.insert('/Users/Zhuanz/Desktop/case_003_crm_hls_boundary_layer/inputs/cad_codex_v1.step', doc.Name); o={x.Label:x for x in doc.Objects}; bb=o['thin_access_plate'].Shape.BoundBox; print(min(bb.XLength, bb.YLength, bb.ZLength))\""
    expected_advisor_to_catch: thin_wall_advisor
    hypothesized_v_series_match: "no inherited compressible finding; V10-style thin-wall advisor coverage for external-RANS geometry"
    reference_data_validity: "preserved for published CRM-HLS airframe geometry; auxiliary defect body is excluded from reference-section comparisons"
```
tokens used
124,812
## Deliverable 1 — Engineering brief

### Component picked + bank ID

**Case ID:** `case_003_crm_hls_boundary_layer`

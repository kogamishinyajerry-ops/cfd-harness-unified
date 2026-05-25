"""DEC-V61-202 M3.6 cycle 1 · stage real-CAD demo case for end-to-end demo recording.

Stages `circular_cylinder_wake` (matching `knowledge/workbench_basics/circular_cylinder_wake.yaml`)
under `ui/backend/user_drafts/imported/circular_cylinder_wake/` with a real
cylinder.stl so the frontend's `useCaseGlb` path triggers and renders a real 3D
model in the geometry viewport (instead of the empty-CAD placeholder).

The case_id matches the canonical workbench-basics fixture, so BOTH endpoints fire:
  GET /api/cases/circular_cylinder_wake/workbench-basics  -> 200 (7 patches)
  GET /api/cases/circular_cylinder_wake/geometry/render   -> 200 (transcoded glb)
=> `authoredCadParts && caseProbe.available` => useCaseGlb=true => vtk.js renders.

Used by `scripts/dogfood/m35_workbench_demo.mjs` (which also flips Playwright
into `--use-gl=swiftshader` so vtk.js gets a software WebGL context in headless).

Idempotent. Re-run safely (overwrites case dir).
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import yaml

CASE_ID = "circular_cylinder_wake"
REPO_ROOT = Path(__file__).resolve().parents[2]
IMPORTED_DIR = REPO_ROOT / "ui" / "backend" / "user_drafts" / "imported"
CASE_DIR = IMPORTED_DIR / CASE_ID

# Minimal manifest matching the schema accepted by geometry/render endpoint.
# The actual basics (7 patches) come from knowledge/workbench_basics/circular_cylinder_wake.yaml,
# which is read independently by /api/cases/{id}/workbench-basics.
MANIFEST = {
    "source": "imported",
    "source_origin": "imported_user",
    "case_id": CASE_ID,
    "origin_filename": "cylinder.stl",
    "ingest_report_summary": {
        "is_watertight": True,
        "bbox_min": [-0.05, -0.05, -0.10],
        "bbox_max": [0.05, 0.05, 0.10],
        "bbox_extent": [0.10, 0.10, 0.20],
        "unit_guess": "m",
        "solid_count": 1,
        "face_count": 128,
        "is_single_shell": True,
        "patches": [{"name": "defaultFaces", "face_count": 128}],
        "all_default_faces": True,
        "warnings": [],
    },
    "created_at": "2026-05-25T10:50:00+00:00",
    "solver_version_compat": "openfoam-v2412",
}

# Source STL — copied from any existing imported cylinder case. Bytes are identical
# across imported_2026-05-22..05-24 cases (same upstream fixture).
SOURCE_STL_CANDIDATES = [
    IMPORTED_DIR / "imported_2026-05-22T14-32-48Z_6a44f896" / "triSurface" / "cylinder.stl",
    IMPORTED_DIR / "imported_2026-05-23T15-10-10Z_6dc3aad8" / "triSurface" / "cylinder.stl",
    IMPORTED_DIR / "imported_2026-05-24T04-53-39Z_8feab5af" / "triSurface" / "cylinder.stl",
]


def stage() -> int:
    if CASE_DIR.exists():
        print(f"[stage] removing existing {CASE_DIR}", file=sys.stderr)
        shutil.rmtree(CASE_DIR)
    (CASE_DIR / "triSurface").mkdir(parents=True, exist_ok=True)
    (CASE_DIR / "system").mkdir(parents=True, exist_ok=True)

    stl_src = next((p for p in SOURCE_STL_CANDIDATES if p.exists()), None)
    if stl_src is None:
        print(
            "[stage] ERROR: no source cylinder.stl found. Stage at least one of:\n"
            + "\n".join(f"  - {p}" for p in SOURCE_STL_CANDIDATES),
            file=sys.stderr,
        )
        return 1
    shutil.copy(stl_src, CASE_DIR / "triSurface" / "cylinder.stl")

    # Optional system files (controlDict + snappyHexMeshDict stub) for completeness.
    sys_src = stl_src.parent.parent / "system"
    if sys_src.exists():
        for f in sys_src.iterdir():
            if f.is_file():
                shutil.copy(f, CASE_DIR / "system" / f.name)

    with (CASE_DIR / "case_manifest.yaml").open("w") as fh:
        yaml.safe_dump(MANIFEST, fh, sort_keys=False, allow_unicode=True)

    print(f"[stage] staged {CASE_DIR}", file=sys.stderr)
    print(f"[stage] open http://localhost:5173/workbench/case/{CASE_ID}?step=geometry", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(stage())

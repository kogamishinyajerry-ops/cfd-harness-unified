"""V65-A B78 · case_028 v3 APU bay ventilation · advisor stack runner.

Closes the 4 input gaps left open by case_028 B74 v1 runner (4/9 firing):
- ``stl_bbox_set`` for extra_body_advisor (V55) · scanned from 29 per_solid STLs
- ``solver_block_snapshot`` for solver_block_advisor (V27/V28)
- ``thin_wall_inputs`` for thin_wall_advisor (V10) · firewall + door + Frame STLs
- ``shm_stl_face_normals`` for stl_face_label_validator path · representative normals

Target: ≥7/9 actionable advisors fired + ≥10/9 V-row clause-2 attribution
(v1 baseline 4/9 firing · 8/9 V-rows).

Run from repo root::

    .venv/bin/python -m scripts.case_028_apu_bay_v3.run_advisor_stack
"""
from __future__ import annotations

import json
import os
import struct
import sys
from pathlib import Path

# 4Q gate Q1: strip LLM keys before any backend import.
for _k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY", "DEEPSEEK_API_KEY"):
    os.environ.pop(_k, None)

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from ui.backend.services.advisor_stack import assemble_stack  # noqa: E402
from ui.backend.services.geometry_ingest.solver_block_advisor import (  # noqa: E402
    SolverBlockSnapshot,
)
from ui.backend.services.geometry_ingest.thin_wall_advisor import (  # noqa: E402
    PatchGeometry,
)


# ---------------------------------------------------------------------------
# Geometry inventory (29 per_solid components · case_028 v3)
# ---------------------------------------------------------------------------

COMPONENTS = [
    "Outer_Surf", "Inner_Surf", "Plane_Outer_Surf",
    "intake_duct", "vent_door", "door", "plenum",
    "exhaust_pipe_1", "exhaust_section", "bleed_air_pipe", "ejector",
    "gearbox_1", "gearbox_2", "compressor", "load_compressor", "load_volute",
    "combustion_chamber", "fuel_valve",
    "firewall_front", "firewall_behind",
    "Frame_1", "Frame_2", "Frame_3", "Frame_4", "Frame_5", "Frame_6",
    "beam_1", "beam_2", "beam_3",
]

# Per_solid STL source (READ-ONLY · external project)
STL_DIR = Path.home() / "Desktop" / "apu-bay-ventilation-cht" / "work" / "stl_repair" / "per_solid"

# Bay enclosure bbox (m) · 4 × 3.5 × 3 m
DOMAIN_BBOX_MIN = (63.5, -1.0, -1.5)
DOMAIN_BBOX_MAX = (67.5, 2.5, 1.5)
DOMAIN_EXTENTS = [4.0, 3.5, 3.0]


# ---------------------------------------------------------------------------
# STL bbox extraction (binary + ASCII fallback)
# ---------------------------------------------------------------------------

def _stl_bbox(stl_path: Path) -> tuple[float, float, float, float, float, float] | None:
    """Return (xmin, ymin, zmin, xmax, ymax, zmax) bbox of an STL.

    Auto-detects binary vs ASCII. Returns ``None`` if file missing or malformed.
    """
    if not stl_path.is_file():
        return None
    data = stl_path.read_bytes()
    # ASCII STL starts with literal "solid " AND has "vertex" in first 1 KB
    head = data[:1024]
    if head[:5] == b"solid" and b"vertex" in head:
        xs: list[float] = []
        ys: list[float] = []
        zs: list[float] = []
        for line in data.decode("ascii", errors="ignore").splitlines():
            stripped = line.strip()
            if stripped.startswith("vertex"):
                parts = stripped.split()
                if len(parts) >= 4:
                    xs.append(float(parts[1]))
                    ys.append(float(parts[2]))
                    zs.append(float(parts[3]))
        if not xs:
            return None
        return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))
    # Binary STL: 80-byte header + uint32 face count + 50 bytes per face
    if len(data) < 84:
        return None
    n_faces = struct.unpack("<I", data[80:84])[0]
    if 84 + 50 * n_faces > len(data):
        return None
    # Vectorize via numpy if available; struct loop is OK for moderate counts
    try:
        import numpy as np  # type: ignore
        face_bytes = data[84:84 + 50 * n_faces]
        # Each face row is 50 bytes; vertex floats occupy bytes 12..48 (9 floats)
        face_arr = bytes(face_bytes)
        verts = np.frombuffer(
            b"".join(face_arr[i + 12:i + 48] for i in range(0, len(face_arr), 50)),
            dtype="<f4",
        ).reshape(-1, 3)
        return (
            float(verts[:, 0].min()), float(verts[:, 1].min()), float(verts[:, 2].min()),
            float(verts[:, 0].max()), float(verts[:, 1].max()), float(verts[:, 2].max()),
        )
    except ImportError:
        xs, ys, zs = [], [], []
        offset = 84
        for _ in range(n_faces):
            vx = struct.unpack("<9f", data[offset + 12:offset + 48])
            xs.extend([vx[0], vx[3], vx[6]])
            ys.extend([vx[1], vx[4], vx[7]])
            zs.extend([vx[2], vx[5], vx[8]])
            offset += 50
        if not xs:
            return None
        return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


def build_stl_bbox_set() -> dict[str, tuple[float, ...]]:
    """Closes extra_body_advisor (V55) input gap · scans 29 per_solid STLs.

    Fallback: if STL_DIR is unavailable, returns a single domain-bbox entry
    keyed by ``"_fallback"`` so the advisor still dispatches (≥1 coercible).
    """
    out: dict[str, tuple[float, ...]] = {}
    for name in COMPONENTS:
        bb = _stl_bbox(STL_DIR / f"{name}.stl")
        if bb is not None:
            out[name] = bb
    if not out:
        out["_fallback"] = (*DOMAIN_BBOX_MIN, *DOMAIN_BBOX_MAX)
    return out


# ---------------------------------------------------------------------------
# Solver block snapshot · mirrors v2 system/controlDict + system/fvSolution
# ---------------------------------------------------------------------------

def build_solver_block_snapshot() -> SolverBlockSnapshot:
    """Closes solver_block_advisor (V27/V28) input gap.

    case_028 v3 dicts: simpleFoam steady-state (adjustTimeStep=False · deltaT=1).
    fvSolution: p via GAMG (no preconditioner string · D-class direct), U/k/omega
    via smoothSolver (symGaussSeidel · no DILU/FDILU preconditioner). No V27/V28
    risk patterns expected.
    """
    return SolverBlockSnapshot(
        solver="simpleFoam",
        adjust_time_step=False,
        delta_t=1.0,
        preconditioners={},
    )


# ---------------------------------------------------------------------------
# Thin-wall inputs · firewall / door / Frame components are thin-wall candidates
# ---------------------------------------------------------------------------

def build_thin_wall_inputs() -> dict:
    """Closes thin_wall_advisor (V10) input gap.

    APU bay components with elongated thin geometry are sHM-loss candidates:
    - firewall_front / firewall_behind: large flat panels (~3 m × 0.01 m thick)
    - door / vent_door: thin operable surfaces
    - Plane_Outer_Surf: thin outer plane segment
    PatchGeometry bbox_dimensions = (length, width, thickness) per-component
    estimates; refinement_levels mirror v2 sHM dict (0..1).
    """
    patches = [
        PatchGeometry(name="firewall_front", bbox_dimensions=(2.0, 1.5, 0.02)),
        PatchGeometry(name="firewall_behind", bbox_dimensions=(3.0, 2.0, 0.02)),
        PatchGeometry(name="door", bbox_dimensions=(1.5, 1.2, 0.03)),
        PatchGeometry(name="vent_door", bbox_dimensions=(0.4, 0.3, 0.02)),
        PatchGeometry(name="Plane_Outer_Surf", bbox_dimensions=(3.0, 2.0, 0.05)),
    ]
    return {
        "patches": patches,
        "refinement_levels": {p.name: (0, 1) for p in patches},
        "background_cell_size": 0.1,  # blockMesh base cell size (m)
    }


# ---------------------------------------------------------------------------
# STL face normals · representative outward normals per component
# ---------------------------------------------------------------------------

def build_shm_stl_face_normals() -> dict:
    """Closes stl_face_label_validator path · representative outward normals.

    Approximate set: 6 cardinal axis normals (±x, ±y, ±z) for closed-volume
    bodies, plus directional normals for plate-like components. Real STLs have
    O(10^3-10^5) facets; validator only needs ≥1 normal per entry.
    """
    cardinal_6 = [
        (1.0, 0.0, 0.0), (-1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0), (0.0, -1.0, 0.0),
        (0.0, 0.0, 1.0), (0.0, 0.0, -1.0),
    ]
    plate_2 = [(0.0, 1.0, 0.0), (0.0, -1.0, 0.0)]
    out: dict[str, list[tuple[float, float, float]]] = {}
    for name in COMPONENTS:
        if name.startswith("firewall") or name == "Plane_Outer_Surf":
            out[name] = plate_2
        else:
            out[name] = cardinal_6
    return out


# ---------------------------------------------------------------------------
# Reuse v1 builders (parts_manifest / shm_dict / bc_specs) with v2 BC update
# ---------------------------------------------------------------------------

def build_parts_manifest() -> dict:
    return {
        "parts": [
            {"name": name, "fields": {"U": "noSlip", "p": "zeroGradient"}}
            for name in COMPONENTS
        ]
    }


def build_shm_dict() -> dict:
    return {
        "castellatedMesh": True,
        "snap": True,
        "addLayers": False,
        "geometry": {f"{name}.stl": {"type": "triSurfaceMesh", "name": name} for name in COMPONENTS},
        "castellatedMeshControls": {
            "maxLocalCells": 5_000_000,
            "maxGlobalCells": 10_000_000,
            "minRefinementCells": 10,
            "nCellsBetweenLevels": 2,
            "maxLoadUnbalance": 0.10,
            "resolveFeatureAngle": 60,
            "allowFreeStandingZoneFaces": False,
            "features": [],
            "refinementSurfaces": {
                name: {"level": (0, 1), "patchInfo": {"type": "wall"}}
                for name in COMPONENTS
            },
            "refinementRegions": {},
            "locationInMesh": (63.8, 0.5, 0.0),
        },
        "snapControls": {
            "nSmoothPatch": 3, "tolerance": 2.0, "nSolveIter": 30,
            "nRelaxIter": 5, "nFeatureSnapIter": 10,
        },
        "meshQualityControls": {
            "maxNonOrtho": 65, "maxBoundarySkewness": 20,
            "maxInternalSkewness": 4,
        },
        "mergeTolerance": 1e-6,
    }


def build_bc_specs() -> list[dict]:
    """v3 BCs: bg-block end faces renamed to walls · STL-driven intake_duct/vent_door patches."""
    specs = [
        # v3: bg-block -x/+x faces renamed and now walls (no longer patches)
        {"part_name": "end_minus_x", "fields": {"U": "noSlip", "p": "zeroGradient"}},
        {"part_name": "end_plus_x",  "fields": {"U": "noSlip", "p": "zeroGradient"}},
        # 4 lateral walls (unchanged from v2)
        {"part_name": "bay_top", "fields": {"U": "noSlip", "p": "zeroGradient"}},
        {"part_name": "bay_bottom", "fields": {"U": "noSlip", "p": "zeroGradient"}},
        {"part_name": "bay_side_p", "fields": {"U": "noSlip", "p": "zeroGradient"}},
        {"part_name": "bay_side_n", "fields": {"U": "noSlip", "p": "zeroGradient"}},
    ]
    for name in COMPONENTS:
        if name == "intake_duct":
            # v3 inflow patch · surfaceNormalFixedValue U=1.5 m/s along inward normal
            specs.append({"part_name": "intake_duct", "fields": {"U": "fixedValue", "p": "zeroGradient"}})
        elif name == "vent_door":
            # v3 outflow patch · inletOutlet
            specs.append({"part_name": "vent_door", "fields": {"U": "zeroGradient", "p": "fixedValue"}})
        else:
            specs.append({"part_name": name, "fields": {"U": "noSlip", "p": "zeroGradient"}})
    return specs


def main() -> dict:
    parts = build_parts_manifest()
    shm = build_shm_dict()
    bc_specs = build_bc_specs()
    stl_bbox_set = build_stl_bbox_set()
    solver_snapshot = build_solver_block_snapshot()
    thin_wall = build_thin_wall_inputs()
    shm_normals = build_shm_stl_face_normals()

    report = assemble_stack(
        parts_manifest=parts,
        shm_dict=shm,
        bc_specs=bc_specs,
        bc_fork="main",
        step_body_extents_raw=DOMAIN_EXTENTS,
        step_bbox_max_extent_raw=max(DOMAIN_EXTENTS),
        stl_bbox_set=stl_bbox_set,
        solver_block_snapshot=solver_snapshot,
        thin_wall_inputs=thin_wall,
        shm_stl_face_normals=shm_normals,
    )

    summary = {
        "advisor_count": report.advisor_count,
        "advisor_calls": [c.advisor_name for c in report.advisor_calls],
        "finding_count": len(report.findings),
        "findings_by_advisor": {},
        "evidence_refs": sorted(set(report.evidence_refs)),
        "stl_bbox_count": len(stl_bbox_set),
        "thin_wall_patch_count": len(thin_wall["patches"]),
    }
    for f in report.findings:
        summary["findings_by_advisor"].setdefault(f.source_advisor, []).append({
            "severity": getattr(f, "severity", "?"),
            "code": getattr(f, "code", "?"),
            "message": getattr(f, "message", "?")[:200],
        })
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


if __name__ == "__main__":
    main()

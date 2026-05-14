"""B50 · V63-A M-VAL-REPORT-3 · case_016 m219 cavity DES acoustic prep driver.

Path B (direct ``assemble_stack``) + Path A (FastAPI ``TestClient``
``POST /api/ai-review``) on the case_016 substrate (currently
inputs-thin: only ``cad_codex_v1.step`` + ``cad_codex_v1.source.json``
on disk). The four substrate artifacts required for full advisor
dispatch — ``parts_manifest`` / ``shm_dict`` / ``thermo_dict`` /
``interface_bodies`` + ``interface_specs`` — are synthesized in
memory from on-disk OpenFOAM dicts and the snappyHexMeshDict
geometry block.

LLM-offline (Q1): pops ``ANTHROPIC_API_KEY`` / ``OPENAI_API_KEY`` /
``GOOGLE_API_KEY`` / ``DEEPSEEK_API_KEY`` before any backend import.

Emits two JSONs alongside this script:

* ``stack_report_python_extended.json`` — Path B response.
* ``stack_report_http_path_a_b50.json`` — Path A response
  (TestClient · in-process).

Mirror of B48 case_011 ``run_extended.py`` adapted to the case_016
single-region compressible-DES-acoustic numerics class.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Q1 invariant — pop LLM keys BEFORE any backend import.
_LLM_KEYS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY", "DEEPSEEK_API_KEY")
for _k in _LLM_KEYS:
    os.environ.pop(_k, None)

REPO_ROOT = Path(__file__).resolve().parents[2]
# REPO_ROOT first so `from ui.backend...` resolves; then ui/backend so
# direct `from services.advisor_stack import ...` also works (B48 precedent).
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(1, str(REPO_ROOT / "ui" / "backend"))

CASE_DIR = Path("/Users/Zhuanz/Desktop/case_016_m219_cavity_des_acoustic")
STEP_PATH = CASE_DIR / "inputs" / "cad_codex_v1.step"
OUT_DIR = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# Substrate synthesis (in-memory — case_016 has only step + source.json on disk).
# ---------------------------------------------------------------------------

# 16 geometry bodies from case/system/snappyHexMeshDict::geometry{}.
# Role tagging is by name heuristic — same convention as the V62-A
# TRACK-2 retro (2026-05-14_stack_track_c_session_2_case_016.md §3).
_BBOX_MM = {
    "inflow": [-5079.5002, -457.81223, 8.843484, -5076.1273, 457.81223, 6095.5],
    "outflow": [10156.127, -457.84227, 8.8435113, 10159.5, 457.84227, 6095.5],
}

BODY_ROLES = [
    ("flat_plate_upstream", "wall"),
    ("flat_plate_downstream", "wall"),
    ("flat_plate_side_port", "wall"),
    ("flat_plate_side_starboard", "wall"),
    ("cavity_floor", "wall"),
    ("cavity_le_wall", "wall"),
    ("cavity_te_wall", "wall"),
    ("cavity_side_wall_port", "wall"),
    ("cavity_side_wall_starboard", "wall"),
    ("debris_cube", "extra_body"),  # D6 sub-grid debris (10 mm cube · per source.json)
    ("top_far_field", "freestream"),
    ("far_field_port", "freestream"),
    ("far_field_starboard", "freestream"),
    ("inflow", "inlet"),
    ("outflow", "outlet"),
    ("fwh_porous_surface", "fwh_sampling"),  # FW-H Ffowcs-Williams-Hawkings porous surface
]

# Per case/0/ BC files (read 2026-05-15 for B50): inflow uses
# freestreamVelocity/freestreamPressure (correct far-field BC); outflow
# uses inletOutlet/zeroGradient (correct outflow). The manifest layer
# annotates V81 boundary_emission tags so A5 inlet_outlet_validator
# does NOT fire on missing-annotation by default.
def _bc_for_role(role: str) -> dict[str, str]:
    """Map role → BC field dict transcribed from case/0.orig/* (2026-05-15)."""
    if role == "inlet":
        # case/0.orig/{U,p,T,k,omega,nut,alphat} on patch `inflow`
        return {
            "U": "freestreamVelocity",
            "p": "freestreamPressure",
            "T": "freestream",
            "k": "freestream",
            "omega": "freestream",
            "nut": "calculated",
            "alphat": "calculated",
        }
    if role == "outlet":
        # case/0.orig/{U,p,T,k,omega,nut,alphat} on patch `outflow`
        return {
            "U": "pressureInletOutletVelocity",
            "p": "waveTransmissive",
            "T": "waveTransmissive",
            "k": "inletOutlet",
            "omega": "inletOutlet",
            "nut": "calculated",
            "alphat": "calculated",
        }
    if role == "freestream":
        # case/0.orig/{U,p,T,k,omega,nut,alphat} on top_far_field /
        # far_field_port / far_field_starboard
        return {
            "U": "freestreamVelocity",
            "p": "waveTransmissive",
            "T": "freestream",
            "k": "freestream",
            "omega": "freestream",
            "nut": "calculated",
            "alphat": "calculated",
        }
    if role == "wall":
        # walls use wallFunctions on k+omega+nut, noSlip on U, zeroGradient on p/T
        return {
            "U": "noSlip",
            "p": "zeroGradient",
            "T": "zeroGradient",
            "k": "kqRWallFunction",
            "omega": "omegaWallFunction",
            "nut": "nutkWallFunction",
            "alphat": "compressible::alphatWallFunction",
        }
    if role == "extra_body":
        # debris_cube: walls; differentiated only by extra_body=True
        return {
            "U": "noSlip",
            "p": "zeroGradient",
            "T": "zeroGradient",
            "k": "kqRWallFunction",
            "omega": "omegaWallFunction",
            "nut": "nutkWallFunction",
            "alphat": "compressible::alphatWallFunction",
        }
    # fwh_sampling: faceZone-based; no surface BC dispatch
    return {}


PARTS_MANIFEST = {
    "case_id": "case_016_m219_cavity_des_acoustic",
    "parts": [
        {
            "name": name,
            "role": role,
            # bbox in mm (per V81 thin_extrusion bbox spec) — checkMesh.txt
            # reports each patch's bbox in m; convert mm via × 1000.
            **(
                {
                    "bbox": _BBOX_MM[name],
                    "boundary_emission": "thin_extrusion",
                }
                if role in ("inlet", "outlet") and name in _BBOX_MM
                else (
                    {"boundary_emission": "thin_extrusion"}
                    if role in ("inlet", "outlet")
                    else {}
                )
            ),
            **(
                {"extra_body": True, "containment_role": "in_fluid"}
                if role == "extra_body"
                else {}
            ),
            **(
                {"face_labels": [name]}  # single-shell V94 canonical
                if role in ("wall", "inlet", "outlet", "extra_body")
                else {}
            ),
            **({"bc": _bc_for_role(role)} if _bc_for_role(role) else {}),
        }
        for name, role in BODY_ROLES
    ],
}


# Shm_dict transcribed from case/system/snappyHexMeshDict (real
# 16/16 refinementSurfaces — including fwh_porous_surface via
# faceZone/cellZone syntax). The V62-A TRACK-2 retro's lightweight
# regex parser dropped fwh_porous_surface because its entry uses
# faceZone+cellZone syntax instead of patchInfo {}; this synth fixes
# that fidelity gap.
_REF_LEVELS = {
    "cavity_le_wall": (4, 4),
    "cavity_te_wall": (4, 4),
    "cavity_floor": (3, 3),
    "cavity_side_wall_port": (3, 3),
    "cavity_side_wall_starboard": (3, 3),
    "debris_cube": (4, 4),
    "flat_plate_upstream": (1, 2),
    "flat_plate_downstream": (1, 2),
    "flat_plate_side_port": (1, 2),
    "flat_plate_side_starboard": (1, 2),
    "top_far_field": (0, 0),
    "far_field_port": (0, 0),
    "far_field_starboard": (0, 0),
    "inflow": (0, 0),
    "outflow": (0, 0),
    "fwh_porous_surface": (0, 0),  # faceZone-based · not a refining wall
}
SHM_DICT = {
    "geometry": {name: {"type": "triSurfaceMesh", "name": name} for name, _ in BODY_ROLES},
    "castellatedMeshControls": {
        "features": [],
        "refinementSurfaces": {
            name: {"level": list(_REF_LEVELS[name])} for name, _ in BODY_ROLES
        },
        "refinementRegions": {
            "fwh_porous_surface": {"mode": "inside", "levels": [[1e15, 3]]},
        },
        "resolveFeatureAngle": 30,
        "nCellsBetweenLevels": 2,
        "locationInMesh": [-2.5, 0.0, 1.0],
        "allowFreeStandingZoneFaces": True,
    },
    "snapControls": {"nSmoothPatch": 3, "tolerance": 2.0},
    "addLayersControls": {"addLayers": False},
}

# Thermo from constant/thermophysicalProperties — non-polynomial
# (hConst constant-Cp), so A10 should silent-skip on tlow_violation
# class entirely (correct behavior on non-polynomial pureMixture).
THERMO_DICT = {
    "thermoType": {
        "type": "hePsiThermo",
        "mixture": "pureMixture",
        "transport": "sutherland",
        "thermo": "hConst",
        "equationOfState": "perfectGas",
        "specie": "specie",
        "energy": "sensibleInternalEnergy",
    },
    "mixture": {
        "specie": {"molWeight": 28.96},
        "thermodynamics": {"Cp": 1004.5, "Hf": 0.0},
        "transport": {"As": 1.458e-06, "Ts": 110.4},
    },
}

# Interface artifacts: case_016 is SINGLE-REGION (region_air only).
# No fluid-solid CHT interface exists. Both empty per V62-A TRACK-2
# observation (correct A2-v2 silent-skip).
INTERFACE_BODIES: list[dict] = []
INTERFACE_SPECS: list[dict] = []

# Stl_bbox_set: D6 advisor consumes this with parts_manifest's
# extra_body marker for fluid-domain containment check. Bboxes are
# derived from checkMesh.txt patch bounding boxes (read 2026-05-15).
STL_BBOX_SET = {
    "debris_cube": {
        "bbox_min": [0.315, 0.013, -0.084],
        "bbox_max": [0.32499999, 0.023, -0.074],
        "max_extent_m": 0.01,
    },
    # The fluid domain reference for D6 containment is the cavity volume.
    "cavity_floor": {
        "bbox_min": [0.008, -0.0505, -0.1015],
        "bbox_max": [0.5, 0.0505, -0.0987],
        "max_extent_m": 0.492,
    },
}

# STEP body extents — per inputs/cad_codex_v1.source.json geometry_mm
# scaled by 1e-3 (mm → m). The 17-solid count comes from
# evidence/00_region_v1.json + HANDOFF note; we list the bounding-box
# longest axis per body group as A2-v2 unit_detector airframe filter.
STEP_BBOX = [-5.0795, -0.4585, -0.1015, 10.1595, 0.4585, 6.0955]  # m
STEP_EXTENTS_RAW = [15.24, 0.917, 6.197]  # m, overall box (x,y,z)


# ---------------------------------------------------------------------------
# Path B — direct assemble_stack call.
# ---------------------------------------------------------------------------

def _to_json_safe(obj):
    """Strip Finding.raw payloads to keep the report JSON-clean."""
    if isinstance(obj, dict):
        return {k: _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_json_safe(v) for v in obj]
    if hasattr(obj, "__dict__"):
        return _to_json_safe(vars(obj))
    return obj


def run_path_b():
    from services import advisor_stack

    report = advisor_stack.assemble_stack(
        parts_manifest=PARTS_MANIFEST,
        interface_bodies={},  # empty mapping → A2-v2 silent-skip
        interface_specs=tuple(),
        shm_dict=SHM_DICT,
        thermo_dict=THERMO_DICT,
        step_path=str(STEP_PATH),
        step_bbox_max_extent_raw=max(STEP_EXTENTS_RAW),
        step_body_extents_raw=STEP_EXTENTS_RAW,
        stl_bbox_set=STL_BBOX_SET,
    )

    findings = []
    for f in report.findings:
        findings.append(
            {
                "source_advisor": f.source_advisor,
                "severity": f.severity,
                "code": f.code,
                "message": f.message,
                "location": f.location,
                "evidence_v_rows": list(f.evidence_v_rows or ()),
            }
        )

    advisor_calls = []
    for c in report.advisor_calls:
        advisor_calls.append(
            {
                "advisor_name": c.advisor_name,
                "status": c.status,
                "input_summary": c.input_summary,
                "duration_ms": round(c.duration_ms, 3),
                "version": c.version,
            }
        )

    return {
        "path": "B_python_direct",
        "advisor_count": report.advisor_count,
        "advisors_dispatched": sorted({c.advisor_name for c in report.advisor_calls}),
        "finding_count": len(report.findings),
        "critical_count": report.critical_count,
        "warning_count": report.warning_count,
        "info_count": sum(1 for f in report.findings if f.severity == "info"),
        "failed_advisor_count": report.failed_advisor_count,
        "evidence_refs": sorted(report.evidence_refs),
        "env_keys_present": {k: bool(os.environ.get(k)) for k in _LLM_KEYS},
        "stack_duration_ms": round(report.stack_duration_ms, 3),
        "findings": findings,
        "advisor_calls": advisor_calls,
    }


# ---------------------------------------------------------------------------
# Path A — FastAPI TestClient POST /api/ai-review.
# ---------------------------------------------------------------------------

def run_path_a():
    from fastapi.testclient import TestClient

    from main import app

    payload = {
        "case_dir": str(CASE_DIR),
        "parts_manifest": PARTS_MANIFEST,
        "shm_dict": SHM_DICT,
        "thermo_dict": THERMO_DICT,
        "step_path": str(STEP_PATH),
        "step_bbox": STEP_BBOX,
        "step_extents": STEP_EXTENTS_RAW,
        "interface_bodies": INTERFACE_BODIES,
        "interface_specs": INTERFACE_SPECS,
        "stl_bbox_set": STL_BBOX_SET,
    }

    client = TestClient(app)
    resp = client.post("/api/ai-review", json=payload)
    body = resp.json()
    report = body.get("report") or {}
    findings = report.get("findings") or []
    info_count = sum(1 for f in findings if f.get("severity") == "info")
    return {
        "path": "A_http_testclient",
        "http_status": resp.status_code,
        "advisor_count": report.get("advisor_count"),
        "advisors_dispatched": sorted(
            {c.get("advisor_name") for c in (report.get("advisor_calls") or [])}
        ),
        "finding_count": len(findings),
        "critical_count": report.get("critical_count"),
        "warning_count": report.get("warning_count"),
        "info_count": info_count,
        "failed_advisor_count": report.get("failed_advisor_count"),
        "evidence_refs": report.get("evidence_refs"),
        "stack_duration_ms": report.get("stack_duration_ms"),
        "llm_enhanced": body.get("llm_enhanced"),
        "audit_artifact_path": body.get("audit_artifact_path"),
        "timing": body.get("timing"),
        "env_keys_present": {k: bool(os.environ.get(k)) for k in _LLM_KEYS},
        "findings": findings,
        "advisor_calls": report.get("advisor_calls"),
        "v_series_drift_guard": report.get("v_series_drift_guard"),
    }


# ---------------------------------------------------------------------------

def main():
    out_b = run_path_b()
    (OUT_DIR / "stack_report_python_extended.json").write_text(
        json.dumps(out_b, indent=2)
    )
    print("[Path B] wrote stack_report_python_extended.json")
    print(
        f"  advisors={out_b['advisor_count']} findings={out_b['finding_count']}"
        f" crit={out_b['critical_count']} warn={out_b['warning_count']}"
        f" failed={out_b['failed_advisor_count']}"
    )

    out_a = run_path_a()
    (OUT_DIR / "stack_report_http_path_a_b50.json").write_text(
        json.dumps(out_a, indent=2)
    )
    print("[Path A] wrote stack_report_http_path_a_b50.json")
    print(
        f"  http={out_a['http_status']} advisors={out_a['advisor_count']}"
        f" findings={out_a['finding_count']} crit={out_a['critical_count']}"
        f" warn={out_a['warning_count']} failed={out_a['failed_advisor_count']}"
        f" llm_enhanced={out_a['llm_enhanced']}"
    )


if __name__ == "__main__":
    main()

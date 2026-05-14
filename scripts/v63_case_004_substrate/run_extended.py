"""Path (b) extended · assemble_stack on case_004 with the 3 newly synthesized inputs.

DEC-V63-A-sub-M-CASE-004-SUBSTRATE (V63-A Tier 2 · cross-case extension #2 driving
Done dim #6 from 1 canonical case ≥3/9 to 2 canonical cases ≥3/9 · mirror of the
B42 case_006 substrate land at scripts/v63_case_006_substrate/run_extended.py).

Mirrors ``scripts/stack_track_c_case_ext_1/run_python_path.py`` (same
parts_manifest + shm_dict=None + thermo_dict=None + step_path baseline) and
adds three substrate-side input files newly landed under ``case_004/inputs/``:

  - ``thin_wall_inputs.yaml`` -> ``thin_wall_advisor`` dispatch (V10)
  - ``interface_bodies.json`` + ``interface_specs.json`` -> A2-v2
    ``virtual_interface_detector`` dispatch (V22/V25/V33/V36/V42/V43/V50)

Goal: push V-row truth-capture rate from 1/9 (V29 only) to >=3/9 (add V30
thin_wall sliver via yaw_sensor_shim 0.75 mm + D1 sub-mm gap via
nacelle_body↔nacelle_service_cover 0.30 mm).

Run from repo root::

    .venv/bin/python -m scripts.v63_case_004_substrate.run_extended
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# 4Q gate Q1: drop LLM keys BEFORE any backend import.
for _k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY", "DEEPSEEK_API_KEY"):
    os.environ.pop(_k, None)

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import yaml  # noqa: E402

from scripts.stack_track_c_case_ext_1.build_inputs import (  # noqa: E402
    CASE_DIR,
    build_parts_manifest,
    build_shm_dict,
    build_thermo_dict,
    step_path,
)
from ui.backend.services.advisor_stack import assemble_stack  # noqa: E402
from ui.backend.services.geometry_ingest import (  # noqa: E402
    thin_wall_advisor,
    virtual_interface_detector,
)

INPUTS = CASE_DIR / "inputs"


def load_thin_wall_inputs() -> dict:
    """Load case_004/inputs/thin_wall_inputs.yaml and rebuild PatchGeometry tuples."""
    raw = yaml.safe_load((INPUTS / "thin_wall_inputs.yaml").read_text())
    patches = tuple(
        thin_wall_advisor.PatchGeometry(
            name=p["name"],
            bbox_dimensions=tuple(p["bbox_dimensions"]),
        )
        for p in raw["patches"]
    )
    refinement_levels = {
        name: tuple(levels) for name, levels in raw["refinement_levels"].items()
    }
    return {
        "patches": patches,
        "refinement_levels": refinement_levels,
        "background_cell_size": float(raw["background_cell_size"]),
        "min_cells_per_thickness": int(raw.get("min_cells_per_thickness", 2)),
    }


def load_interface_bodies() -> dict[str, virtual_interface_detector.BodyGeometry]:
    """Load case_004/inputs/interface_bodies.json and rebuild BodyGeometry dataclasses."""
    raw = json.loads((INPUTS / "interface_bodies.json").read_text())
    out: dict[str, virtual_interface_detector.BodyGeometry] = {}
    for key, body in raw.items():
        if key.startswith("_"):
            continue
        faces = tuple(
            virtual_interface_detector.FaceGeometry(
                area=float(f["area"]),
                bbox_min=tuple(f["bbox_min"]),
                bbox_max=tuple(f["bbox_max"]),
                normal=tuple(f["normal"]),
                centroid=tuple(f["centroid"]),
            )
            for f in body["faces"]
        )
        out[key] = virtual_interface_detector.BodyGeometry(
            name=body["name"],
            faces=faces,
            centroid=tuple(body["centroid"]),
        )
    return out


def load_interface_specs() -> tuple[virtual_interface_detector.InterfaceSpec, ...]:
    """Load case_004/inputs/interface_specs.json -> InterfaceSpec tuple."""
    raw = json.loads((INPUTS / "interface_specs.json").read_text())
    return tuple(
        virtual_interface_detector.InterfaceSpec(
            patch_name=s["patch_name"],
            mode=s["mode"],
            body_a=s.get("body_a"),
            body_b=s.get("body_b"),
            body=s.get("body"),
            axis=s.get("axis"),
        )
        for s in raw["specs"]
    )


def main() -> dict:
    parts = build_parts_manifest()
    shm = build_shm_dict()
    thermo = build_thermo_dict()
    step = step_path()

    interface_bodies = load_interface_bodies()
    interface_specs = load_interface_specs()
    thin_wall_inputs = load_thin_wall_inputs()

    report = assemble_stack(
        parts_manifest=parts,
        shm_dict=shm,
        thermo_dict=thermo,
        step_path=step,
        interface_bodies=interface_bodies,
        interface_specs=interface_specs,
        thin_wall_inputs=thin_wall_inputs,
    )

    out = {
        "advisor_count": report.advisor_count,
        "finding_count": len(report.findings),
        "critical_count": report.critical_count,
        "warning_count": report.warning_count,
        "failed_advisor_count": report.failed_advisor_count,
        "advisors_dispatched": sorted({c.advisor_name for c in report.advisor_calls}),
        "evidence_refs": sorted(report.evidence_refs),
        "findings": [
            {
                "code": f.code,
                "severity": f.severity,
                "source_advisor": f.source_advisor,
                "evidence_v_rows": list(f.evidence_v_rows),
                "message": f.message,
                "location": f.location,
            }
            for f in report.findings
        ],
        "advisor_calls": [
            {
                "advisor_name": c.advisor_name,
                "status": c.status,
                "duration_ms": c.duration_ms,
                "input_summary": c.input_summary,
                "version": c.version,
                "output_summary": (
                    c.output
                    if isinstance(c.output, dict)
                    else type(c.output).__name__
                ),
            }
            for c in report.advisor_calls
        ],
        "env_keys_present": {
            k: bool(os.environ.get(k))
            for k in (
                "ANTHROPIC_API_KEY",
                "OPENAI_API_KEY",
                "GOOGLE_API_KEY",
                "DEEPSEEK_API_KEY",
            )
        },
    }

    out_path = Path(__file__).parent / "stack_report_python_extended.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))
    return out


if __name__ == "__main__":
    out = main()
    print(
        json.dumps(
            {
                "advisor_count": out["advisor_count"],
                "finding_count": out["finding_count"],
                "critical_count": out["critical_count"],
                "warning_count": out["warning_count"],
                "failed_advisor_count": out["failed_advisor_count"],
                "advisors_dispatched": out["advisors_dispatched"],
                "evidence_refs": out["evidence_refs"],
                "env_keys_present": out["env_keys_present"],
            },
            indent=2,
        )
    )

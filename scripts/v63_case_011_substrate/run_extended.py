"""Path (b) extended · assemble_stack on case_011 v5b with the 3 newly synthesized substrate inputs + D11 V94 face-label dispatch wiring.

DEC-V63-A-sub-M-CASE-011-SUBSTRATE (V63-A Tier 2 · cross-case extension #3
driving Done dim #6 from 2 canonical cases ≥3/9 to 3 canonical cases ≥3/9 ·
mirror of B42 case_006 + B45 case_004 substrate lands).

Mirrors ``scripts/stack_track_c_session_1/build_inputs.py`` (same shm_dict +
step_path baseline · case_011 v5b live) and adds three substrate-side
input files newly landed under ``case_011_plate_fin_compact_hx/inputs/``:

  - ``thin_wall_inputs.yaml``   -> ``thin_wall_advisor`` dispatch (V10/V30)
  - ``interface_bodies.json``   ─┐
  - ``interface_specs.json``    ─┴-> A2-v2 ``virtual_interface_detector`` dispatch
                                     (V22/V25/V33/V36/V42/V43/V50) + D5 30 um classifier

Additionally — case_011 is the **canonical V94 face-label-loss case** per
``DEC-V63-A-sub-D11``. We extend ``parts_manifest`` with ``face_labels`` (6
labels across hot/cold regions) + supply a 3-region ``shm_stl_face_normals``
dict so the D11 ``stl_face_label_validator`` dispatches and emits the
documented 6-orphan replay (V94).

Goal: push V-row truth-capture rate from 2/9 (V10 + V20+V96, post
TRACK-1-rerun) to ≥3/9 by adding V22 (A2-v2 plate-plate adjacency) + V30
(thin_wall sliver class with multi-patch) + V94 (D11 face-label) + D5
(A2-v2 unintended_gap classifier on separator_3_4 30 um). Target: 6/9 firm.

Run from repo root::

    .venv/bin/python -m scripts.v63_case_011_substrate.run_extended

LLM-offline check (Q1): this script imports ONLY from advisor_stack +
geometry_ingest. No anthropic/openai/corpus_loader.
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

from scripts.stack_track_c_session_1.build_inputs import (  # noqa: E402
    CASE_DIR,
    build_parts_manifest,
    build_shm_dict,
    build_step_payload,
)
from ui.backend.services.advisor_stack import assemble_stack  # noqa: E402
from ui.backend.services.geometry_ingest import (  # noqa: E402
    thin_wall_advisor,
    virtual_interface_detector,
)

INPUTS = CASE_DIR / "inputs"


def load_thin_wall_inputs() -> dict:
    """Load case_011/inputs/thin_wall_inputs.yaml and rebuild PatchGeometry tuples."""
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
    """Load case_011/inputs/interface_bodies.json -> BodyGeometry dataclasses."""
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
    """Load case_011/inputs/interface_specs.json -> InterfaceSpec tuple."""
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


def build_parts_manifest_with_face_labels() -> dict:
    """Overlay face_labels onto the TRACK-1 parts_manifest baseline.

    case_011 v1 sediment surfaced V94 — cq.exporters single-shell STL
    emitted only the parent body label per region (region_hot_fluid /
    region_cold_fluid / region_solid), while the engineer's case profile
    expected six named sub-face labels (hot_inlet/outlet/walls +
    cold_inlet/outlet/walls). D11 stl_face_label_validator orphan-fires
    once per declared-but-missing label.

    Mirrors the case_011 V94 regression test in
    ``ui/backend/tests/test_stl_face_label_validator.py`` (test #11)
    verbatim — same 6 labels, same 3 STL parent-body inventory.
    """
    base = build_parts_manifest()
    # Overlay face_labels on the two fluid regions (V94 canonical replay)
    for part in base["parts"]:
        if part["name"] == "region_hot_fluid":
            part["face_labels"] = ["hot_inlet", "hot_outlet", "hot_walls"]
        elif part["name"] == "region_cold_fluid":
            part["face_labels"] = ["cold_inlet", "cold_outlet", "cold_walls"]
        # region_solid intentionally omitted — boundary of conduction box,
        # no inlet/outlet face_labels authored by engineer
    return base


def build_stl_face_normals() -> dict:
    """3-region single-shell STL inventory (V94 canonical case_011 v1).

    cq.exporters single-watertight-shell behaviour: only the parent
    region body labels appear in the emitted STL. Normals chosen to
    differ across the three regions (so the dict's three keys are
    distinct) — actual normal direction is not load-bearing for D11
    path (a); only presence-or-absence of the parent label is.
    """
    return {
        "region_hot_fluid": [(0.0, 1.0, 0.0)],
        "region_cold_fluid": [(0.0, -1.0, 0.0)],
        "region_solid": [(0.0, 0.0, 1.0)],
    }


def main() -> dict:
    parts = build_parts_manifest_with_face_labels()
    shm = build_shm_dict()
    step_payload = build_step_payload()

    interface_bodies = load_interface_bodies()
    interface_specs = load_interface_specs()
    thin_wall_inputs = load_thin_wall_inputs()
    stl_face_normals = build_stl_face_normals()

    report = assemble_stack(
        parts_manifest=parts,
        shm_dict=shm,
        step_path=Path(step_payload["step_path"]),
        step_bbox_max_extent_raw=step_payload["step_bbox_max_extent_raw"],
        interface_bodies=interface_bodies,
        interface_specs=interface_specs,
        thin_wall_inputs=thin_wall_inputs,
        shm_stl_face_normals=stl_face_normals,
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
    summary = {
        "advisor_count": out["advisor_count"],
        "finding_count": out["finding_count"],
        "critical_count": out["critical_count"],
        "warning_count": out["warning_count"],
        "failed_advisor_count": out["failed_advisor_count"],
        "advisors_dispatched": out["advisors_dispatched"],
        "evidence_refs": out["evidence_refs"],
        "env_keys_present": out["env_keys_present"],
    }
    print(json.dumps(summary, indent=2, default=str))
    print()
    print("=== findings ===")
    for i, f in enumerate(out["findings"], 1):
        print(f"[{i}] [{f['severity'].upper()}] advisor={f['source_advisor']} code={f['code']}")
        print(f"     v_rows={f['evidence_v_rows']}")
        print(f"     loc={f['location']}")
        print(f"     msg={(f['message'] or '')[:200]}")

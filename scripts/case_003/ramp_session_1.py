"""case_003 ramp · session 1 driver.

Substrate-listening test: drive case_003 CRM-HLS through main-project
preprocessing primitives (A1 cad_ingest + P0 unit_detector), via FreeCAD
subprocess bridge. Reports what worked, what's the next blocker, where
the workbench (route/service layer) breaks down.

Run from repo root:
    .venv/bin/python scripts/case_003/ramp_session_1.py

Writes:
    ui/backend/user_drafts/imported/case_003_crm_hls/probe_session_1.json
    .planning/case_profiles/case_003_ramp_log_2026-05-11.md (appended)
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# Ensure main-project services importable when run from repo root.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from ui.backend.services.geometry_ingest.unit_detector import (
    GeometricUnit,
    detect_unit,
)


FREECAD_CMD = "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd"
CASE_DIR = REPO_ROOT / "ui/backend/user_drafts/imported/case_003_crm_hls"
STEP_PATH = CASE_DIR / "raw/cad.step"
PROBE_OUT = CASE_DIR / "probe_session_1.json"
PROBE_SCRIPT = REPO_ROOT / "scripts/case_003/_freecad_probe.py"


def main() -> int:
    print(f"=== case_003 ramp · session 1 ===")
    print(f"repo root : {REPO_ROOT}")
    print(f"step file : {STEP_PATH}")
    print(f"size      : {STEP_PATH.stat().st_size / 1e6:.2f} MB")
    print()

    # 1. P0 STEP header parse (no FreeCAD needed)
    print("[1] P0 · parse STEP header for declared unit")
    from ui.backend.services.geometry_ingest.unit_detector import (
        parse_step_header_unit,
    )
    declared, header_evidence = parse_step_header_unit(STEP_PATH)
    print(f"    declared unit : {declared}")
    for line in header_evidence:
        print(f"    evidence     : {line}")
    print()

    # 2. A1 + bbox via FreeCAD subprocess (needs system FreeCAD)
    print("[2] A1 + bbox · subprocess freecadcmd probe")
    if not Path(FREECAD_CMD).exists():
        print(f"    SKIP — freecadcmd not at expected path {FREECAD_CMD}")
        return 2
    # freecadcmd parses positionals after the script as "files to open" and
    # logs errors but still runs the script body. We pre-write paths to a
    # sidecar args file the probe reads.
    args_file = CASE_DIR / "_probe_args.txt"
    args_file.write_text(f"{STEP_PATH}\n{PROBE_OUT}\n")
    if PROBE_OUT.exists():
        PROBE_OUT.unlink()
    result = subprocess.run(
        [FREECAD_CMD, str(PROBE_SCRIPT)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    if not PROBE_OUT.exists():
        print(f"    FAIL — probe JSON not produced (exit {result.returncode})")
        print(f"    stderr tail: {result.stderr[-500:]}")
        return 3
    probe = json.loads(PROBE_OUT.read_text())
    print(f"    bodies loaded : {probe['n_solids']}")
    print(f"    bbox max extent (raw): {probe['bbox_max_extent_raw']:.4g}")
    print(f"    labels:")
    for s in probe["solids"][:10]:
        print(f"      {s['label']:40s}  ({s['n_solids']}sld/{s['n_faces']}fc)")
    if len(probe["solids"]) > 10:
        print(f"      ... ({len(probe['solids']) - 10} more)")
    print()

    # 3. P0 combined decision
    print("[3] P0 · combined unit decision (header + bbox)")
    detection = detect_unit(
        step_path=STEP_PATH,
        bbox_max_extent_raw=probe["bbox_max_extent_raw"],
    )
    print(f"    declared : {detection.declared_unit}")
    print(f"    bbox plausible : {[u.value for u in detection.bbox_plausible_units]}")
    print(f"    decision : {detection.decision}")
    print(f"    confidence : {detection.confidence}")
    print(f"    evidence:")
    for line in detection.evidence:
        print(f"      - {line}")
    print()

    # 4. Predict next blocker
    print("[4] Predicted next blocker")
    if detection.decision == GeometricUnit.UNKNOWN:
        print("    UNIT — engineer must confirm before any downstream step")
    elif detection.decision == GeometricUnit.INCH and detection.declared_unit != GeometricUnit.INCH:
        print(
            "    UNIT_SCALE_MISMATCH — geometry interpreted as inches despite header "
            "claiming otherwise (V20 case_003 archetype)"
        )
    else:
        # Unit clear; next blocker = STEP→STL conversion + workbench import
        print(
            "    STEP_TO_STL — workbench import endpoint accepts STL only (M5.0); "
            "need FreeCAD-subprocess Mesh export step before route can ingest. "
            "Plus: 91 m airframe at MM means we need to verify HLPW6 source unit "
            "(real CRM-HLS half-span ≈ 30 m, so 91 m at MM = 0.091 m is way too small "
            "— most likely the STEP was authored in inches OR has a per-body unit "
            "conversion lost in cadquery / FreeCAD chain)."
        )
    print()

    print(f"[done] probe JSON: {PROBE_OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

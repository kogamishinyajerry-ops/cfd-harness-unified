"""DEC-V61-202-SUB-M30-CYCLE6 · provenance audit_v2 log dogfood.

Stages a case, makes several decide() calls (via the GET frame route)
with different (step, focus_patch) combos, and asserts:
    1. The decisions.jsonl log file exists at the documented path
    2. Each frame call produced exactly one log line
    3. Lines parse as valid JSON with the documented schema
    4. focus_patch is captured per-line (set / null faithfully recorded)
    5. The state_sha + manifest_state_sha on the log match the frame
    6. replay_decisions.py reader reads back what the writer wrote
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import yaml
from fastapi.testclient import TestClient


CASE_ID = "case_007_cycle6_provenance"

MANIFEST = {
    "case_id": CASE_ID,
    "case_family": "ship_vof",
    "solver_backend": "openfoam",
    "physics": {
        "solver": "interFoam",
        "turbulence_model": "kOmegaSST",
    },
    "bc": {
        "patches": {
            "inlet": {
                "patch_type": "fixedValue",
                "fields": {"U": [1.0, 0.0, 0.0]},
            },
            "outlet": {
                "patch_type": "zeroGradient",
                "fields": {"p": "zeroGradient"},
            },
            "wall": {"patch_type": "noSlip", "fields": {}},
        }
    },
}

ARTIFACTS = {
    "mesh_report.json": {
        "gate_status": "PASS",
        "stats": {"cells": 1_240_000},
        "quality_dimension": {"dimension_status": "PASS"},
    },
    "bc_audit.json": {
        "gate_status": "WARN",
        "patch_coverage_dimension": {
            "dimension_status": "WARN",
            "gaps_by_field": {"U": ["inlet"]},
        },
    },
}


def main():
    # Stage in tmp.
    tmpdir = Path(tempfile.mkdtemp(prefix="cycle6_provenance_"))
    imported_root = tmpdir / "imported"
    imported_root.mkdir()
    case_dir = imported_root / CASE_ID
    case_dir.mkdir()
    (case_dir / "case_manifest.yaml").write_text(yaml.safe_dump(MANIFEST))
    art_dir = case_dir / "artifacts"
    art_dir.mkdir()
    for name, payload in ARTIFACTS.items():
        (art_dir / name).write_text(json.dumps(payload))

    audit_root = tmpdir / "audit_v2"
    audit_root.mkdir()

    # Re-enable provenance for the dogfood and point it at tmp.
    os.environ.pop("WORKBENCH_PROVENANCE_DISABLED", None)
    import ui.backend.routes.workbench_frame as wf
    import ui.backend.services.case_completeness.analyzer as cc_analyzer
    import ui.backend.services.manifest_patch as mp
    import ui.backend.services.workbench_decide_provenance as wp

    wf.IMPORTED_DIR = imported_root
    cc_analyzer.IMPORTED_DIR = imported_root
    mp.IMPORTED_DIR = imported_root
    wp.AUDIT_V2_DIR = audit_root

    from ui.backend.main import app
    client = TestClient(app)

    # Make 5 calls with varying step / focus_patch.
    calls = [
        ("step=1", None),
        ("step=4", None),
        ("step=4", "inlet"),
        ("step=4", "outlet"),
        ("step=5", None),
    ]
    frames = []
    for step_qs, focus in calls:
        url = f"/api/cases/{CASE_ID}/workbench_frame?{step_qs}"
        if focus:
            url += f"&focus_patch={focus}"
        r = client.get(url)
        assert r.status_code == 200, f"GET {url} failed: {r.text}"
        frames.append(r.json())

    log_path = audit_root / CASE_ID / "decisions.jsonl"

    # ── Checks ────────────────────────────────────────────────────────
    print("\n=== Cycle 6 provenance dogfood ===\n")

    log_exists = log_path.exists()
    lines = []
    if log_exists:
        for raw in log_path.read_text().splitlines():
            if raw.strip():
                lines.append(json.loads(raw))

    sha_matches = (
        len(lines) == len(frames)
        and all(
            lines[i]["state_sha"] == frames[i]["state_sha"]
            and lines[i]["manifest_state_sha"] == frames[i]["manifest_state_sha"]
            for i in range(len(lines))
        )
    )

    focus_recorded = (
        len(lines) >= 5
        and lines[0]["focus_patch"] is None
        and lines[2]["focus_patch"] == "inlet"
        and lines[3]["focus_patch"] == "outlet"
    )

    all_json_valid = True
    for raw in log_path.read_text().splitlines() if log_exists else []:
        if raw.strip():
            try:
                json.loads(raw)
            except json.JSONDecodeError:
                all_json_valid = False

    # Reader smoke check.
    reader_path = Path("scripts/audit_v2/replay_decisions.py").resolve()
    reader_works = False
    try:
        import subprocess
        env = dict(os.environ)
        env["PYTHONPATH"] = "."
        result = subprocess.run(
            [
                sys.executable,
                str(reader_path),
                CASE_ID,
                "--audit-dir", str(audit_root),
                "--limit", "3",
            ],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
        reader_works = result.returncode == 0 and "TIMESTAMP" in result.stdout
    except Exception:
        pass

    checks = [
        ("Log file created at expected path",
         log_exists),
        (f"Log has exactly {len(calls)} lines (one per frame call)",
         len(lines) == len(calls)),
        ("All log lines parse as valid JSON",
         all_json_valid),
        ("state_sha + manifest_state_sha on lines match frames",
         sha_matches),
        ("focus_patch captured per-line (set / null faithful)",
         focus_recorded),
        ("Schema fields present (rail_primary.kind / topbar_cta.kind / bottom_card_count)",
         all(
            "rail_primary" in line and "kind" in line["rail_primary"]
            and "topbar_cta" in line and "kind" in line["topbar_cta"]
            and "bottom_card_count" in line
            for line in lines
         )),
        ("replay_decisions.py reads the log and prints a header",
         reader_works),
    ]

    all_pass = True
    for label, ok in checks:
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print(f"  [{status}] {label}")

    print()
    print(f"Verdict: {'PASS' if all_pass else 'FAIL'}")

    # Cleanup the tmpdir on success.
    if all_pass:
        shutil.rmtree(tmpdir, ignore_errors=True)

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()

"""DEC-V61-202 M3.3 cycle 1 · stage demo case for real-user UX validation.

Stages a deterministic case under
`ui/backend/user_drafts/imported/m33_ux_demo_seed/` so a real engineer
can navigate to /workbench/case/m33_ux_demo_seed?step=geometry and
exercise M3.2 cycles 1-5 (severity rail + 3 copy affordances + toast)
with their own hands, not Playwright.

Closes the gap from M3.2 retro §"What went poorly" #4 (no real-user UX
validation). Idempotent — re-run safely (overwrites).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

CASE_ID = "m33_ux_demo_seed"
REPO_ROOT = Path(__file__).resolve().parents[2]
IMPORTED_DIR = REPO_ROOT / "ui" / "backend" / "user_drafts" / "imported"
CASE_DIR = IMPORTED_DIR / CASE_ID

# Manifest with NO case_family so step-1 (geometry) surfaces an
# info_gap rail with severity=warn, field_path=case_family, and body_text
# (analyzer-emitted gap.why). This is the same shape m32-dogfood.spec.ts
# uses; the cycle-6 dogfood proved body_text renders for this seed.
MANIFEST_YAML = f"""case_id: {CASE_ID}
solver_backend: openfoam
physics:
  solver: simpleFoam
  turbulence_model: kOmegaSST
bc:
  patches:
    inlet:
      patch_type: fixedValue
      fields:
        U: [1.0, 0.0, 0.0]
    outlet:
      patch_type: zeroGradient
      fields:
        p: zeroGradient
    wall:
      patch_type: noSlip
      fields: {{}}
"""

BC_AUDIT = {
    "gate_status": "WARN",
    "patch_coverage_dimension": {
        "dimension_status": "WARN",
        "gaps_by_field": {"U": ["inlet"]},
    },
}

MESH_REPORT = {
    "gate_status": "PASS",
    "stats": {"cells": 500_000},
    "quality_dimension": {"dimension_status": "PASS"},
}


def main() -> int:
    CASE_DIR.mkdir(parents=True, exist_ok=True)
    (CASE_DIR / "case_manifest.yaml").write_text(MANIFEST_YAML)
    artifacts = CASE_DIR / "artifacts"
    artifacts.mkdir(exist_ok=True)
    (artifacts / "bc_audit.json").write_text(json.dumps(BC_AUDIT, indent=2))
    (artifacts / "mesh_report.json").write_text(json.dumps(MESH_REPORT, indent=2))

    print(f"staged · case_dir={CASE_DIR}")
    print(f"open · http://localhost:5173/workbench/case/{CASE_ID}?step=geometry")
    return 0


if __name__ == "__main__":
    sys.exit(main())

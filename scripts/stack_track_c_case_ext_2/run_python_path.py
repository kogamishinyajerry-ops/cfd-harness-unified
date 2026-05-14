"""Path (b) · direct ``assemble_stack(...)`` against case_009 v1 inputs.

V63-A Tier 2 sub-DEC M-CASE-EXT-2 · 5th distinct numerics class Track C session.

Run from repo root:
    .venv/bin/python -m scripts.stack_track_c_case_ext_2.run_python_path
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

# 4Q gate Q1: drop LLM keys BEFORE any backend import.
for _k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY", "DEEPSEEK_API_KEY"):
    os.environ.pop(_k, None)

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.stack_track_c_case_ext_2.build_inputs import (  # noqa: E402
    build_parts_manifest,
    build_shm_dict,
    build_thermo_dict,
    step_path,
)
from ui.backend.services.advisor_stack import assemble_stack  # noqa: E402


def main() -> dict:
    parts = build_parts_manifest()
    shm = build_shm_dict()
    thermo = build_thermo_dict()
    step = step_path()

    report = assemble_stack(
        parts_manifest=parts,
        shm_dict=shm,
        thermo_dict=thermo,
        step_path=step,
    )

    advisors_dispatched = sorted({c.advisor_name for c in report.advisor_calls})
    out = {
        "advisor_count": report.advisor_count,
        "finding_count": len(report.findings),
        "critical_count": report.critical_count,
        "warning_count": report.warning_count,
        "failed_advisor_count": report.failed_advisor_count,
        "advisors_dispatched": advisors_dispatched,
        "advisor_calls": [
            {
                "advisor_name": c.advisor_name,
                "status": c.status,
                "input_summary": c.input_summary,
                "duration_ms": c.duration_ms,
                "version": c.version,
            }
            for c in report.advisor_calls
        ],
        "evidence_refs": sorted(report.evidence_refs),
        "findings": [asdict(f) for f in report.findings],
        "env_keys_present": {
            k: bool(os.environ.get(k))
            for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY", "DEEPSEEK_API_KEY")
        },
    }

    out_path = Path(__file__).parent / "stack_report_python.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps({k: v for k, v in out.items() if k != "findings"}, indent=2, default=str))
    print(f"\n[python-path] wrote {out_path}")
    print(f"[python-path] {len(out['findings'])} findings detail in JSON file")
    return out


if __name__ == "__main__":
    main()

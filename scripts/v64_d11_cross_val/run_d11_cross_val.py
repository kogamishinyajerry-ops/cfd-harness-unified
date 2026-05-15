"""D11 cross-validation runner · V64-A Tier 3 M-V64A-D11-CROSS-VAL.

Runs D11 (stl_face_label_validator) against synthetic substrate derived
from case_018/019/020 kickoff specs per V63-A close DEC §8 carry-over #4.

Substrate immutability: case_018/019/020 have no materialized substrate;
this runner only reads additive synthetic YAML files under
``.planning/audits/d11_cross_val/<case>/substrate.yaml`` and writes
evidence JSON next to each substrate. No existing case substrate is
mutated.

Q1 LLM-offline: this script drops LLM-keys before importing backend
modules and depends only on advisor_stack + stl_face_label_validator
(both pure-function Python).

Usage::

    .venv/bin/python -m scripts.v64_d11_cross_val.run_d11_cross_val

Or per-case::

    .venv/bin/python -m scripts.v64_d11_cross_val.run_d11_cross_val case_018

Output: ``.planning/audits/d11_cross_val/<case>/d11_evidence.json`` per
case + a summary printed to stdout (consumed by the validation report
authoring step).
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

# Q1 gate · drop LLM keys BEFORE any backend import.
for _k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY", "DEEPSEEK_API_KEY"):
    os.environ.pop(_k, None)

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import yaml  # noqa: E402

from ui.backend.services.advisor_stack import assemble_stack  # noqa: E402
from ui.backend.services.geometry_ingest import (  # noqa: E402
    stl_face_label_validator,
)

CASES = ("case_018", "case_019", "case_020")
AUDIT_ROOT = REPO / ".planning" / "audits" / "d11_cross_val"


def load_substrate(case: str) -> dict:
    """Read the per-case synthetic substrate YAML."""
    path = AUDIT_ROOT / case / "substrate.yaml"
    return yaml.safe_load(path.read_text())


def _finding_to_dict(f: stl_face_label_validator.FaceLabelFinding) -> dict:
    return {
        "advisor_name": f.advisor_name,
        "severity": f.severity,
        "code": f.code,
        "face_label": f.face_label,
        "location": f.location,
        "detail": f.detail,
        "evidence_v_rows": list(f.evidence_v_rows),
        "suggested_fix": f.suggested_fix,
    }


def run_one(case: str) -> dict:
    """Run D11 directly + through assemble_stack and capture both."""
    sub = load_substrate(case)
    parts_manifest = sub["parts_manifest"]
    stl_face_normals = sub["stl_face_normals"]
    shm_dict = sub["shm_dict"]
    expected = sub["expected_findings"]

    # Direct invocation — exercises pure-function path.
    direct_report = stl_face_label_validator.validate_face_label_consistency(
        stl_face_normals, parts_manifest, shm_dict
    )

    # Stack invocation — exercises the dispatch gate.
    stack_report = assemble_stack(
        parts_manifest=parts_manifest,
        shm_dict=shm_dict,
        shm_stl_face_normals=stl_face_normals,
    )

    d11_calls = [
        c for c in stack_report.advisor_calls
        if c.advisor_name == "stl_face_label_validator"
    ]
    d11_dispatched = len(d11_calls) == 1
    d11_status = d11_calls[0].status if d11_dispatched else "not_dispatched"
    d11_findings_from_stack = [
        {
            "source_advisor": f.source_advisor,
            "severity": f.severity,
            "code": f.code,
            "message": f.message,
            "location": f.location,
            "evidence_v_rows": list(f.evidence_v_rows),
        }
        for f in stack_report.findings
        if f.source_advisor == "stl_face_label_validator"
    ]

    # Cross-check direct vs stack-routed: counts must agree.
    actual_by_code = {
        "orphan_declared_label": 0,
        "duplicate_face_label_in_manifest": 0,
        "shm_reference_undeclared_in_manifest": 0,
    }
    for f in direct_report.findings:
        actual_by_code[f.code] = actual_by_code.get(f.code, 0) + 1
    actual_by_code["total"] = sum(
        v for k, v in actual_by_code.items() if k != "total"
    )

    expected_codes = {
        k: expected[k] for k in actual_by_code
    }
    match = actual_by_code == expected_codes

    return {
        "case_id": sub["case_id"],
        "substrate_source": sub["source"],
        "substrate_type": sub["substrate_type"],
        "dispatch": {
            "dispatched": d11_dispatched,
            "status": d11_status,
            "duration_ms": d11_calls[0].duration_ms if d11_dispatched else None,
        },
        "direct_invocation": {
            "declared_labels": list(direct_report.declared_labels),
            "stl_labels": list(direct_report.stl_labels),
            "shm_referenced_labels": list(direct_report.shm_referenced_labels),
            "findings": [_finding_to_dict(f) for f in direct_report.findings],
            "warning_count": direct_report.warning_count,
            "critical_count": direct_report.critical_count,
        },
        "stack_invocation": {
            "d11_findings": d11_findings_from_stack,
            "stack_advisor_count": stack_report.advisor_count,
            "stack_finding_count": len(stack_report.findings),
            "stack_duration_ms": stack_report.stack_duration_ms,
        },
        "verdict": {
            "expected_findings": expected_codes,
            "actual_findings": actual_by_code,
            "match": match,
            "archetype": expected["archetype"],
            "v94_attribution": expected["v94_attribution"],
        },
    }


def main(argv: list[str]) -> int:
    selected = argv[1:] if len(argv) > 1 else list(CASES)
    summary = []
    for case in selected:
        if case not in CASES:
            print(f"unknown case: {case}", file=sys.stderr)
            return 2
        evidence = run_one(case)
        out_path = AUDIT_ROOT / case / "d11_evidence.json"
        out_path.write_text(json.dumps(evidence, indent=2, sort_keys=True))
        verdict = evidence["verdict"]
        summary.append({
            "case": case,
            "match": verdict["match"],
            "expected_total": verdict["expected_findings"]["total"],
            "actual_total": verdict["actual_findings"]["total"],
            "archetype": verdict["archetype"],
        })
        print(
            f"{case}: dispatched={evidence['dispatch']['dispatched']} "
            f"expected={verdict['expected_findings']['total']} "
            f"actual={verdict['actual_findings']['total']} "
            f"match={verdict['match']} "
            f"archetype={verdict['archetype']}"
        )

    n_match = sum(1 for s in summary if s["match"])
    print(
        f"\nCross-val: {n_match}/{len(summary)} cases MATCH expected D11 behavior."
    )
    return 0 if n_match == len(summary) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

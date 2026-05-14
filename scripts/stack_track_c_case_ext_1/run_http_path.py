"""Path (a) · ``POST /api/ai-review`` via FastAPI TestClient against case_004.

V63-A Tier 2 sub-DEC M-CASE-EXT-1 · 4th distinct numerics class Track C session.

TestClient is used instead of a live uvicorn server to avoid port conflicts
(per MEMORY rule "no port squatting"). The route is the production code path;
TestClient calls .app directly and exercises the same Pydantic schema +
audit-artifact persistence.

Run from repo root:
    .venv/bin/python -m scripts.stack_track_c_case_ext_1.run_http_path
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

from fastapi.testclient import TestClient  # noqa: E402

from scripts.stack_track_c_case_ext_1.build_inputs import (  # noqa: E402
    build_parts_manifest,
)
from ui.backend.main import app  # noqa: E402


def main() -> dict:
    # Symmetric with TRACK-3 case_006: pass only parts_manifest to avoid
    # auto-discovery confounds. shm_dict / thermo_dict are None (build_*
    # returned None for case_004 substrate), so we omit them from the payload.
    # case_004 has no thin_wall_inputs / interface_bodies / step_path field
    # available on the route schema either (same route-schema gap noted in
    # TRACK-3 §7 item 1).
    payload = {
        "parts_manifest": build_parts_manifest(),
    }

    payload_path = Path(__file__).parent / "case_004_v1_payload.json"
    payload_path.write_text(json.dumps(payload, indent=2, default=str))

    with TestClient(app) as client:
        resp = client.post("/api/ai-review", json=payload)

    status = resp.status_code
    body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    report = body.get("report") or {}

    findings = report.get("findings") or []
    advisor_calls = report.get("advisor_calls") or []
    advisors_dispatched = sorted({c.get("advisor_name") for c in advisor_calls if c.get("advisor_name")})

    out = {
        "status_code": status,
        "advisor_count": report.get("advisor_count"),
        "finding_count": len(findings),
        "critical_count": sum(1 for f in findings if f.get("severity") in ("critical", "fail")),
        "warning_count": sum(1 for f in findings if f.get("severity") == "warning"),
        "failed_advisor_count": sum(1 for c in advisor_calls if c.get("status") == "error"),
        "advisors_dispatched": advisors_dispatched,
        "advisor_calls": [
            {
                "advisor_name": c.get("advisor_name"),
                "status": c.get("status"),
                "input_summary": c.get("input_summary"),
                "duration_ms": c.get("duration_ms"),
            }
            for c in advisor_calls
        ],
        "evidence_refs": sorted(report.get("evidence_refs") or []),
        "findings": findings,
        "llm_enhanced": body.get("llm_enhanced"),
        "audit_artifact_path": body.get("audit_artifact_path"),
        "env_keys_present": {
            k: bool(os.environ.get(k))
            for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY", "DEEPSEEK_API_KEY")
        },
    }

    out_path = Path(__file__).parent / "stack_report_http.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps({k: v for k, v in out.items() if k != "findings"}, indent=2, default=str))
    print(f"\n[http-path] wrote {out_path}")
    print(f"[http-path] {len(out['findings'])} findings detail in JSON file")
    return out


if __name__ == "__main__":
    main()

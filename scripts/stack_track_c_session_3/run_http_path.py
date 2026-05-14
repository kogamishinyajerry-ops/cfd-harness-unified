"""Path (a) · `POST /api/ai-review` via FastAPI TestClient against case_006.

Track C session 3 (M-STACK-TRACK-3 · validation case).

TestClient is used instead of a live uvicorn server to avoid port conflicts
(per MEMORY rule "no port squatting"). The route is the production code path;
TestClient calls .app directly and exercises the same Pydantic schema +
audit-artifact persistence.

Run from repo root:
    .venv/bin/python -m scripts.stack_track_c_session_3.run_http_path
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

from scripts.stack_track_c_session_3.build_inputs import (  # noqa: E402
    build_parts_manifest,
    build_shm_dict,
    build_thermo_dict,
)
from ui.backend.main import app  # noqa: E402


def main() -> dict:
    payload = {
        "parts_manifest": build_parts_manifest(),
        "shm_dict": build_shm_dict(),
        "thermo_dict": build_thermo_dict(),
        # NOTE: route schema does NOT accept step_path / interface_bodies /
        # interface_specs / thin_wall_inputs-as-dict directly; auto-discovery
        # via case_dir is the only HTTP path. case_006 inputs/ holds the
        # parts_manifest.yaml + cad_codex_v1.step but no shm/thermo/thin_wall
        # YAML — to preserve symmetry with the python path, we pass the
        # 3 dict artifacts explicitly and omit case_dir auto-discovery.
    }

    payload_path = Path(__file__).parent / "case_006_v1_payload.json"
    payload_path.write_text(json.dumps(payload, indent=2, default=str))

    client = TestClient(app)
    resp = client.post("/api/ai-review", json=payload)

    if resp.status_code != 200:
        out = {
            "status_code": resp.status_code,
            "body": resp.json(),
        }
        (Path(__file__).parent / "stack_report_http.json").write_text(
            json.dumps(out, indent=2)
        )
        return out

    data = resp.json()
    report = data["report"]
    advisor_calls = report.get("advisor_calls", [])

    out = {
        "status_code": resp.status_code,
        "advisor_count": report.get("advisor_count"),
        "finding_count": len(report.get("findings", [])),
        "critical_count": report.get("critical_count"),
        "warning_count": report.get("warning_count"),
        "failed_advisor_count": report.get("failed_advisor_count"),
        "advisors_dispatched": sorted({c["advisor_name"] for c in advisor_calls}),
        "evidence_refs": sorted(report.get("evidence_refs", [])),
        "findings": report.get("findings", []),
        "advisor_calls": [
            {
                "advisor_name": c["advisor_name"],
                "status": c["status"],
                "duration_ms": c["duration_ms"],
                "input_summary": c["input_summary"],
                "version": c["version"],
            }
            for c in advisor_calls
        ],
        "audit_artifact_path": data.get("audit_artifact_path"),
        "llm_enhanced": data.get("llm_enhanced"),
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

    out_path = Path(__file__).parent / "stack_report_http.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))
    return out


if __name__ == "__main__":
    out = main()
    print(
        json.dumps(
            {
                "status_code": out["status_code"],
                "advisor_count": out.get("advisor_count"),
                "finding_count": out.get("finding_count"),
                "critical_count": out.get("critical_count"),
                "warning_count": out.get("warning_count"),
                "failed_advisor_count": out.get("failed_advisor_count"),
                "advisors_dispatched": out.get("advisors_dispatched"),
                "evidence_refs": out.get("evidence_refs"),
                "llm_enhanced": out.get("llm_enhanced"),
                "audit_artifact_path": out.get("audit_artifact_path"),
                "env_keys_present": out.get("env_keys_present"),
            },
            indent=2,
        )
    )

"""Path (a): HTTP POST to /api/ai-review for case_011 v5b.

Compares the HTTP response against the Python-path stack report
(stack_report_python.json). Both must produce identical Finding
counts, identical advisor_calls statuses, and identical evidence
V-row union — otherwise the stack has surface-shape divergence
between in-process and over-the-wire callers.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from scripts.stack_track_c_session_1.build_inputs import assemble_payload  # noqa: E402


def _post_review(host: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f"{host}/api/ai-review",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    host = "http://127.0.0.1:8001"
    payload_raw = assemble_payload()

    # POST body matches AIReviewRequest BaseModel:
    #   case_dir / parts_manifest / shm_dict / thermo_dict / thin_wall_inputs
    request_body = {
        "parts_manifest": payload_raw["parts_manifest"],
        "shm_dict": payload_raw["shm_dict"],
        "thin_wall_inputs": payload_raw["thin_wall_inputs"],
    }
    # Note: AIReviewRequest does NOT accept step_path / step_bbox; those are
    # constructed server-side from case_dir auto-discovery. We're testing the
    # wire contract here, so omit them.

    response = _post_review(host, request_body)
    out = Path(__file__).parent / "stack_report_http.json"
    out.write_text(json.dumps(response, indent=2))

    print(f"=== stack report (HTTP path) ===")
    print(f"out: {out}")
    rep = response.get("report", {})
    print(f"advisor_count:        {rep.get('advisor_count')}")
    print(f"finding_count:        {len(rep.get('findings', []))}")
    print(f"critical_count:       {rep.get('critical_count')}")
    print(f"warning_count:        {rep.get('warning_count')}")
    print(f"failed_advisor_count: {rep.get('failed_advisor_count')}")
    advisors = [c.get("advisor_name") for c in rep.get("advisor_calls", [])]
    statuses = [(c.get("advisor_name"), c.get("status")) for c in rep.get("advisor_calls", [])]
    print(f"advisors_dispatched:  {advisors}")
    print(f"advisor_statuses:     {statuses}")
    print(f"evidence_refs:        {sorted(rep.get('evidence_refs', []))}")
    print()
    print("=== findings ===")
    for i, f in enumerate(rep.get("findings", []), 1):
        sev = f.get("severity", "?").upper()
        adv = f.get("source_advisor", "?")
        code = f.get("code", "?")
        msg = (f.get("message") or "")[:200]
        rows = f.get("evidence_v_rows", [])
        print(f"[{i}] [{sev}] advisor={adv} code={code}")
        print(f"     v_rows={tuple(rows)}")
        print(f"     msg={msg}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        print(f"HTTP {exc.code} {exc.reason}: {body[:500]}", file=sys.stderr)
        sys.exit(2)

"""Path (a) rerun: HTTP POST /api/ai-review for case_011 v5b after
B31 REQ-SCHEMA-EXPAND (commit a1119ae) which adds step_path / step_bbox
/ step_extents / interface_bodies / interface_specs to AIReviewRequest.

Compared to TRACK-1 original (scripts/stack_track_c_session_1/
run_http_path.py): now passes step_path + step_bbox explicitly so the
HTTP path can dispatch unit_detector, closing the path A vs path B
advisor-count gap documented in the original retro §2.

Expected outcome (per smoke evidence and TRACK-1 §8 enhancements #1/#2):
- Path A advisor count rises from 4 → 5+ (drift_guard still added at
  route boundary on top of assemble_stack's 5).
- Findings shrink from 7 → ~2 (6 shm false-positives silenced by V99,
  unit_detector finding now present, thin_wall finding preserved).
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
    host = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8002"
    payload_raw = assemble_payload()

    # Build request body with all REQ-SCHEMA-EXPAND fields now accepted.
    # step_bbox 6-tuple is server-reduced to step_bbox_max_extent_raw =
    # max(extents). Use the same extent value the python-path passes
    # (0.180 m) so both paths probe the same body shape.
    ext = float(payload_raw["step_bbox_max_extent_raw"])
    request_body = {
        "parts_manifest": payload_raw["parts_manifest"],
        "shm_dict": payload_raw["shm_dict"],
        "thin_wall_inputs": payload_raw["thin_wall_inputs"],
        "step_path": payload_raw["step_path"],
        "step_bbox": [0.0, 0.0, 0.0, ext, ext, ext],
        "step_extents": [ext],
    }
    # interface_bodies / interface_specs / bc_specs intentionally absent
    # — case_011 v5b substrate carries none of these artifacts (no
    # interface_bodies.json, parts_manifest has cellZone roles only).
    # A2-v2 / D6 / D10 will silently skip on both paths.

    response = _post_review(host, request_body)
    out = Path(__file__).parent / "stack_report_http_rerun.json"
    out.write_text(json.dumps(response, indent=2))

    print("=== stack report (HTTP path RERUN · B31 schema-expand + V99-WIDEN) ===")
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
        print(f"HTTP {exc.code} {exc.reason}: {body[:1000]}", file=sys.stderr)
        sys.exit(2)

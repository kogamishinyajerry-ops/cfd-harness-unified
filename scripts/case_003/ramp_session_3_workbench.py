"""case_003 ramp · session 3 driver · workbench import probe.

Three substrate probes against POST /api/import/stl using the 10 ASCII STL
produced by session 2's freecad_step_to_stl bridge:

    A. raw airframe upload (87 MB) → expect 413 (50 MB cap)
    B. small single-body upload (inlet.stl, ~3 KB) → ingestion outcome +
       whether patch name comes through as the body label
    C. combined multi-solid ASCII of 9 small bodies (no airframe) with
       per-body 'solid <label>' headers rewritten → patch detection
       outcome
    D. combined multi-solid ASCII of all 10 bodies → expect 413 again

Run from repo root:
    .venv/bin/python scripts/case_003/ramp_session_3_workbench.py

Spike-class probe; not production code. Output goes to ramp_log session 3.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from ui.backend.main import app  # noqa: E402

STL_DIR = REPO_ROOT / "ui/backend/user_drafts/imported/case_003_crm_hls/stl_session_2"
MANIFEST = STL_DIR / "manifest.json"

_SOLID_RE = re.compile(rb"^\s*solid\b[^\n]*", re.MULTILINE)
_ENDSOLID_RE = re.compile(rb"^\s*endsolid\b[^\n]*", re.MULTILINE)


def rewrite_solid_name(stl_bytes: bytes, name: str) -> bytes:
    encoded = name.encode("ascii", errors="replace")
    out = _SOLID_RE.sub(b"solid " + encoded, stl_bytes, count=1)
    out = _ENDSOLID_RE.sub(b"endsolid " + encoded, out, count=1)
    if not out.endswith(b"\n"):
        out += b"\n"
    return out


def main() -> int:
    if not MANIFEST.exists():
        print(f"MANIFEST missing: {MANIFEST}. Regenerate session 2 first.")
        return 1
    manifest = json.loads(MANIFEST.read_text())
    print(f"=== case_003 ramp · session 3 · workbench import ===")
    print(f"manifest: {MANIFEST}  ({manifest['n_bodies']} bodies)")
    print()

    client = TestClient(app)

    # --- Probe A: raw airframe ---
    airframe_path = STL_DIR / "airframe_reference.stl"
    airframe_bytes = airframe_path.read_bytes()
    print(f"[A] POST /api/import/stl with airframe_reference.stl ({len(airframe_bytes) / 1e6:.1f} MB)")
    resp = client.post(
        "/api/import/stl",
        files={"file": ("airframe_reference.stl", airframe_bytes, "application/sla")},
    )
    print(f"    status={resp.status_code}")
    try:
        detail = resp.json()
        if isinstance(detail, dict):
            d = detail.get("detail", detail)
            if isinstance(d, dict):
                print(f"    failing_check={d.get('failing_check')!r}  reason={d.get('reason')!r}")
            else:
                print(f"    detail={d!r}")
    except Exception:
        print(f"    body-bytes={len(resp.content)}")
    print()

    # --- Probe B: small single body ---
    inlet_path = STL_DIR / "inlet.stl"
    inlet_bytes = inlet_path.read_bytes()
    print(f"[B] POST /api/import/stl with inlet.stl ({len(inlet_bytes)} B)")
    resp = client.post(
        "/api/import/stl",
        files={"file": ("inlet.stl", inlet_bytes, "application/sla")},
    )
    print(f"    status={resp.status_code}")
    body = resp.json()
    if resp.status_code == 200:
        report = body["ingest_report"]
        print(f"    case_id={body['case_id']}  watertight={report['is_watertight']}  "
              f"solid_count={report['solid_count']}  unit_guess={report['unit_guess']!r}")
        print(f"    patches={[p['name'] for p in report['patches']]}  "
              f"all_default_faces={report['all_default_faces']}")
        print(f"    bbox_extent={report['bbox_extent']}")
        print(f"    warnings={report['warnings']}")
    else:
        d = body.get("detail", body)
        print(f"    failing_check={d.get('failing_check')!r}  reason={d.get('reason')!r}")
        if "ingest_report" in d:
            r = d["ingest_report"]
            print(f"    report.solid_count={r.get('solid_count')}  "
                  f"watertight={r.get('is_watertight')}  patches={[p['name'] for p in r.get('patches', [])]}")
    print()

    # --- Build combined multi-solid ASCII ---
    def build_combined(bodies_subset):
        chunks = []
        for body_meta in bodies_subset:
            raw = (STL_DIR / f"{body_meta['stem']}.stl").read_bytes()
            chunks.append(rewrite_solid_name(raw, body_meta["stem"]))
        return b"".join(chunks)

    small_bodies = [b for b in manifest["bodies"] if b["stem"] != "airframe_reference"]
    combined_small = build_combined(small_bodies)
    print(f"[C] POST /api/import/stl with combined (9 bodies, no airframe) "
          f"({len(combined_small)} B)")
    resp = client.post(
        "/api/import/stl",
        files={"file": ("case_003_combined_no_airframe.stl", combined_small, "application/sla")},
    )
    print(f"    status={resp.status_code}")
    body = resp.json()
    if resp.status_code == 200:
        report = body["ingest_report"]
        print(f"    case_id={body['case_id']}  watertight={report['is_watertight']}  "
              f"solid_count={report['solid_count']}  unit_guess={report['unit_guess']!r}")
        print(f"    patches={[p['name'] for p in report['patches']]}")
        print(f"    all_default_faces={report['all_default_faces']}")
        print(f"    bbox_extent={report['bbox_extent']}")
        print(f"    warnings={report['warnings']}")
    else:
        d = body.get("detail", body)
        print(f"    failing_check={d.get('failing_check')!r}  reason={d.get('reason')!r}")
        if "ingest_report" in d:
            r = d["ingest_report"]
            print(f"    report.solid_count={r.get('solid_count')}  watertight={r.get('is_watertight')}  "
                  f"patches={[p['name'] for p in r.get('patches', [])]}")
    print()

    # --- Probe D: combined all 10 ---
    combined_all = build_combined(manifest["bodies"])
    print(f"[D] POST /api/import/stl with combined (all 10 bodies) "
          f"({len(combined_all) / 1e6:.1f} MB)")
    resp = client.post(
        "/api/import/stl",
        files={"file": ("case_003_combined.stl", combined_all, "application/sla")},
    )
    print(f"    status={resp.status_code}")
    try:
        d = resp.json().get("detail", {})
        if isinstance(d, dict):
            print(f"    failing_check={d.get('failing_check')!r}  reason={d.get('reason')!r}")
    except Exception:
        pass
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())

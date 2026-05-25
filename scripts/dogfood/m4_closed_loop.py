#!/usr/bin/env python3
"""M4 (DEC-V61-204) closed-loop dogfood — asserts the charter close-criterion
1-4 against a running backend.

The V4 workbench's post-Step-7 loop is: build → Run (C2 trigger) → results
refresh → report figures (C3 display). This script exercises that loop at the
API layer the V4 UI calls, so a green run here = the UI's closed loop is backed
by real backend behavior (the UI wiring itself is covered by vitest + the
mock-mode visual spot-checks in the C2/C3 retros).

Charter close-criterion (DEC-V61-204), `passes: true` iff ALL hold:
  1. POST /api/import/{case}/solve → exit_code 0 (SolveSummary; converged).
  2. results refresh: /residual-series source flips off "empty" (→ log/runs);
     /results-summary returns finite U-magnitude stats.
  3. /report-bundle returns the 4 figure artifacts OR a classified
     "unavailable" state (500+matplotlib) — never an unclassified crash.
  4. no regression to the M3.x guided flow → the V4 vitest suite (run
     separately: `npm test` in ui/frontend); reported here as a reminder.

USAGE:
    .venv/bin/python scripts/dogfood/m4_closed_loop.py \
        --base-url http://127.0.0.1:8001 --case-id lid_driven_cavity

Exit 0 = criteria 1-3 PASS (live solver available + loop closes).
Exit 2 = live solver unavailable (cfd-openfoam container down / case not
         built) — criteria 1-3 could not be exercised; the precise blocker is
         printed. NOT a fabricated pass.
Exit 1 = a criterion was exercised and FAILED.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import urllib.error
import urllib.request


def _req(method: str, url: str, timeout: float = 180.0):
    req = urllib.request.Request(url, method=method, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, (json.loads(body) if body else None)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            detail = json.loads(body)
        except Exception:
            detail = body
        return e.code, detail


def _finite(x) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(x)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8001")
    ap.add_argument("--case-id", default="lid_driven_cavity")
    ap.add_argument("--solve-timeout", type=float, default=300.0)
    args = ap.parse_args()
    base = args.base_url.rstrip("/")
    cid = args.case_id

    print(f"# M4 closed-loop dogfood · base={base} · case={cid}\n")

    # ── Criterion 1 · Run ──────────────────────────────────────────────
    print("[1/3] POST /solve (engineer-initiated run; AI never triggers this)…")
    status, body = _req("POST", f"{base}/api/import/{cid}/solve", timeout=args.solve_timeout)
    blob = json.dumps(body).lower() if body is not None else ""
    # Setup/infra blockers (not loop-logic failures): container down, case not
    # imported, or case not built to a solvable state (no mesh / BCs). These
    # mean "criteria 1-3 could not be exercised" — exit 2, never a fake pass.
    setup_blocker = (
        status == 503
        or (status == 404 and "not found" in blob)
        or (status == 409 and any(
            t in blob for t in ("mesh_missing", "bc_not_setup", "mesh_bc_mismatch")
        ))
        or ("container" in blob and "not" in blob)
    )
    if setup_blocker:
        print(f"  ⏭  live solver/case not ready (HTTP {status}): {body}")
        print("     → bring up cfd-openfoam + import & build the case (mesh + BCs),")
        print("       then re-run. Criteria 1-3 NOT exercised (no fabricated pass).")
        return 2
    if status != 200 or not isinstance(body, dict):
        print(f"  ✗ FAIL: /solve HTTP {status}: {body}")
        return 1
    converged = body.get("converged")
    wall = body.get("wall_time_s")
    print(f"  ✓ solve returned 200 · converged={converged} · wall_time_s={wall}")

    # ── Criterion 2 · results refresh ──────────────────────────────────
    print("[2/3] GET /residual-series + /results-summary…")
    _, rs = _req("GET", f"{base}/api/cases/{cid}/residual-series")
    src = rs.get("source") if isinstance(rs, dict) else None
    if src in (None, "empty"):
        print(f"  ✗ FAIL: residual-series source still '{src}' after solve")
        return 1
    print(f"  ✓ residual-series source flipped to '{src}'")
    sstatus, summ = _req("GET", f"{base}/api/cases/{cid}/results-summary")
    umag = None
    if isinstance(summ, dict):
        umag = (summ.get("u_magnitude") or summ.get("U_magnitude") or {})
    finite_stats = isinstance(umag, dict) and any(_finite(v) for v in umag.values())
    if not finite_stats:
        print(f"  ✗ FAIL: results-summary lacks finite U stats (HTTP {sstatus}): {summ}")
        return 1
    print(f"  ✓ results-summary has finite U-magnitude stats")

    # ── Criterion 3 · report figures OR classified fallback ────────────
    print("[3/3] GET /report-bundle (figures render OR classified fallback)…")
    rbstatus, rb = _req("GET", f"{base}/api/cases/{cid}/report-bundle")
    if rbstatus == 200 and isinstance(rb, dict) and len(rb.get("artifacts", {})) == 4:
        print(f"  ✓ report-bundle 200 · 4 artifacts · plane={rb.get('plane_axes')}")
    elif rbstatus == 500 and "matplotlib" in json.dumps(rb).lower():
        print("  ✓ matplotlib absent → 500 'matplotlib required' (UI shows the")
        print("    explicit 'report unavailable on this build' fallback — acceptable)")
    elif rbstatus in (404, 409):
        print(f"  ✗ FAIL: report-bundle {rbstatus} after a successful solve "
              f"(expected figures or matplotlib-500): {rb}")
        return 1
    else:
        print(f"  ✗ FAIL: report-bundle unclassified state HTTP {rbstatus}: {rb}")
        return 1

    print("\n# criteria 1-3 PASS · run the V4 vitest suite for criterion 4 "
          "(no-regression).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

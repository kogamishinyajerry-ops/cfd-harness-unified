"""Live-fire smoke test (P2) — drive a real workbench through the
persona-facing route chain end-to-end.

Complementary to `ui/backend/tests/test_persona_facing_smoke_e2e.py`:
that one uses TestClient + mocked solver_runner so it runs in CI
without Docker. THIS script hits an actual running workbench at
localhost:8000 and exercises the real OpenFOAM container, validating
the chain that 30+ live persona runs accumulated in B-ext-2..6.

Use cases:
- Pre-merge sanity check before opening a PR that touches /solve,
  setup-bc, run_history, field_sample, or geometry_render
- Post-deploy smoke against a staging workbench
- Reproducing an F-series finding in isolation (e.g., reproducing F13
  /solve 502 on a specific case)

Walks the same route order a Step 6 persona walks:

    /api/health
    POST /api/import/stl                        (multipart STL)
    POST /api/import/{case_id}/mesh             (gmsh + gmshToFoam)
    POST /api/import/{case_id}/setup-bc         (LDC defaults)
    POST /api/import/{case_id}/solve            (icoFoam in container)
    GET  /api/cases/{case_id}/run-history       (F11)
    GET  /api/cases/{case_id}/run-history/{id}  (F11 measurement.yaml)
    GET  /api/cases/{case_id}/results-summary   (final-time U parsed)
    GET  /api/cases/{case_id}/results/{id}/field/U  (F15 vector)
    GET  /api/cases/{case_id}/results/{id}/field/p  (F15 scalar)

Each step asserts an F-series invariant; first failure exits non-zero
with a one-line summary suitable for a Slack/email/CI alert.

Usage:
    .venv/bin/python -m scripts.dogfood.smoke_simulation
    .venv/bin/python -m scripts.dogfood.smoke_simulation --base-url http://staging.internal:8000
    .venv/bin/python -m scripts.dogfood.smoke_simulation --case backward_step

Exit codes: 0 = all asserts pass; 2 = workbench unreachable; 3 =
F-series invariant failed.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import httpx

GEOMETRY_DIR = Path("scripts/dogfood/cases/geometry")
DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_CASE = "backward_step"


def _check(label: str, ok: bool, detail: str = "") -> None:
    """Assert an F-series invariant; on failure print a one-line summary
    and exit 3 (so CI alerts can grep for FAIL: lines)."""
    if ok:
        print(f"  PASS · {label}")
        return
    print(f"FAIL: {label} · {detail}", file=sys.stderr)
    sys.exit(3)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--case", default=DEFAULT_CASE,
                        choices=["backward_step", "naca0012", "pipe_expansion"])
    parser.add_argument("--timeout", type=float, default=120.0,
                        help="per-request timeout for the smoke client")
    args = parser.parse_args(argv)

    base = args.base_url.rstrip("/")
    stl_file = GEOMETRY_DIR / f"{args.case}.stl"
    if not stl_file.exists():
        print(f"FAIL: STL fixture missing: {stl_file}", file=sys.stderr)
        return 2

    print(f"Live-fire smoke · base={base} · case={args.case}")
    print("=" * 60)

    with httpx.Client(timeout=args.timeout) as wb:
        # 0. Workbench reachable?
        try:
            r = wb.get(f"{base}/api/health")
        except httpx.HTTPError as exc:
            print(f"FAIL: workbench unreachable: {exc}", file=sys.stderr)
            return 2
        _check("workbench /api/health 200", r.status_code == 200,
               f"got {r.status_code}")

        # 1. STL upload
        with stl_file.open("rb") as fh:
            r = wb.post(
                f"{base}/api/import/stl",
                files={"file": (stl_file.name, fh, "model/stl")},
            )
        _check("POST /api/import/stl 200", r.status_code == 200,
               f"{r.status_code}: {r.text[:200]}")
        case_id = r.json()["case_id"]
        print(f"  → case_id={case_id}")

        # 2. Mesh
        r = wb.post(f"{base}/api/import/{case_id}/mesh", json={})
        _check("POST /mesh 200", r.status_code == 200,
               f"{r.status_code}: {r.text[:200]}")
        cell_count = r.json()["mesh_summary"]["cell_count"]
        _check("mesh has cells", cell_count > 0, f"cell_count={cell_count}")

        # 3. Setup-bc (LDC defaults — wrong physics on non-cube but
        # transport-validates the chain; F12-warning may surface)
        r = wb.post(f"{base}/api/import/{case_id}/setup-bc")
        _check("POST /setup-bc 200", r.status_code == 200,
               f"{r.status_code}: {r.text[:200]}")
        warnings = r.json().get("warnings") or []
        if warnings:
            print(f"  → F12 warnings surfaced: {warnings[0][:80]}...")

        # 4. Solve (the long step — actual OpenFOAM container)
        t0 = time.monotonic()
        r = wb.post(f"{base}/api/import/{case_id}/solve")
        solve_s = time.monotonic() - t0
        _check("POST /solve 200", r.status_code == 200,
               f"{r.status_code} in {solve_s:.1f}s: {r.text[:200]}")
        body = r.json()
        run_id = body.get("run_id")
        _check("F11 · /solve returns run_id (DEC-V61-188)",
               run_id is not None and run_id != "",
               f"run_id={run_id!r}")
        print(f"  → run_id={run_id} · converged={body['converged']}"
              f" · wall_time_s={body['wall_time_s']:.1f}")

        # 5. F11 invariant: /run-history lists the run
        r = wb.get(f"{base}/api/cases/{case_id}/run-history")
        _check("GET /run-history 200", r.status_code == 200,
               f"{r.status_code}: {r.text[:200]}")
        run_ids = [run["run_id"] for run in r.json()["runs"]]
        _check(f"F11 · run_id={run_id} in /run-history (DEC-V61-188)",
               run_id in run_ids,
               f"run-history has {run_ids}")

        # 6. F11 detail: measurement.yaml round-trip
        r = wb.get(f"{base}/api/cases/{case_id}/run-history/{run_id}")
        _check("GET /run-history/{id} 200", r.status_code == 200,
               f"{r.status_code}: {r.text[:200]}")
        d = r.json()
        residuals = d.get("residuals") or {}
        _check("F11 · measurement.yaml carries residuals.p",
               residuals.get("p") is not None,
               f"residuals={residuals}")

        # 7. /results-summary parses final-time U
        r = wb.get(f"{base}/api/cases/{case_id}/results-summary")
        _check("GET /results-summary 200 (DEC-V61-178)",
               r.status_code == 200,
               f"{r.status_code}: {r.text[:200]}")
        s = r.json()
        _check("results-summary has cell_count",
               s.get("cell_count", 0) > 0,
               f"cell_count={s.get('cell_count')}")

        # 8. F15 invariant: /field/U returns 200 with vector header
        r = wb.get(
            f"{base}/api/cases/{case_id}/results/{run_id}/field/U"
        )
        _check("F15 · /field/U 200 (DEC-V61-196 layer 1+2)",
               r.status_code == 200,
               f"{r.status_code}: {r.text[:200]}")
        components = r.headers.get("X-Field-Components")
        _check("F15 · X-Field-Components: 3 for U (vector parser)",
               components == "3",
               f"got X-Field-Components={components!r}")
        n_cells = int(r.headers.get("X-Field-Point-Count", "0"))
        expected_bytes = n_cells * 3 * 4
        _check(
            f"F15 · /field/U body length = {expected_bytes} bytes",
            len(r.content) == expected_bytes,
            f"got {len(r.content)} bytes for {n_cells} cells × 3 × 4",
        )

        # 9. F15 regression-guard: scalar p still returns components=1
        r = wb.get(
            f"{base}/api/cases/{case_id}/results/{run_id}/field/p"
        )
        _check("F15 · /field/p 200 (scalar regression guard)",
               r.status_code == 200,
               f"{r.status_code}: {r.text[:200]}")
        _check("F15 · X-Field-Components: 1 for p (scalar unchanged)",
               r.headers.get("X-Field-Components") == "1",
               f"got {r.headers.get('X-Field-Components')!r}")

    print("=" * 60)
    print(f"OK · all F-series invariants hold · solve_s={solve_s:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Adversarial-loop executable smoke test.

Drives every adversarial case under ``tools/adversarial/cases/`` through
the cfd-harness pipeline (import → mesh → BC → solve) and asserts the
expected outcome from each case's ``intent.json``. Designed to run as
a pre-push gate for backend changes that touch the import / mesh / BC /
solve hot paths.

This operationalizes RETRO-V61-053's ``executable_smoke_test`` risk
flag — the post-R3 defects (Codex APPROVE'd code that fails at runtime)
that motivated the flag. Defect 8 (iter06 symmetry constraint type)
was discovered exactly this way during the 2026-04-30/05-01 adversarial
arc; this runner converts that one-shot validation into permanent
regression protection.

Per-case behavior is declared via ``intent.json`` field
``smoke_runner.expected_status``:
  - ``converged``           — full pipeline must succeed and converge
  - ``manual_bc_baseline``  — uses author_dicts.py path (skipped here;
                              run via the legacy iter03 driver instead)
  - ``expected_failure_v61_104`` — known to fail until DEC-V61-104 ships
                                   (interior obstacle topology). Failure
                                   is logged but doesn't fail the suite.
  - ``analytical_comparator_pass`` — DEC-V61-106. Run full pipeline,
                                     ignore residual gate, evaluate the
                                     case's ``analytical_comparators``
                                     block against the extractor's
                                     ResultsSummary measures. PASS iff
                                     all comparators pass.

Default backend URL is http://127.0.0.1:8003. Override via --base-url
or CFD_BACKEND_URL env. Exits non-zero when any case fails its declared
expectation.

Usage:
    python tools/adversarial/run_smoke.py
    python tools/adversarial/run_smoke.py --filter iter06
    python tools/adversarial/run_smoke.py --base-url http://localhost:8000
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import urllib.error
import urllib.request

# DEC-V61-106: analytical_comparator_pass support. The comparator
# evaluator is pure-logic (no backend deps). The extractor IS a backend
# import — kept lazy so that the smoke runner stays importable without
# the full backend env when the user runs it for help/dry-run.
# Add the project root (two levels up from tools/adversarial/) so both
# ``tools.adversarial.*`` and ``ui.backend.*`` resolve.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.adversarial.comparators import (  # noqa: E402
    ComparatorSuiteResult,
    evaluate_comparator_suite,
    format_suite_summary,
)


CASES_ROOT = Path(__file__).resolve().parent / "cases"
DEFAULT_BASE_URL = os.environ.get("CFD_BACKEND_URL", "http://127.0.0.1:8003")

# Cases without an explicit smoke_runner block in intent.json default to
# this (so newly-added cases are smoke-tested unless opted out).
_DEFAULT_CONFIG = {"expected_status": "converged"}


class SmokeError(RuntimeError):
    """Raised when a pipeline call fails before convergence is even
    knowable (network error, HTTP 5xx, etc.). Distinct from a case
    that diverges (which is itself the assertion target)."""


def _http_post_multipart(url: str, file_path: Path, timeout: float) -> dict:
    """Minimal multipart/form-data POST (single ``file`` field). Avoids
    a runtime dependency on ``requests`` so the runner works in a clean
    venv with stdlib only."""
    boundary = b"----cfd-smoke-boundary-9b3f7a2e"
    content_type = f"multipart/form-data; boundary={boundary.decode()}"
    body = (
        b"--" + boundary + b"\r\n"
        b'Content-Disposition: form-data; name="file"; filename="'
        + file_path.name.encode("ascii") + b'"\r\n'
        b"Content-Type: application/octet-stream\r\n\r\n"
        + file_path.read_bytes()
        + b"\r\n--" + boundary + b"--\r\n"
    )
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": content_type, "Content-Length": str(len(body))},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        raise SmokeError(f"HTTP {exc.code} at {url}: {body_text}") from exc
    except urllib.error.URLError as exc:
        raise SmokeError(f"network error at {url}: {exc}") from exc


def _http_post_json(url: str, payload: dict | None, timeout: float) -> dict:
    data = json.dumps(payload or {}).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/json", "Content-Length": str(len(data))},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        try:
            body_json = json.loads(body_text)
        except json.JSONDecodeError:
            body_json = {"raw": body_text}
        raise SmokeError(f"HTTP {exc.code} at {url}: {body_json}") from exc
    except urllib.error.URLError as exc:
        raise SmokeError(f"network error at {url}: {exc}") from exc


def _check_backend(base_url: str) -> None:
    try:
        with urllib.request.urlopen(f"{base_url}/api/health", timeout=5) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            if body.get("status") != "ok":
                raise SmokeError(f"backend unhealthy: {body}")
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        raise SmokeError(
            f"backend not reachable at {base_url}/api/health: {exc}. "
            "Start with `uvicorn ui.backend.main:app --port 8003` or "
            "set CFD_BACKEND_URL."
        ) from exc


def _load_smoke_config(case_dir: Path) -> dict:
    intent_path = case_dir / "intent.json"
    if not intent_path.is_file():
        return dict(_DEFAULT_CONFIG)
    try:
        intent = json.loads(intent_path.read_text())
    except (json.JSONDecodeError, OSError):
        return dict(_DEFAULT_CONFIG)
    cfg = dict(_DEFAULT_CONFIG)
    cfg.update(intent.get("smoke_runner", {}))
    return cfg


def run_case(case_dir: Path, base_url: str) -> dict[str, Any]:
    """Drive one adversarial case through the full pipeline. Returns a
    structured result dict with a ``status`` field — never raises for
    expected pipeline failures (those become status="diverged" or
    status="failed_<stage>")."""
    geometry = case_dir / "geometry.stl"
    if not geometry.is_file():
        return {"case": case_dir.name, "status": "skipped",
                "reason": "no geometry.stl (likely manual_bc_baseline)"}

    cfg = _load_smoke_config(case_dir)
    expected = cfg.get("expected_status", "converged")
    if expected == "manual_bc_baseline":
        return {"case": case_dir.name, "status": "skipped",
                "reason": "manual_bc_baseline — run via case-specific driver"}
    if expected == "physics_validation_required":
        # Case converges numerically but the physics needs domain-
        # knowledge validation. DEC-V61-106 deprecates this class —
        # cases should declare an explicit analytical_comparator_pass
        # block. Until each is migrated, skip with a hint.
        return {"case": case_dir.name, "status": "skipped",
                "reason": "physics_validation_required — migrate to analytical_comparator_pass (DEC-V61-106)"}

    started = time.monotonic()

    # Stage 1: import
    try:
        import_resp = _http_post_multipart(
            f"{base_url}/api/import/stl", geometry, timeout=60
        )
    except SmokeError as exc:
        return {"case": case_dir.name, "status": "failed_import",
                "expected_status": expected, "error": str(exc)}
    case_id = import_resp.get("case_id")
    if not case_id:
        return {"case": case_dir.name, "status": "failed_import",
                "expected_status": expected,
                "error": f"import response missing case_id: {import_resp}"}

    # Stage 2: mesh (gmsh + gmshToFoam)
    try:
        mesh_resp = _http_post_json(
            f"{base_url}/api/import/{case_id}/mesh",
            {"mesh_mode": "beginner"}, timeout=300,
        )
    except SmokeError as exc:
        return {"case": case_dir.name, "status": "failed_mesh",
                "expected_status": expected, "case_id": case_id,
                "error": str(exc)}
    cell_count = mesh_resp.get("mesh_summary", {}).get("cell_count")

    # Stage 3: setup-bc (from named STL patches). Honor intent.json's
    # solver block (delta_t, end_time) and physics block
    # (characteristic_velocity_m_s, nu) so cases can declare their own
    # stable parameters. Adversarial iter05 fail-then-pass: the rotated
    # T-junction's mesh has small cells; the backend default U=0.5 +
    # dt=0.01 puts Courant > 9 and the solver explodes by t=0.02s.
    # iter05's intent specifies U=0.3 + dt=0.002 which is stable.
    #
    # Smoke caps: intent values are calibrated for production runs (e.g.
    # iter01 declares end=600s for full convergence to steady-state).
    # The smoke runner only needs enough timesteps to assess convergence
    # trajectory, so we cap dt-derived end_time aggressively. For
    # expected-failure cases, even tighter caps — divergence happens in
    # the first 2-3 timesteps and there's no point chewing CPU cycles
    # on a known-bad case for the full smoke window.
    SMOKE_MAX_STEPS_PASS = 250         # ~2.5s at dt=0.01
    SMOKE_MAX_STEPS_FAIL = 10          # ~0.1s at dt=0.01 — divergence shows by step 3
    SMOKE_MAX_END_PASS = 2.5
    SMOKE_MAX_END_FAIL = 0.1
    bc_qs_parts: list[str] = ["from_stl_patches=1"]
    intent_path = case_dir / "intent.json"
    if intent_path.is_file():
        try:
            intent = json.loads(intent_path.read_text())
        except (json.JSONDecodeError, OSError):
            intent = {}
        physics = intent.get("physics", {}) or {}
        solver = intent.get("solver", {}) or {}
        if "characteristic_velocity_m_s" in physics:
            bc_qs_parts.append(f"inlet_speed={float(physics['characteristic_velocity_m_s'])}")
        if "nu_m2_s" in physics:
            bc_qs_parts.append(f"nu={float(physics['nu_m2_s'])}")
        intent_dt = float(solver.get("delta_t_s", 0.01))
        intent_end = float(solver.get("end_time_s", 5.0))
        # For converged / expected_failure cases the smoke runner caps
        # dt to keep the smoke window short. For analytical-comparator
        # cases the intent's dt was chosen for stability on that
        # specific geometry — overriding it can push CFL into a
        # divergence regime that has nothing to do with the case's
        # physics intent. Trust intent_dt and only cap end_time.
        if expected == "analytical_comparator_pass":
            smoke_dt = intent_dt
        else:
            smoke_dt = min(intent_dt, 0.01)
        if expected.startswith("expected_failure"):
            max_steps, max_end = SMOKE_MAX_STEPS_FAIL, SMOKE_MAX_END_FAIL
        elif expected == "analytical_comparator_pass":
            # Analytical-comparator cases need enough steps for the
            # physics primitives (bypass jet, recirculation) to
            # develop. Keep the step cap (250) but relax the wall-time
            # cap — at intent_dt=1.0 the case needs ~250s run-time, not
            # the 2.5s SMOKE_MAX_END_PASS that's calibrated for
            # transient icoFoam at dt=0.01.
            max_steps = SMOKE_MAX_STEPS_PASS
            max_end = float("inf")
        else:
            max_steps, max_end = SMOKE_MAX_STEPS_PASS, SMOKE_MAX_END_PASS
        smoke_end = min(intent_end, smoke_dt * max_steps, max_end)
        bc_qs_parts.append(f"delta_t={smoke_dt}")
        bc_qs_parts.append(f"end_time={smoke_end}")
    bc_url = f"{base_url}/api/import/{case_id}/setup-bc?" + "&".join(bc_qs_parts)
    try:
        bc_resp = _http_post_json(bc_url, None, timeout=60)
    except SmokeError as exc:
        return {"case": case_dir.name, "status": "failed_setup_bc",
                "expected_status": expected, "case_id": case_id,
                "cell_count": cell_count, "error": str(exc)}
    patches = bc_resp.get("patches", [])
    bc_warnings = bc_resp.get("warnings", [])

    # Stage 4: solve (icoFoam in cfd-openfoam container)
    try:
        solve_resp = _http_post_json(
            f"{base_url}/api/import/{case_id}/solve", None, timeout=600,
        )
    except SmokeError as exc:
        return {"case": case_dir.name, "status": "failed_solve",
                "expected_status": expected, "case_id": case_id,
                "cell_count": cell_count, "patches": patches,
                "bc_warnings": bc_warnings, "error": str(exc)}

    # The backend reports converged=true if the solver runs to end_time
    # without crashing — but iter01 (interior obstacle) diverges to NaN
    # residuals while still "completing" to end_time. Tighten the check
    # by requiring finite residuals and a continuity error within an
    # absolute bound. Defect-9 follow-up: the backend's converged signal
    # is too generous for "did the case converge to a usable solution".
    converged_backend = bool(solve_resp.get("converged"))
    cont_err = solve_resp.get("last_continuity_error")
    residual_p = solve_resp.get("last_initial_residual_p")
    finite = (
        cont_err is not None
        and residual_p is not None
        and isinstance(cont_err, (int, float))
        and isinstance(residual_p, (int, float))
        and abs(cont_err) < 1.0
        and abs(residual_p) < 1.0
        and cont_err == cont_err  # NaN check (NaN != NaN)
        and residual_p == residual_p
    )
    converged = converged_backend and finite

    # DEC-V61-106: analytical_comparator_pass branch. After solve, run
    # the extractor on the case_dir and evaluate the case's comparator
    # block. Verdict is decoupled from the residual gate (the case may
    # not have reached steady state yet, but the physics primitives —
    # bypass jet, recirculation, etc. — should already be present).
    comparator_suite: ComparatorSuiteResult | None = None
    if expected == "analytical_comparator_pass":
        polymesh = mesh_resp.get("mesh_summary", {}).get("polyMesh_path")
        case_disk_dir: Path | None = None
        if polymesh:
            # polyMesh path is "<case_dir>/constant/polyMesh"; walk up 2.
            case_disk_dir = Path(polymesh).parent.parent
        if case_disk_dir is None or not case_disk_dir.is_dir():
            comparator_suite = ComparatorSuiteResult(
                all_passed=False,
                individual_results=(),
                structural_error=f"case_dir_not_found_for_extractor: {case_disk_dir}",
            )
        else:
            # Codex R10: ``case_solve/__init__.py`` eagerly re-exports
            # other backend modules (yaml-dependent, etc.). If the
            # smoke runner runs in a slim env that lacks those deps,
            # the import cascade aborts the whole smoke run instead of
            # surfacing a structured comparator failure. Catch
            # ImportError / ModuleNotFoundError up-front.
            try:
                from ui.backend.services.case_solve.results_extractor import (
                    ResultsExtractError,
                    extract_results_summary,
                )
            except (ImportError, ModuleNotFoundError) as exc:
                comparator_suite = ComparatorSuiteResult(
                    all_passed=False,
                    individual_results=(),
                    structural_error=(
                        f"extractor_import_failed: {exc} — smoke env "
                        "missing backend deps; install ui/backend "
                        "requirements or run from project venv"
                    ),
                )
            else:
                try:
                    summary_obj = extract_results_summary(
                        case_disk_dir, case_id=case_id,
                    )
                    # Pull comparator block from intent.json
                    intent_path = case_dir / "intent.json"
                    comparators = []
                    if intent_path.is_file():
                        try:
                            intent_data = json.loads(intent_path.read_text())
                            comparators = (
                                intent_data.get("smoke_runner", {})
                                .get("analytical_comparators", [])
                            )
                        except (json.JSONDecodeError, OSError):
                            comparators = []
                    summary_dict = {
                        "final_time": summary_obj.final_time,
                        "cell_count": summary_obj.cell_count,
                        "u_magnitude_min": summary_obj.u_magnitude_min,
                        "u_magnitude_max": summary_obj.u_magnitude_max,
                        "u_magnitude_mean": summary_obj.u_magnitude_mean,
                        "u_x_mean": summary_obj.u_x_mean,
                        "u_x_min": summary_obj.u_x_min,
                        "u_x_max": summary_obj.u_x_max,
                        "is_recirculating": summary_obj.is_recirculating,
                    }
                    comparator_suite = evaluate_comparator_suite(
                        comparators, summary_dict,
                    )
                except (ResultsExtractError, OSError, ValueError) as exc:
                    comparator_suite = ComparatorSuiteResult(
                        all_passed=False,
                        individual_results=(),
                        structural_error=f"extractor_error: {exc}",
                    )

    elapsed = time.monotonic() - started
    result: dict[str, Any] = {
        "case": case_dir.name,
        "status": "converged" if converged else "diverged",
        "expected_status": expected,
        "case_id": case_id,
        "cell_count": cell_count,
        "patches": [p.get("name") + "=" + p.get("bc_class", "?") for p in patches],
        "bc_warnings": bc_warnings,
        "cont_err": solve_resp.get("last_continuity_error"),
        "residual_p": solve_resp.get("last_initial_residual_p"),
        "wall_time_s": solve_resp.get("wall_time_s"),
        "smoke_elapsed_s": round(elapsed, 2),
    }
    if comparator_suite is not None:
        # Override status with the comparator verdict for this branch.
        result["status"] = (
            "comparator_pass" if comparator_suite.all_passed
            else "comparator_fail"
        )
        result["comparator_summary"] = format_suite_summary(comparator_suite)
        result["comparator_all_passed"] = comparator_suite.all_passed
        result["comparator_structural_error"] = comparator_suite.structural_error
    return result


def _classify(result: dict[str, Any]) -> str:
    """Return PASS / EXPECTED_FAILURE / FAIL based on declared expected
    status vs actual outcome."""
    status = result["status"]
    expected = result.get("expected_status", "converged")
    if status == "skipped":
        return "SKIP"
    if expected == "expected_failure_v61_104":
        # iter01-style: known to fail until V61-104 ships. Anything
        # OTHER than failure is a surprise (and probably means V61-104
        # secretly landed — investigate).
        if status == "converged":
            return "UNEXPECTED_PASS"
        return "EXPECTED_FAILURE"
    if expected == "analytical_comparator_pass":
        # DEC-V61-106: verdict driven by the comparator suite, not the
        # residual gate. status is set to "comparator_pass" or
        # "comparator_fail" upstream.
        return "PASS" if status == "comparator_pass" else "FAIL"
    # Default: expected to converge.
    return "PASS" if status == "converged" else "FAIL"


def _format_result(result: dict[str, Any], verdict: str) -> str:
    name = result["case"]
    if verdict == "SKIP":
        return f"  ⊘ {name:<10} SKIPPED — {result.get('reason', '')}"
    if verdict == "PASS":
        if result.get("expected_status") == "analytical_comparator_pass":
            return (
                f"  ✓ {name:<10} cells={result.get('cell_count')} "
                f"comparator=PASS wall={result.get('wall_time_s'):.1f}s "
                f"(smoke {result.get('smoke_elapsed_s')}s)\n"
                f"{result.get('comparator_summary', '')}"
            )
        return (
            f"  ✓ {name:<10} cells={result.get('cell_count')} "
            f"cont_err={result.get('cont_err'):.2e} "
            f"wall={result.get('wall_time_s'):.1f}s "
            f"(smoke {result.get('smoke_elapsed_s')}s)"
        )
    if verdict == "EXPECTED_FAILURE":
        return (
            f"  ⚠ {name:<10} EXPECTED_FAILURE ({result['status']}) — "
            f"unblocked by DEC-V61-104"
        )
    if verdict == "UNEXPECTED_PASS":
        return f"  ⁉ {name:<10} UNEXPECTED_PASS — investigate (V61-104 silently landed?)"
    # FAIL
    err = result.get("error", "")
    if result.get("expected_status") == "analytical_comparator_pass":
        return (
            f"  ✗ {name:<10} FAIL (comparator) "
            f"cells={result.get('cell_count')} err={err[:200]}\n"
            f"{result.get('comparator_summary', '')}"
        )
    return (
        f"  ✗ {name:<10} FAIL ({result['status']}) "
        f"cont_err={result.get('cont_err')} err={err[:200]}"
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Run all adversarial cases through the cfd-harness pipeline."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL,
                         help=f"backend URL (default: {DEFAULT_BASE_URL})")
    parser.add_argument("--filter", default="",
                         help="case-name substring filter (e.g. 'iter06')")
    parser.add_argument("--json", action="store_true",
                         help="emit JSON results to stdout instead of human format")
    args = parser.parse_args(argv)

    try:
        _check_backend(args.base_url)
    except SmokeError as exc:
        print(f"backend check failed: {exc}", file=sys.stderr)
        return 2

    cases = sorted(
        d for d in CASES_ROOT.iterdir()
        if d.is_dir() and (args.filter in d.name)
    )
    if not cases:
        print(f"no cases matched filter {args.filter!r} in {CASES_ROOT}", file=sys.stderr)
        return 2

    if not args.json:
        print(f"Running {len(cases)} adversarial case(s) against {args.base_url}\n")

    results: list[dict[str, Any]] = []
    verdicts: list[str] = []
    for case_dir in cases:
        if not args.json:
            print(f"  → {case_dir.name} ...")
        result = run_case(case_dir, args.base_url)
        verdict = _classify(result)
        results.append(result)
        verdicts.append(verdict)
        if not args.json:
            # Move cursor up + clear and print the verdict line.
            sys.stdout.write("\033[F\033[K")
            print(_format_result(result, verdict))

    if args.json:
        json.dump([{"verdict": v, **r} for v, r in zip(verdicts, results)],
                  sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
    else:
        passes = verdicts.count("PASS")
        fails = verdicts.count("FAIL") + verdicts.count("UNEXPECTED_PASS")
        skips = verdicts.count("SKIP")
        expect_fails = verdicts.count("EXPECTED_FAILURE")
        print(
            f"\nResults: {passes} PASS · {expect_fails} EXPECTED_FAILURE · "
            f"{skips} SKIP · {fails} FAIL"
        )

    return 1 if any(v in ("FAIL", "UNEXPECTED_PASS") for v in verdicts) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""V91.3 · V9.D · Manifest → RunArtifactSlice adapter.

Derives a RunArtifactSlice from the existing audit-package manifest dict
shape so the V9 matcher can run against it without requiring the run
pipeline to emit a separate artifact.

Inputs read from manifest:
    - manifest["measurement"]["comparator_verdict"]
        → success (PASS → True · FAIL → False · None → True)
        → convergence_stats.converged (mirrors success)
    - manifest["measurement"]["key_quantities"] + manifest["case"]["gold_standard"]
        → gold_delta.max_abs_pct (max relative deviation across observables)
    - manifest["run"]["outputs"]["solver_log_tail"]
        → convergence_stats.max_iters_reached (regex "reached.*maxIter" or "Maximum iter")
        → convergence_stats.final_iter (last "Time = N" or "Iteration N")

NOT derived (history-array data absent from manifest schema):
    - residuals (per-iter history)
    - forces (per-iter history)

Consequence: 3 of 8 V9 rules dormant in production until manifest schema
widens (R1 residual_oscillation_p · R5 forces_not_converged · R7
residual_plateau_u). Documented as V91 retro Open Q.

V130: this function is pure (reads dict argument, returns dataclass).
No I/O. No network. No subprocess. RS#35 import-allowlist enforced.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .pattern_matcher import (
    ConvergenceStats,
    GoldDelta,
    MatchedCommentary,
    RunArtifactSlice,
    match_advisor_patterns,
)
from .rules import V9_ADVISOR_RULES, V9_RULESET_VERSION


# Regex patterns reading from solver log tail. Conservative — only fire
# when we're confident. Manifest is the only data source; no fallback.
_RE_MAX_ITERS = re.compile(
    r"(?:Maximum iterations reached|reached.*maxIter|maxIter\s+exceeded)",
    re.IGNORECASE,
)
# V91 Codex P2 #4: real OpenFOAM logs often write "Time = 0.998s" with a
# trailing "s" (seconds unit) — keep the unit optional so transient-solver
# logs also yield final_iter.
_RE_TIME_LINE = re.compile(r"^\s*Time\s*=\s*(\d+(?:\.\d+)?)\s*s?\s*$", re.MULTILINE)
_RE_ITER_LINE = re.compile(r"^\s*Iteration\s+(\d+)\b", re.MULTILINE | re.IGNORECASE)


def _parse_final_iter(log_tail: str) -> Optional[int]:
    """Find the last 'Time = N' or 'Iteration N' marker in log_tail.

    OpenFOAM steady solvers emit 'Time = N' (where N is the iteration
    number for SIMPLE/PISO loops). Transient solvers emit floating-point
    timestamps. The final iteration is whichever value appears latest.
    """
    times = [float(m) for m in _RE_TIME_LINE.findall(log_tail)]
    iters = [int(m) for m in _RE_ITER_LINE.findall(log_tail)]
    candidates: List[float] = []
    if times:
        candidates.append(times[-1])
    if iters:
        candidates.append(float(iters[-1]))
    if not candidates:
        return None
    # Take the max — both kinds of marker may co-exist; pick the latest.
    return int(max(candidates))


def derive_slice_from_manifest(manifest: Dict[str, Any]) -> RunArtifactSlice:
    """Build a RunArtifactSlice from audit-package manifest dict shape.

    Tolerates missing fields gracefully — returns a slice with whatever
    data is available. Predicates that need missing fields will return
    None (matcher's documented behavior).
    """
    case = manifest.get("case") or {}
    run = manifest.get("run") or {}
    measurement = manifest.get("measurement") or {}
    outputs = run.get("outputs") or {}

    case_id = case.get("id") or ""
    run_id = run.get("run_id") or ""
    verdict = measurement.get("comparator_verdict")
    log_tail = outputs.get("solver_log_tail") or ""
    key_quantities = measurement.get("key_quantities") or {}

    # V91 Codex P1 #2 fix: success / exit_code are SOLVER-HEALTH signals,
    # not comparator-verdict signals. Real audit manifests carry
    # ``measurement.key_quantities.solver_success`` for the clean-run-vs-crash
    # distinction; comparator_verdict only reports whether output matched
    # gold (physics drift can FAIL on a perfectly clean run). Treating
    # FAIL as a crash falsely fires R3 (RUN_FAILED_NONZERO_EXIT) which
    # claims the solver died, which it didn't.
    solver_success = key_quantities.get("solver_success") if isinstance(key_quantities, dict) else None
    if solver_success is False:
        success = False
        exit_code = 1
    else:
        # solver_success is True OR absent (older manifests lack the field);
        # treat as nominal — R3 will not fire.
        success = True
        exit_code = 0

    # Gold delta — compute max |actual - expected| / |expected| * 100.
    #
    # V91 Codex P1 #3 fix: real audit manifests carry gold_standard.observables
    # as a LIST of {name, ref_value, tolerance, unit, ...} records, and
    # measurement.key_quantities as a SINGLETON record {quantity, value, ...}
    # (one observation per audit pass). Old dict-shaped fixtures
    # {name: ref_value} are accepted as fallback for backward-compat with
    # ad-hoc test fixtures.
    gold_delta: Optional[GoldDelta] = None
    gs = case.get("gold_standard") or {}
    raw_observables = gs.get("observables") if isinstance(gs, dict) else None

    # Normalize observables → list[(name, ref_value)] tuples
    obs_pairs: List[tuple[str, float]] = []
    if isinstance(raw_observables, list):
        for entry in raw_observables:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            ref = entry.get("ref_value")
            if isinstance(name, str) and isinstance(ref, (int, float)) and ref != 0:
                obs_pairs.append((name, float(ref)))
    elif isinstance(raw_observables, dict):
        # Legacy/test-fiction dict shape {name: ref_value}
        for name, ref in raw_observables.items():
            if isinstance(name, str) and isinstance(ref, (int, float)) and ref != 0:
                obs_pairs.append((name, float(ref)))

    if obs_pairs and isinstance(key_quantities, dict):
        # Real-world key_quantities shape: singleton {quantity, value, ...}
        singleton_quantity = key_quantities.get("quantity")
        singleton_value = key_quantities.get("value")
        is_singleton = isinstance(singleton_quantity, str) and isinstance(singleton_value, (int, float))

        max_pct: Optional[float] = None
        for name, ref in obs_pairs:
            actual: Optional[float] = None
            if is_singleton:
                # Match by exact name OR substring prefix (handles
                # "u_centerline[y=0.3750]" matching observable "u_centerline").
                if singleton_quantity == name or singleton_quantity.startswith(name):
                    actual = float(singleton_value)
            else:
                # Multi-key dict shape (test fiction): direct name lookup
                cand = key_quantities.get(name)
                if isinstance(cand, (int, float)):
                    actual = float(cand)
            if actual is None:
                continue
            pct = abs(actual - ref) / abs(ref) * 100.0
            if max_pct is None or pct > max_pct:
                max_pct = pct
        if max_pct is not None:
            gold_delta = GoldDelta(max_abs_pct=max_pct)

    # Convergence stats — parse log_tail. If log_tail missing, stats=None
    # → R2, R6, R8 dormant. Converged status is now decoupled from comparator
    # verdict (per Codex P1 #2 disposition): converged means "solver
    # converged" — a separate concept from "output matches gold".
    convergence_stats: Optional[ConvergenceStats] = None
    if log_tail:
        max_iters_reached = bool(_RE_MAX_ITERS.search(log_tail))
        final_iter = _parse_final_iter(log_tail)
        # converged = solver ran cleanly AND did not hit iteration cap.
        # Comparator verdict is intentionally NOT a factor here.
        converged = success and not max_iters_reached
        if final_iter is not None:
            convergence_stats = ConvergenceStats(
                final_iter=final_iter,
                max_iters_reached=max_iters_reached,
                converged=converged,
                elapsed_seconds=0.0,  # not in manifest yet
            )

    return RunArtifactSlice(
        run_id=run_id,
        case_id=case_id,
        success=success,
        exit_code=exit_code,
        # residuals + forces dormant in V91 scope — see module docstring
        convergence_stats=convergence_stats,
        gold_delta=gold_delta,
    )


def matches_for_manifest(manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Compute matched commentary list for a manifest dict.

    Returns canonical-JSON-ready dicts (not dataclass instances) so the
    caller can serialize to the audit-package zip without further work.
    """
    slice_ = derive_slice_from_manifest(manifest)
    matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
    return [
        {
            "rule_id": m.rule_id,
            "matched_at": m.matched_at,
            "commentary_excerpt": m.commentary_excerpt,
            "provenance": m.provenance,
            "severity": m.severity,
        }
        for m in matches
    ]


def commentary_section_for_manifest(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Build the manifest's top-level ``commentary`` section.

    Schema:
        {
            "version": "v9.0.0",
            "matched": [<MatchedCommentary dicts>, ...]
        }

    Empty matched list is still a valid section (audit-trail completeness:
    a clean run that triggered no rules still records "we checked").
    """
    return {
        "version": V9_RULESET_VERSION,
        "matched": matches_for_manifest(manifest),
    }

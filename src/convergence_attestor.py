"""DEC-V61-038: Pre-extraction convergence attestor A1..A6.

Complements DEC-V61-036b (post-extraction gates G3/G4/G5). Where G3/G4/G5
say "the extracted measurement cannot be trusted because the final-state
fields are broken", A1..A6 say "the run itself never physically converged
even if the solver exited 0".

Composition with gates:
    solver exit 0
    → attestor.attest(log)    → ATTEST_PASS / HAZARD / FAIL
    → if ATTEST_FAIL: contract FAIL (before extraction)
    → else: comparator_gates.check_all_gates(log, vtk)
    → if any gate: contract FAIL
    → else: comparator verdict

Checks:
    A1 solver_exit_clean       — no FOAM FATAL / floating exception  → FAIL
    A2 continuity_floor        — final sum_local ≤ case floor        → HAZARD
    A3 residual_floor          — final initial residuals ≤ target    → HAZARD
    A4 solver_iteration_cap    — pressure loop hit cap repeatedly    → FAIL
    A5 bounding_recurrence     — turbulence bounding in last N iters → HAZARD
    A6 no_residual_progress    — residuals stuck at plateau          → HAZARD

A1/A4 are hard FAIL (solver crashes / caps never acceptable).
A2/A3/A5/A6 default HAZARD; per-case thresholds can promote to FAIL
via knowledge/attestor_thresholds.yaml (not shipped in this DEC —
thresholds live in module constants; future DEC migrates to YAML).

The attestor returns ATTEST_FAIL if ANY check FAILs; ATTEST_HAZARD if
only HAZARD-tier checks fire; else ATTEST_PASS.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Optional

from src.comparator_gates import parse_solver_log

# ---------------------------------------------------------------------------
# Thresholds (per-case override not wired in this DEC; defaults calibrated
# from Codex round-1 physics audit + BFS/DHC/LDC real logs)
# ---------------------------------------------------------------------------

A2_CONTINUITY_FLOOR = 1.0e-4           # incompressible steady; G5 fires at 1e-2
A3_RESIDUAL_FLOOR = 1.0e-3             # initial residual of any field
A4_ITERATION_CAP_PATTERNS = (
    # Capture pressure-solver `No Iterations N`. The pre-text between the
    # solver header and `No Iterations` includes "Initial residual = X,
    # Final residual = Y," — use `.+?` non-greedy and require the full
    # pattern on one line.
    re.compile(r"GAMG:\s+Solving for p,.+?No Iterations\s+(\d+)"),
    re.compile(r"PCG:\s+Solving for p,.+?No Iterations\s+(\d+)"),
    re.compile(r"BiCGStab:.+?No Iterations\s+(\d+)"),
)
A4_ITERATION_CAP_VALUES = (1000, 999, 998)  # solver-reported caps
A4_CONSECUTIVE = 3                     # how many consecutive hits = FAIL

A5_BOUNDING_WINDOW = 50                # last N iterations to inspect
A5_BOUNDING_RECURRENCE_FRAC = 0.30     # ≥ 30% of window bounded = HAZARD

A6_PROGRESS_WINDOW = 50
A6_PROGRESS_DECADE_FRAC = 1.0          # need > 1 decade decay over window


AttestVerdict = Literal["ATTEST_PASS", "ATTEST_HAZARD", "ATTEST_FAIL"]
CheckVerdict = Literal["PASS", "HAZARD", "FAIL"]


@dataclass
class AttestorCheck:
    """Single check outcome (A1..A6)."""

    check_id: str              # "A1" .. "A6"
    concern_type: str          # "SOLVER_CRASH_LOG" / "CONTINUITY_NOT_CONVERGED" / ...
    verdict: CheckVerdict
    summary: str
    detail: str
    evidence: dict = field(default_factory=dict)


@dataclass
class AttestationResult:
    """Aggregate attestation: overall verdict + per-check breakdown.

    `concerns` is the subset of checks whose verdict is HAZARD or FAIL
    (PASS checks are not surfaced in the fixture to avoid clutter).
    """

    overall: AttestVerdict
    checks: list[AttestorCheck] = field(default_factory=list)

    @property
    def concerns(self) -> list[AttestorCheck]:
        return [c for c in self.checks if c.verdict != "PASS"]


# ---------------------------------------------------------------------------
# Per-check regexes (reuse parse_solver_log output where possible)
# ---------------------------------------------------------------------------

_INITIAL_RESIDUAL_RE = re.compile(
    r"Solving for\s+(\w+),\s*Initial residual\s*=\s*([\deE+.\-]+),"
    r"\s*Final residual\s*=\s*([\deE+.\-]+),\s*No Iterations\s+(\d+)"
)

_BOUNDING_LINE_RE = re.compile(r"^\s*bounding\s+(k|epsilon|omega|nuTilda|nut)\b")
# OpenFOAM writes `Time = 123` on its own line AND as `Time = 123s` with
# trailing `s`. Accept either form; trailing whitespace tolerated.
_TIME_STEP_RE = re.compile(r"^Time\s*=\s*[\deE+.\-]+s?\s*$")


def _parse_residual_timeline(log_path: Path) -> dict[str, list[float]]:
    """Extract per-field Initial residual history across all iterations.

    Returns {"Ux": [...], "Uy": [...], "p": [...], "k": [...], "epsilon": [...]}.
    Order preserves the log's iteration order. Used by A3 + A6.
    """
    timeline: dict[str, list[float]] = {}
    with log_path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = _INITIAL_RESIDUAL_RE.search(line)
            if not m:
                continue
            field_name = m.group(1)
            try:
                r0 = float(m.group(2))
            except ValueError:
                continue
            timeline.setdefault(field_name, []).append(r0)
    return timeline


def _parse_iteration_caps(log_path: Path) -> list[int]:
    """Return a list of pressure-solver iteration counts per time step.

    Used by A4 to detect repeated cap-hits.
    """
    counts: list[int] = []
    with log_path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            for pattern in A4_ITERATION_CAP_PATTERNS:
                m = pattern.search(line)
                if m:
                    try:
                        counts.append(int(m.group(1)))
                    except ValueError:
                        pass
                    break
    return counts


def _parse_bounding_lines_per_step(log_path: Path) -> list[set[str]]:
    """Return list of sets, one per `Time =` block, containing fields that
    bounded in that block. Used by A5.
    """
    blocks: list[set[str]] = [set()]
    with log_path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if _TIME_STEP_RE.match(line):
                blocks.append(set())
                continue
            m = _BOUNDING_LINE_RE.match(line)
            if m:
                blocks[-1].add(m.group(1))
    # Drop leading empty block before first `Time =`.
    if blocks and not blocks[0]:
        blocks.pop(0)
    return blocks


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def _check_a1_solver_crash(log_path: Path) -> AttestorCheck:
    stats = parse_solver_log(log_path)
    if stats.fatal_detected:
        return AttestorCheck(
            check_id="A1",
            concern_type="SOLVER_CRASH_LOG",
            verdict="FAIL",
            summary=(
                stats.fatal_lines[0][:240] if stats.fatal_lines
                else "FOAM FATAL detected in log"
            ),
            detail=(
                "DEC-V61-038 A1: solver log contains a FOAM FATAL / IO ERROR / "
                "floating exception marker. Even if the shell exit code was 0 "
                "(which can happen under Docker signal handling), the solver's "
                "own diagnostic says the run aborted abnormally. Any measurement "
                "from this run is unreliable."
            )[:2000],
            evidence={"fatal_lines": stats.fatal_lines[:3]},
        )
    return AttestorCheck(
        check_id="A1", concern_type="SOLVER_CRASH_LOG", verdict="PASS",
        summary="no FOAM FATAL / floating exception in log",
        detail="",
    )


def _check_a2_continuity_floor(log_path: Path) -> AttestorCheck:
    stats = parse_solver_log(log_path)
    sl = stats.final_continuity_sum_local
    if sl is None:
        return AttestorCheck(
            check_id="A2", concern_type="CONTINUITY_NOT_CONVERGED", verdict="PASS",
            summary="no continuity line in log (case may not report it)",
            detail="",
        )
    if sl > A2_CONTINUITY_FLOOR:
        verdict: CheckVerdict = "FAIL" if sl > 1e-2 else "HAZARD"
        return AttestorCheck(
            check_id="A2",
            concern_type="CONTINUITY_NOT_CONVERGED",
            verdict=verdict,
            summary=(f"final sum_local={sl:.3g} > floor {A2_CONTINUITY_FLOOR:.0e}")[:240],
            detail=(
                f"DEC-V61-038 A2: incompressible steady continuity error at "
                f"convergence should be ≤ {A2_CONTINUITY_FLOOR:.0e}. Observed "
                f"final sum_local={sl:.6g}. Values between {A2_CONTINUITY_FLOOR:.0e} "
                f"and 1e-2 are HAZARD (marginal convergence); >1e-2 is FAIL "
                "(DEC-036b G5 also fires)."
            )[:2000],
            evidence={"sum_local": sl, "threshold": A2_CONTINUITY_FLOOR},
        )
    return AttestorCheck(
        check_id="A2", concern_type="CONTINUITY_NOT_CONVERGED", verdict="PASS",
        summary=f"final sum_local={sl:.3g} ≤ {A2_CONTINUITY_FLOOR:.0e}",
        detail="",
    )


def _check_a3_residual_floor(log_path: Path) -> AttestorCheck:
    timeline = _parse_residual_timeline(log_path)
    if not timeline:
        return AttestorCheck(
            check_id="A3", concern_type="RESIDUALS_ABOVE_TARGET", verdict="PASS",
            summary="no residual lines parsed from log",
            detail="",
        )
    offenders: dict[str, float] = {}
    for field_name, history in timeline.items():
        last = history[-1]
        if last > A3_RESIDUAL_FLOOR:
            offenders[field_name] = last
    if offenders:
        sorted_off = sorted(offenders.items(), key=lambda kv: -kv[1])
        summary = (
            f"final residuals above {A3_RESIDUAL_FLOOR:.0e}: "
            + ", ".join(f"{k}={v:.3g}" for k, v in sorted_off[:3])
        )[:240]
        return AttestorCheck(
            check_id="A3", concern_type="RESIDUALS_ABOVE_TARGET",
            verdict="HAZARD",
            summary=summary,
            detail=(
                "DEC-V61-038 A3: at convergence, SIMPLE/PISO initial residuals "
                f"should be ≤ {A3_RESIDUAL_FLOOR:.0e}. Fields listed above have "
                "final-iteration Initial residuals exceeding that floor. This "
                "may be physically expected for some cases (impinging_jet "
                "p_rgh, RBC oscillatory modes) — HAZARD not FAIL until a "
                "per-case override promotes it."
            )[:2000],
            evidence={"offenders": offenders, "threshold": A3_RESIDUAL_FLOOR},
        )
    return AttestorCheck(
        check_id="A3", concern_type="RESIDUALS_ABOVE_TARGET", verdict="PASS",
        summary=f"all residuals ≤ {A3_RESIDUAL_FLOOR:.0e}",
        detail="",
    )


def _check_a4_iteration_cap(log_path: Path) -> AttestorCheck:
    counts = _parse_iteration_caps(log_path)
    if not counts:
        return AttestorCheck(
            check_id="A4", concern_type="SOLVER_ITERATION_CAP", verdict="PASS",
            summary="no pressure solver iteration counts in log",
            detail="",
        )
    consecutive = 0
    for c in counts:
        if c in A4_ITERATION_CAP_VALUES or c >= 1000:
            consecutive += 1
            if consecutive >= A4_CONSECUTIVE:
                return AttestorCheck(
                    check_id="A4", concern_type="SOLVER_ITERATION_CAP",
                    verdict="FAIL",
                    summary=(
                        f"pressure solver hit {c} iterations in "
                        f"≥ {A4_CONSECUTIVE} consecutive steps"
                    )[:240],
                    detail=(
                        "DEC-V61-038 A4: pressure-velocity solver loop is "
                        f"hitting its iteration cap (~{c}) in at least "
                        f"{A4_CONSECUTIVE} consecutive outer iterations. "
                        "SIMPLE/PISO coupling has effectively failed — the "
                        "solver is burning CPU without reducing the residual. "
                        "Hard FAIL."
                    )[:2000],
                    evidence={
                        "consecutive_cap_hits": consecutive,
                        "final_cap_value": c,
                        "total_steps": len(counts),
                    },
                )
        else:
            consecutive = 0
    return AttestorCheck(
        check_id="A4", concern_type="SOLVER_ITERATION_CAP", verdict="PASS",
        summary=f"pressure solver peaked at {max(counts)} iterations",
        detail="",
    )


def _check_a5_bounding_recurrence(log_path: Path) -> AttestorCheck:
    blocks = _parse_bounding_lines_per_step(log_path)
    if len(blocks) < 5:
        # Too few time steps to judge recurrence.
        return AttestorCheck(
            check_id="A5", concern_type="BOUNDING_RECURRENT", verdict="PASS",
            summary=f"only {len(blocks)} time-step blocks parsed",
            detail="",
        )
    window = blocks[-A5_BOUNDING_WINDOW:]
    if not window:
        return AttestorCheck(
            check_id="A5", concern_type="BOUNDING_RECURRENT", verdict="PASS",
            summary="no final-window blocks",
            detail="",
        )
    per_field_frac: dict[str, float] = {}
    for field_name in ("k", "epsilon", "omega", "nuTilda", "nut"):
        bounded_count = sum(1 for b in window if field_name in b)
        if bounded_count == 0:
            continue
        frac = bounded_count / len(window)
        per_field_frac[field_name] = frac
    offenders = {k: v for k, v in per_field_frac.items()
                 if v >= A5_BOUNDING_RECURRENCE_FRAC}
    if offenders:
        top = max(offenders.items(), key=lambda kv: kv[1])
        return AttestorCheck(
            check_id="A5", concern_type="BOUNDING_RECURRENT",
            verdict="HAZARD",
            summary=(
                f"{top[0]} bounded in {top[1]*100:.0f}% of last "
                f"{len(window)} iterations (threshold "
                f"{A5_BOUNDING_RECURRENCE_FRAC*100:.0f}%)"
            )[:240],
            detail=(
                "DEC-V61-038 A5: turbulence field is being clipped in a large "
                f"fraction of the FINAL {len(window)} iterations. Healthy "
                "convergence shows bounding events in early transients then "
                "stabilises. Recurrent bounding in the tail indicates the "
                "solution never settles — 'converged' residuals are an artefact "
                "of clipping, not physical equilibrium."
            )[:2000],
            evidence={"per_field_fraction": per_field_frac, "window": len(window)},
        )
    return AttestorCheck(
        check_id="A5", concern_type="BOUNDING_RECURRENT", verdict="PASS",
        summary=(
            f"bounding fractions in last {len(window)} iters: "
            + ", ".join(f"{k}={v:.0%}" for k, v in per_field_frac.items())
            if per_field_frac else f"no bounding in last {len(window)} iters"
        )[:240],
        detail="",
    )


def _check_a6_no_progress(log_path: Path) -> AttestorCheck:
    timeline = _parse_residual_timeline(log_path)
    if not timeline:
        return AttestorCheck(
            check_id="A6", concern_type="NO_RESIDUAL_PROGRESS", verdict="PASS",
            summary="no residuals parsed",
            detail="",
        )
    offenders: dict[str, dict[str, float]] = {}
    for field_name, history in timeline.items():
        if len(history) < A6_PROGRESS_WINDOW:
            continue
        window = history[-A6_PROGRESS_WINDOW:]
        lo = min(window)
        hi = max(window)
        if lo <= 0 or hi <= 0:
            continue
        # A6 only fires when residuals are STUCK AT A HIGH PLATEAU — i.e.,
        # still above the A3 floor. If residuals have already decayed to
        # convergence (< 1e-3), a small decade-range in the tail is just
        # machine-noise fluctuation, not "stuck". Guard against this
        # false positive (caught on LDC: Ux plateaued at 1e-5 with 0.02
        # decades range — that's converged, not stuck).
        if hi < A3_RESIDUAL_FLOOR:
            continue
        decades = math_log10(hi / lo) if hi > lo else 0.0
        if decades < A6_PROGRESS_DECADE_FRAC:
            offenders[field_name] = {"decades": decades, "lo": lo, "hi": hi}
    if offenders:
        worst = min(offenders.items(), key=lambda kv: kv[1]["decades"])
        return AttestorCheck(
            check_id="A6", concern_type="NO_RESIDUAL_PROGRESS",
            verdict="HAZARD",
            summary=(
                f"{worst[0]} residual range over last "
                f"{A6_PROGRESS_WINDOW} iters: "
                f"{worst[1]['lo']:.2e} – {worst[1]['hi']:.2e} "
                f"({worst[1]['decades']:.2f} decades)"
            )[:240],
            detail=(
                "DEC-V61-038 A6: initial residuals for the fields listed "
                f"above did not decay > {A6_PROGRESS_DECADE_FRAC:.1f} decade(s) "
                f"over the last {A6_PROGRESS_WINDOW} iterations. Solver is "
                "stuck at a plateau; any scalar extracted from this 'converged' "
                "state is physically ambiguous."
            )[:2000],
            evidence={"offenders": offenders, "window": A6_PROGRESS_WINDOW},
        )
    return AttestorCheck(
        check_id="A6", concern_type="NO_RESIDUAL_PROGRESS", verdict="PASS",
        summary="all residual histories show > 1 decade decay in tail window",
        detail="",
    )


def math_log10(x: float) -> float:
    """log10 with a zero-guard. Inlined to avoid a dependency in this module."""
    import math
    if x <= 0:
        return 0.0
    return math.log10(x)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def attest(log_path: Optional[Path]) -> AttestationResult:
    """Run A1..A6 against a solver log; aggregate into an AttestationResult.

    When log_path is None or absent, returns ATTEST_PASS with no checks
    (attestor is a log-based tool; absent log = no signal).
    """
    if log_path is None or not log_path.is_file():
        return AttestationResult(overall="ATTEST_PASS", checks=[])

    checks = [
        _check_a1_solver_crash(log_path),
        _check_a2_continuity_floor(log_path),
        _check_a3_residual_floor(log_path),
        _check_a4_iteration_cap(log_path),
        _check_a5_bounding_recurrence(log_path),
        _check_a6_no_progress(log_path),
    ]

    has_fail = any(c.verdict == "FAIL" for c in checks)
    has_hazard = any(c.verdict == "HAZARD" for c in checks)
    if has_fail:
        overall: AttestVerdict = "ATTEST_FAIL"
    elif has_hazard:
        overall = "ATTEST_HAZARD"
    else:
        overall = "ATTEST_PASS"

    return AttestationResult(overall=overall, checks=checks)


def check_to_audit_concern_dict(c: AttestorCheck) -> dict[str, Any]:
    """Serialize a non-PASS AttestorCheck as an audit_concerns[] entry."""
    return {
        "concern_type": c.concern_type,
        "summary": c.summary,
        "detail": c.detail,
        "decision_refs": ["DEC-V61-038"],
        "evidence": c.evidence,
        "attestor_check_id": c.check_id,
        "attestor_verdict": c.verdict,
    }

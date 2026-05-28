"""V9 convergence-ruleset BEHAVIORAL eval (Stage-2 increment 2a).

Per `.planning/strategic/stage_goal_spec_v0.1_2026-05-28.md` §4: this is the
case-level *behavioral* rung of the eval ladder — the one that was missing.

How this DIFFERS from `tests/test_v9_pattern_matcher.py` (and why it is not
redundant):

  - test_v9_pattern_matcher.py `TestPositiveCases` assert `any(m.rule_id ==
    "RULE_X" ...)` — they confirm rule X *fires*, but say NOTHING about the
    other 8 rules. `TestNegativeCases` pin one rule's boundary true-negative
    at a time.
  - This file asserts the **COMPLETE firing set** for each labeled fixture:
    rule X fires AND every other rule behaves as specified. A regression that
    made, say, R8 (healthy) spuriously co-fire on an oscillating run would
    pass every existing `any()`-based positive test — but fail here.

That is the difference between a benchmark that *documents* expected behavior
and one that *adjudicates* it (Blueprint v4: "benchmark负责裁决"). The
adjudicator's teeth are the **set equality** below: actual_fired == expected,
which catches both false-negatives (missing fire) and — the genuinely new
coverage — cross-rule **false-positives**.

Each fixture's `expected` set is labeled from the predicate logic in
`ui/backend/services/v9_advisor/rules.py` (NOT snapshotted from whatever the
matcher happens to emit). The CO-FIRING fixtures (F5–F8) are the highest-value
rows: they pin legitimate two-rule semantics that no other test specifies —
e.g. a run that converges cleanly but lands 8.2% off the gold benchmark
SHOULD fire both R4 (gold-delta) and R8 (healthy-convergence); they are not
mutually exclusive.

Pure functions over synthetic `RunArtifactSlice` inputs → LLM-offline and
deterministic by construction (no real solve, no I/O).
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from ui.backend.services.v9_advisor import (
    ConvergenceStats,
    ForcesEntry,
    GoldDelta,
    RunArtifactSlice,
    V9_ADVISOR_RULES,
    match_advisor_patterns,
)

# Full rule IDs (1:1 with _PREDICATES_BY_ID in rules.py).
R1 = "RESIDUAL_OSCILLATION_P_V9_R1"
R2 = "MAX_ITERS_REACHED_V9_R2"
R3 = "RUN_FAILED_NONZERO_EXIT_V9_R3"
R4 = "GOLD_DELTA_EXCEEDS_5_PCT_V9_R4"
R5 = "FORCES_NOT_CONVERGED_V9_R5"
R6 = "SLOW_CONVERGENCE_V9_R6"
R7 = "RESIDUAL_PLATEAU_U_V9_R7"
R8 = "HEALTHY_CONVERGENCE_V9_R8"
R9 = "RESIDUAL_DIVERGENCE_V9_R9"

ALL_RULE_IDS = frozenset({R1, R2, R3, R4, R5, R6, R7, R8, R9})

# A clean, healthy converged run: p & U residuals monotonically decreasing
# (8 pts), converged at iter 800, forces flat (<0.1% drift), gold-delta 0.75%.
# Note: U has only 8 samples, so R7 (needs last-20) can never fire from base —
# fixtures that test R7 supply a 20-point U history explicitly.
def _base_healthy() -> RunArtifactSlice:
    decreasing = [1e-2, 5e-3, 2.5e-3, 1e-3, 5e-4, 2.5e-4, 1e-4, 5e-5]
    return RunArtifactSlice(
        run_id="R-OK-1",
        case_id="lid_driven_cavity",
        success=True,
        exit_code=0,
        residuals={"p": list(decreasing), "U": list(decreasing)},
        forces=[
            ForcesEntry(iteration=i, Cd=0.95 + (i % 2) * 0.001, Cl=0.0, Cm=0.0)
            for i in range(20)
        ],
        convergence_stats=ConvergenceStats(
            final_iter=800, max_iters_reached=False, converged=True, elapsed_seconds=28.0
        ),
        gold_delta=GoldDelta(max_abs_pct=0.75),
    )


def _with(**overrides) -> RunArtifactSlice:
    return RunArtifactSlice(**{**_base_healthy().__dict__, **overrides})


def _residuals(p=None, u=None) -> dict:
    base = _base_healthy().residuals
    return {
        "p": list(p) if p is not None else list(base["p"]),
        "U": list(u) if u is not None else list(base["U"]),
    }


@dataclass(frozen=True)
class EvalCase:
    label: str
    slice_: RunArtifactSlice
    expected: frozenset[str]
    rationale: str


# Force history that drifts ~18% in the last 10 iters (Cd ramps 0.5 → 1.45).
_DRIFTY_FORCES = [ForcesEntry(iteration=i, Cd=0.5 + i * 0.05, Cl=0.0, Cm=0.0) for i in range(20)]
# U residual stuck at ~1.5e-3 (variation < 2%, magnitude > 1e-4 floor) → plateau.
_U_PLATEAU = [1.5e-3 + (i % 3 - 1) * 1e-6 for i in range(20)]
# p oscillating about the mean with > 0.3 amplitude ratio.
_OSC_P = [1e-2, 5e-3, 1.2e-2, 4e-3, 1.3e-2, 3.5e-3, 1.4e-2, 3e-3]
# p climbing monotonically past O(1) → unambiguous blow-up.
_DIVERGING_P = [0.5, 2.0, 10.0, 50.0]


EVAL_CASES: list[EvalCase] = [
    # ---- single-rule discrimination (exact set == one rule) --------------
    EvalCase(
        "healthy",
        _base_healthy(),
        frozenset({R8}),
        "clean converged run fires EXACTLY the healthy marker — nothing else",
    ),
    EvalCase(
        "oscillating_p",
        _with(residuals=_residuals(p=_OSC_P)),
        frozenset({R1}),
        "oscillating p → R1; R8 must stay silent (p not monotonically decreasing)",
    ),
    EvalCase(
        "max_iters_not_converged",
        _with(
            convergence_stats=ConvergenceStats(
                final_iter=5000, max_iters_reached=True, converged=False, elapsed_seconds=60.0
            )
        ),
        frozenset({R2}),
        "hit max iters without converging → R2 only; R6/R8 require converged=True",
    ),
    EvalCase(
        "u_plateau_not_converged",
        _with(
            residuals=_residuals(u=_U_PLATEAU),
            convergence_stats=ConvergenceStats(
                final_iter=900, max_iters_reached=False, converged=False, elapsed_seconds=40.0
            ),
        ),
        frozenset({R7}),
        "U stuck on a plateau, run not converged → R7 only; R8 silent (converged=False)",
    ),
    # ---- legitimate CO-FIRING (the semantics no other test pins) ---------
    EvalCase(
        "converged_but_off_gold",
        _with(gold_delta=GoldDelta(max_abs_pct=8.2)),
        frozenset({R4, R8}),
        "converged cleanly BUT 8.2% off the benchmark → R4 AND R8 (not exclusive)",
    ),
    EvalCase(
        "diverged_and_crashed",
        _with(
            success=False,
            exit_code=1,
            residuals=_residuals(p=_DIVERGING_P),
            convergence_stats=ConvergenceStats(
                final_iter=3, max_iters_reached=False, converged=False, elapsed_seconds=1.5
            ),
        ),
        frozenset({R3, R9}),
        "blow-up that also exits nonzero → R3 (crash) AND R9 (divergence)",
    ),
    EvalCase(
        "converged_but_slow",
        _with(
            convergence_stats=ConvergenceStats(
                final_iter=6000, max_iters_reached=False, converged=True, elapsed_seconds=240.0
            )
        ),
        frozenset({R6, R8}),
        "converged healthily but took 6000 iters → R6 AND R8",
    ),
    EvalCase(
        "converged_but_forces_drift",
        _with(forces=_DRIFTY_FORCES),
        frozenset({R5, R8}),
        "residuals converged (R8) but force coefficients still drifting (R5)",
    ),
]


def _fired_rule_ids(slice_: RunArtifactSlice) -> frozenset[str]:
    return frozenset(m.rule_id for m in match_advisor_patterns(slice_, V9_ADVISOR_RULES))


@pytest.mark.parametrize("case", EVAL_CASES, ids=lambda c: c.label)
def test_v9_ruleset_fires_exactly_the_expected_set(case: EvalCase) -> None:
    """The adjudicator: actual fired set must EQUAL the labeled expected set.

    Set equality (not `any`) is what catches cross-rule false-positives — a
    rule firing when it should not — which the per-rule positive/negative
    tests structurally cannot see.
    """
    fired = _fired_rule_ids(case.slice_)
    missing = case.expected - fired
    unexpected = fired - case.expected
    assert fired == case.expected, (
        f"[{case.label}] firing-set mismatch.\n"
        f"  rationale : {case.rationale}\n"
        f"  expected  : {sorted(case.expected)}\n"
        f"  actual    : {sorted(fired)}\n"
        f"  missing   : {sorted(missing)} (expected to fire, did not)\n"
        f"  unexpected: {sorted(unexpected)} (fired, should be silent — "
        f"cross-rule false positive)"
    )


def test_eval_exercises_every_rule() -> None:
    """Coverage canary: the union of expected sets must touch all 9 rules.

    Without this, a rule could silently lose adjudication coverage when a
    fixture is removed — and the suite would still be green while the
    benchmark stopped testing that rule.
    """
    covered = frozenset().union(*(c.expected for c in EVAL_CASES))
    missing = ALL_RULE_IDS - covered
    assert not missing, (
        f"behavioral eval does not exercise rule(s) {sorted(missing)}; add a "
        f"fixture whose expected set includes them, or this adjudicator has a "
        f"blind spot."
    )


def test_eval_includes_co_firing_cases() -> None:
    """Pin that the eval tests cross-rule SEMANTICS, not just isolated rules.

    The whole point of a set-equality adjudicator (vs the existing `any()`
    tests) is multi-rule discrimination. If every fixture were a single-rule
    set, this file would add little over test_v9_pattern_matcher.py.
    """
    co_firing = [c for c in EVAL_CASES if len(c.expected) >= 2]
    assert len(co_firing) >= 3, (
        f"only {len(co_firing)} co-firing fixtures; the adjudicator's unique "
        f"value is pinning legitimate multi-rule firings — keep >=3"
    )

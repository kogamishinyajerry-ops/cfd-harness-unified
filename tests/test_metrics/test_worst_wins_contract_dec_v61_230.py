"""DEC-V61-230 · single contract source-of-truth for the TWO worst-wins reducers.

This is the ONE cross-package test that pins the worst-wins trust-verdict contract
shared by BOTH reducers and makes any future SILENT divergence fail CI:

  - Reducer A: src.metrics.trust_gate.reduce_reports   (Plane.EVALUATION, 3-state)
  - Reducer B: cfdtrust.audit.report._overall_status   (standalone verifier, 5-state)

Per DEC-V61-230 the two reducers are deliberately NOT physically merged: cfdtrust must
stay a ZERO-src-dependency portable verifier so signed audit packages replay air-gapped
(system-architect consult 2026-06-07 — a single shared `src.*` import would break that
invariant + byte-repro portability, and .importlinter only scopes `src.*` so it would not
even catch the breakage). Instead THIS TEST is the single behavioural source of truth:

  (1) AGREEMENT on the shared closed alphabet {PASS,WARN,FAIL}: on every multiset of those
      three, Reducer A and Reducer B return the same verdict. A fence/fix applied to ONE
      reducer that changes a verdict on a shared-alphabet input now turns this test RED —
      this is the machine guard that kills the roadmap's "围栏只补一处会静默漏" risk.
  (2) DIVERGENCE cells (empty set, BLOCKED/MOCKED tiers, unknown/missing status) are pinned
      as KNOWN + INTENTIONAL with rationale + source lines, so they are documented, never
      silent. Whoever touches either reducer must consciously update this contract.

This file is TEST code; it bridges both packages only to enforce the contract and is NOT
part of either shipped wheel — cfdtrust's standalone invariant is preserved.
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

import pytest

# Test-only bridge to the standalone cfdtrust verifier (NOT a runtime/package import;
# this file ships in neither wheel, so cfdtrust's zero-src-dependency contract holds).
# APPEND (not insert(0)): resolves the unambiguous `cfdtrust` package WITHOUT shadowing
# the repo's top-level `tools/` / `cases/` for any later bare import in a shared session
# (ui/backend/audit/ also contains tools/ + cases/).
_AUDIT_ROOT = Path(__file__).resolve().parents[2] / "ui" / "backend" / "audit"
if str(_AUDIT_ROOT) not in sys.path:
    sys.path.append(str(_AUDIT_ROOT))

from src.metrics import MetricClass, MetricReport, MetricStatus  # Reducer A inputs
from src.metrics.trust_gate import reduce_reports  # Reducer A

from cfdtrust.audit.report import _overall_status  # Reducer B (standalone verifier)


def _A(statuses):
    """Drive Reducer A on a list of 3-state MetricStatus → uppercase verdict string."""
    reports = [
        MetricReport(name=f"m{i}", metric_class=MetricClass.RESIDUAL, status=s)
        for i, s in enumerate(statuses)
    ]
    return reduce_reports(reports).overall.value.upper()


def _B(statuses):
    """Drive Reducer B on the SAME statuses (as a gates dict) → verdict string."""
    gates = {f"g{i}": {"status": s.value.upper()} for i, s in enumerate(statuses)}
    return _overall_status(gates)


_SHARED = [MetricStatus.PASS, MetricStatus.WARN, MetricStatus.FAIL]
_SHARED_COMBOS = [
    c for n in (1, 2, 3) for c in itertools.combinations_with_replacement(_SHARED, n)
]


# ---------- (1) AGREEMENT on the shared closed alphabet — the anti-silent-divergence guard ----------
@pytest.mark.parametrize("combo", _SHARED_COMBOS)
def test_shared_alphabet_reducers_agree(combo):
    """CONTRACT SSOT: on any non-empty multiset of {PASS,WARN,FAIL}, A and B agree.
    A future change making the two diverge on a shared-alphabet input fails HERE."""
    a, b = _A(list(combo)), _B(list(combo))
    assert a == b, (
        f"worst-wins divergence on {[s.value for s in combo]}: A={a} B={b} "
        f"— DEC-V61-230 shared-alphabet contract broken (a fence touched one reducer "
        f"but not the other)."
    )


@pytest.mark.parametrize(
    "combo,expected",
    [
        ((MetricStatus.PASS,), "PASS"),
        ((MetricStatus.WARN,), "WARN"),
        ((MetricStatus.FAIL,), "FAIL"),
        ((MetricStatus.PASS, MetricStatus.WARN), "WARN"),
        ((MetricStatus.PASS, MetricStatus.FAIL), "FAIL"),
        ((MetricStatus.WARN, MetricStatus.FAIL), "FAIL"),
        ((MetricStatus.PASS, MetricStatus.WARN, MetricStatus.FAIL), "FAIL"),
    ],
)
def test_shared_alphabet_exact_worst_wins_verdict(combo, expected):
    """Pin the exact worst-wins precedence FAIL > WARN > PASS on the shared alphabet,
    asserted identically against BOTH reducers."""
    assert _A(list(combo)) == expected
    assert _B(list(combo)) == expected


# ---------- (2) DIVERGENCE cells — pinned KNOWN + INTENTIONAL (documented, never silent) ----------
def test_divergence_cell_1_empty_set():
    """Empty input: A=PASS (vacuous — trust_gate.py:368-369 + module docstring) vs
    B=WARN (report.py:34 fallthrough; `statuses == {"PASS"}` is False for empty set).
    Opposite default-safety polarity — INTENTIONAL, pinned so neither drifts silently."""
    assert _A([]) == "PASS"
    assert _overall_status({}) == "WARN"


def test_divergence_cells_2to4_B_richer_tiers_A_cannot_represent():
    """B carries BLOCKED/MOCKED honesty tiers + conservative unknown→WARN + missing→FAIL;
    A's 3-state enum cannot represent them. INTENTIONAL asymmetry: B is the LIVE verifier
    (feeds schema-validated trust_report.json, 5-state enum), A's inputs are physically
    3-state. Pinned on the B side (report.py:23-34)."""
    assert _overall_status({"g": {"status": "BLOCKED"}}) == "BLOCKED"
    assert _overall_status({"g": {"status": "MOCKED"}}) == "MOCKED"
    assert _overall_status({"g": {"status": "SKIPPED"}}) == "WARN"  # unknown → WARN catch-all
    assert _overall_status({"g": {}}) == "FAIL"  # missing status key → FAIL default
    # B precedence FAIL > BLOCKED > MOCKED > WARN > PASS
    assert _overall_status({"a": {"status": "PASS"}, "b": {"status": "BLOCKED"}}) == "BLOCKED"
    assert _overall_status({"a": {"status": "WARN"}, "b": {"status": "MOCKED"}}) == "MOCKED"
    assert _overall_status({"a": {"status": "BLOCKED"}, "b": {"status": "MOCKED"}}) == "BLOCKED"


def test_reducer_A_closed_three_state_and_documented_fail_open():
    """Pin A's closed 3-state contract. A only inspects FAIL then WARN buckets, so any
    out-of-enum status is non-blocking (the documented fail-open). It is UNREACHABLE in
    production today because A's MetricStatus enum (base.py:37-42) physically holds only
    pass/warn/fail (DEC-V61-230 §live-impact: A's output is also dormant — no production
    consumer). Pinned to catch any future widening of A's input vocabulary that would
    spring the trap (at which point A MUST be made fail-closed — a separate DEC decision)."""
    assert {s.value for s in MetricStatus} == {"pass", "warn", "fail"}
    assert _A([]) == "PASS"  # vacuous PASS — A's documented empty-set default

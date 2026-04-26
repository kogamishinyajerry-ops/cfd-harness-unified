---
decision_id: DEC-V61-071
title: Wire load_tolerance_policy into task_runner._build_trust_gate_report (P1 Metrics & Trust tail)
status: ACCEPTED_R2_APPROVE_WITH_COMMENTS (2026-04-26 · trust-core boundary item · R1 CHANGES_REQUIRED → verbatim fix → R2 APPROVE_WITH_COMMENTS · 1 non-blocking test-fidelity comment addressed in follow-up commit · 17/17 trust-gate + 132/132 broader suite pass)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-04-26
authored_under: 治理收口 2026-04-26 → 2026-05-03 anchor session · Workflow B
parent_retro: RETRO-V61-004 §"Canonical Follow-up #1"
parent_session: https://www.notion.so/34ec68942bed8105a5f2f961241cd32b
supersedes_gate: none
autonomous_governance: false
external_gate_self_estimated_pass_rate: 0.85
notion_sync_status: pending
codex_tool_report_path: reports/codex_tool_reports/dec_v61_071_round1.md (R1 CHANGES_REQUIRED) + reports/codex_tool_reports/dec_v61_071_round2.md (R2 pending)
codex_round_arc:
  R1_initial_paauhtgaiah: failed (usage limit) — retry on kogamishinyajerry
  R1_kogamishinyajerry: failed (usage limit · cx-auto Score-vs-actual drift)
  R1_picassoer651: SUCCESS (61% Score) → CHANGES_REQUIRED · F#1 MED slug resolution + F#2 LOW lazy load
  R2_picassoer651: APPROVE_WITH_COMMENTS · 0 blocking findings · 1 non-blocking test-fidelity comment (real-whitelist regression test added in follow-up)
r1_findings_summary:
  F1_MED_slug_resolution: "TaskSpec.name often display title not slug → load_tolerance_policy silently misses real CaseProfiles. Fix: _resolve_case_slug_for_policy helper walks knowledge/whitelist.yaml name↔id mapping."
  F2_LOW_lazy_load: "Loader was eager (filesystem I/O on attestation-only and no-input paths). Fix: moved load call inside `if comparison is not None:` branch."
r1_fix_commit: f0f0f80
---

# DEC-V61-071 · load_tolerance_policy wiring (P1 Metrics & Trust tail)

## Why

RETRO-V61-004 §"Canonical Follow-up #1" identified that the P1 Metrics &
Trust arc completed without exercising `load_tolerance_policy` in the
production path. The recommended next-step was to add the call to
`task_runner._build_trust_gate_report` so policy dispatch runs in
production before P1-T4 (ObservableDef formalization) unblocks
per-observable threshold application.

This was the **trust-core P1 tail item** originally numbered V61-057 in
the kickoff prompt + RETRO-V61-004 hard-constraints list. Line-B work
landed at V61-057 (DHC multidim), V61-058 (NACA0012 multidim), V61-061
(NACA mesh refinement), V61-067 (BFS) which reserved V61-068/069/070 for
follow-ups. Renumbered to **V61-071** by the 治理收口 2026-04-26 anchor
session; no semantic change to the deliverable.

## Decision

Add `load_tolerance_policy(task_name)` call inside
`_build_trust_gate_report` and stamp the loaded policy's observable
keys into the comparison report's provenance under
`tolerance_policy_observables`. Verdict semantics are unchanged today —
the comparator already ran with its own threshold. The provenance trail
makes the dispatch path observable so the eventual ObservableDef
migration (P1-T4) has live test coverage.

Failure modes:
- **Missing CaseProfile YAML** → empty observables list, no warning
  (fail-soft per `case_profile_loader` design).
- **Malformed CaseProfile** (`CaseProfileError`) → empty observables +
  WARNING log, run continues.

## Impact

| Metric | Value |
| --- | --- |
| Files modified | 2 (`src/task_runner.py` +20 LOC, `tests/test_task_runner_trust_gate.py` +113 LOC) |
| Total LOC | +133 / -0 |
| Tests added | 3 (success path, missing profile, malformed profile) |
| Test suite | 118/118 pass (P1 trust-gate + metrics + task_runner) |
| ADR-001 plane contract | KEPT (no new cross-plane import; src.metrics already in scope) |
| Self-pass-rate estimate (pre-Codex) | 0.85 (stair-anchor floor per RETRO-V61-001 Q4 + RETRO-V61-004 R5 ADJUST) |

## Trust-core boundary classification

`task_runner.py` is **not** in the strict trust-core 5 modules list
(gold_standards / auto_verifier / convergence_attestor / audit_package /
foam_agent_adapter), but the change touches the trust-gate verdict
construction path. Per kickoff Workflow B explicit ruling, this item is
**inside the trust-core boundary** and Codex review is **mandatory**.

## Codex review status

Codex review is **queued post-DEC-V61-072 sampling audit**. Single
ChatGPT account quota (the kogamishinyajerry account at 100% Score)
must serve both audits sequentially. Codex round 1 fires immediately
after DEC-V61-072 lands.

Pre-Codex self-review checklist (per
`docs/methodology/pre_codex_self_review_checklist.md`):

- [x] Public API surface unchanged (function signature stable)
- [x] No new cross-plane imports
- [x] No `Optional[T]` widened to `T | None` (typing convention preserved)
- [x] Test coverage ≥ existing baseline (118 → 118+3 = 121 pass)
- [x] Failure modes test-covered (missing profile, malformed profile)
- [x] Logging at WARNING level for `CaseProfileError` (not silent)

## Branch + commits

Direct-to-main per §10 治理降级 — but trust-core boundary triggers
mandatory Codex review post-land. If Codex returns CHANGES_REQUIRED,
fix commits attach to this DEC.

- HEAD: `3296ae6` on `origin/main`
- Single commit: `feat(task_runner): wire load_tolerance_policy into _build_trust_gate_report (DEC-V61-071 · P1 tail)`
- Pre-commit: import-linter ADR-001 PASSED · dual-track isolation guard PASSED

## Counter v6.1

`autonomous_governance_counter_v61` does NOT advance — this DEC is
flagged `autonomous_governance: false` because Codex review is
mandatory (trust-core boundary) and the trio-gate (G-9 + G-1 + VCP) is
still external-pending.

## Related decisions

- **Upstream**: RETRO-V61-004 (P1 arc retro · §Canonical Follow-up #1)
- **Sibling**: DEC-V61-054 (P1-T1 MetricsRegistry MVP · CHANGES_REQUIRED→APPROVE_WITH_COMMENTS)
- **Sibling**: DEC-V61-055 (P1-T2+T3 TrustGate reducer + tolerance_policy loader)
- **Sibling**: DEC-V61-056 (P1-T5 task_runner trust_gate report)
- **Sibling**: DEC-V61-072 (Sampling Audit Anchor · First Execution · co-lands today)
- **Downstream**: P1-T4 ObservableDef formalization (still blocked on KOM Draft → Active)

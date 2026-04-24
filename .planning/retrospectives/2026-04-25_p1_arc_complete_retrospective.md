---
retrospective_id: RETRO-V61-004
timestamp: 2026-04-25T05:20 local
scope: P1 Metrics & Trust Layer arc (DEC-V61-054 through DEC-V61-056). Counter progression 40 → 43. Triggered by RETRO-V61-001 cadence rules #3 (V61-054 R1 CHANGES_REQUIRED incident retro) + phase-close pattern for a coherent 5-task milestone (P1-T1/T2/T3/T3b/T5 all CLEAN CLOSE).
status: LANDING — follows DEC-V61-056 close.
author: Claude Opus 4.7 (1M context)
decided_by: Claude (self-executed under 全权自动推进 mode; user sign-off on next touch)
notion_sync_status: synced 2026-04-25T05:25 · Status=Accepted (page_id=34cc6894-2bed-818d-99ba-df034e8a9774, URL=https://www.notion.so/RETRO-V61-004-P1-Metrics-Trust-Layer-arc-complete-5-tasks-3-DECs-4-Codex-rounds-34cc68942bed818d99badf034e8a9774)
---

# P1 Metrics & Trust Layer · Complete Arc Retrospective

## Purpose

The Pivot Charter (2026-04-22) redirected the project from "multi-case
benchmark" to "CFD Harness OS — Case Intelligence Layer." §7 of the
charter defined P1 Metrics & Trust Layer as the first post-pivot
deliverable: a unified PASS/WARN/FAIL verdict produced by a metric-class
hierarchy + tolerance-policy dispatcher + overall-verdict reducer, wired
into the Control-plane task pipeline.

This retro evaluates the 5-task arc that closed that deliverable across
39 commits and 3 Codex audit rounds over ~6 hours on 2026-04-25.

## Data · counter progression + task matrix

| DEC | Task | Counter | Scope | Codex rounds | Final verdict | Est. / actual |
|---|---|---|---|---|---|---|
| V61-054 | P1-T1 | 40→**41** | MetricsRegistry + 4 Metric subclasses + `_comparator_wrap` | **2** | APPROVE_WITH_COMMENTS (R2) | 0.75 / 2-round close |
| V61-055 | P1-T2+T3 (batched) | 41→**42** | TrustGate reducer + CaseProfile tolerance_policy loader + 2-case backfill | **1** | APPROVE_WITH_COMMENTS | 0.82 / 1-round close |
| (unnumbered) | P1-T3b | N/A (additive) | 8-case tolerance_policy backfill (100% whitelist) | 0 | doc-only, no Codex | N/A |
| V61-056 | P1-T5 | 42→**43** | task_runner Control→Evaluation TrustGateReport integration | **1** | APPROVE_WITH_COMMENTS | 0.85 / 1-round close |

Arc total: **4 Codex rounds across 3 code-bearing DECs** (P1-T3b is
doc-only; P1-T4 blocked on KNOWLEDGE_OBJECT_MODEL Draft). Arc counter
delta: +3. Well below the 20-counter ceiling.

## Self-pass-rate calibration

| DEC | Estimated | Codex R1 verdict | Rounds to CLEAN | Calibration delta |
|---|---|---|---|---|
| V61-054 | 0.75 | CHANGES_REQUIRED (2 blocking) | 2 | Over-estimated by ~0.25; R1 caught 2 legitimate correctness bugs. |
| V61-055 | 0.82 | APPROVE_WITH_COMMENTS (1 nit) | 1 | Accurate ± 0.10. R1 caught immutability drift; verbatim fix in same arc. |
| V61-056 | 0.85 | APPROVE_WITH_COMMENTS (2 nits) | 1 | Accurate ± 0.10. R1 caught note-drop + test-gap; verbatim fix in same arc. |

**Observation**: calibration improved monotonically across the arc
(0.75 over-estimate → 0.82 on-mark → 0.85 on-mark). Consistent with
"confidence earned through prior findings" — V61-054's 2 blockers
sharpened the verdict-translation logic, V61-055+V61-056 re-applied the
same rigor to simpler cases.

## Codex economics

| Round | Target | Tokens used | Findings | Verdict |
|---|---|---|---|---|
| V61-054 R1 | P1-T1 5-commit arc | 186,887 | 2 BLOCKING + several non-blocking | CHANGES_REQUIRED |
| V61-054 R2 | 83f1161 fix verification | — | 1 non-blocking docstring scope nit | APPROVE_WITH_COMMENTS |
| V61-055 R1 | P1-T2+T3 batched | 146,155 | 1 non-blocking immutability nit | APPROVE_WITH_COMMENTS |
| V61-056 R1 | P1-T5 minimal slice | 124,803 | 2 non-blocking (note-drop + test gap) | APPROVE_WITH_COMMENTS |

Total: **~460k Codex tokens across 4 rounds**. 2 of 4 rounds delivered
only non-blocking comments (V61-055, V61-056). V61-054 R2 was a verify-
fix round where the non-blocking comment was a scope-of-docstring issue,
not a new defect.

## What Codex caught (that static analysis alone would miss)

1. **V61-054 R1 #1** — `REF_SCALAR_KEYS` wrapper/comparator misalignment.
   Wrapper's key list had `"u"`/`"St"`; comparator's didn't. Pre-fix
   behavior: heterogeneous `reference_values=[{u:2.0},{value:1.0}]`
   produced PASS in comparator but FAIL in wrapper — a trust-gate
   false-fail. This was a **genuine correctness bug** in the evaluation
   foundation. Tests I had written (12 pointwise/integrated) all happened
   to use keys present in BOTH lists, so the bug was invisible until
   Codex constructed the heterogeneous-list repro. **Lesson**: when
   mirroring another component's semantics, extract the data (the
   `REF_SCALAR_KEYS` tuple) to a shared location rather than re-declaring.
   Mirror-by-duplication drifts over time.

2. **V61-054 R1 #2** — `tolerance_policy.get(name, tolerance_policy)`
   cross-pollination. Top-level `tolerance` key leaked into every metric
   that lacked a per-name entry. This contradicted the documented
   `CaseProfile.tolerance_policy[<observable_name>]` semantic from
   METRICS_AND_TRUST_GATES §4. **Lesson**: `dict.get(key, default_dict)`
   is a Python idiom that looks innocent but can leak state when the
   fallback IS the outer container. Prefer explicit `None` fallback or
   `.get(name) or {}`.

3. **V61-055 R1** — `TrustGateReport` "frozen" mutability drift.
   `@dataclass(frozen=True)` freezes attribute rebinding but NOT the
   inner `list`/`dict` containers. Callers could mutate
   `report.count_by_status[FAIL] = 999` and silently invalidate
   `summary()`/`has_failures`. Fixed with `Tuple` + `MappingProxyType`.
   **Lesson**: frozen dataclass ≠ fully immutable. State this in
   docstrings AND enforce at the container level.

4. **V61-056 R1 #1** — `ATTEST_NOT_APPLICABLE` WARN-reason dropped. The
   `_build_trust_gate_report` helper derived notes only from non-PASS
   concerns. Empty concerns + WARN status = user sees an unexplained
   warning. ResidualMetric in src.metrics.residual had a `notes=
   "attestor not applicable..."` fallback for this exact case; the
   task_runner helper diverged. **Lesson**: when building two paths
   that produce the same verdict type (ResidualMetric vs task_runner
   residual-report), cross-check notes emission explicitly; don't
   assume one path's defensive message ports to the other.

5. **V61-056 R1 #2** — test coverage gap. E2E "happy path" only
   exercised the attestation-only branch (gold stubbed to None).
   Comparison branch had 5 direct-helper tests but no end-to-end
   pipeline-integrated test. **Lesson**: when writing E2E tests,
   list the conditional branches in the helper and confirm each branch
   is covered at the E2E layer, not just the unit layer.

None of these would have been caught by `pytest`, `lint-imports`, or
static type checks alone. They all require semantic code reading +
cross-module consistency checking, which Codex excels at.

## What went well

1. **Batched reviews**. V61-055 covered P1-T2 + P1-T3 as a single
   Codex audit (vs two separate rounds). Saved ~150k tokens vs splitting.
   Pattern: group features that share a plane + audit focus area.

2. **Verbatim exception discipline**. V61-054 R1 fix, V61-055 R1
   immutability fix, V61-056 R1 note+tests fix all satisfied the 5/5
   verbatim exception criteria (diff-matches-suggestion / ≤20 LOC /
   ≤2 files / no API change / cites round+finding). Zero unnecessary
   R2+ rounds.

3. **Plane contract held through 39 commits**. Every commit ran
   `lint-imports` and `pytest`; zero contract breaks. ADR-001's 4
   forbidden contracts proved their value as a regression net — caught
   one potential Evaluation→Execution import on V61-054 T1c (cylinder_
   strouhal_fft) that would have been subtle to find manually.

4. **Additive integration pattern**. P1-T5 added `trust_gate_report`
   as an optional `None`-defaulted field on `RunReport`. 25 existing
   task_runner tests passed unchanged. This same pattern will let
   P1-T4 (when KOM unblocks) swap `_build_trust_gate_report` for full
   `MetricsRegistry`-per-task without any downstream-consumer breakage.

## What to watch

1. **P1-T4 is blocked on KNOWLEDGE_OBJECT_MODEL being Draft**. The
   charter has the ObservableDef formalization on P1's critical path
   but it genuinely cannot land until KOM promotes to Active. Mitigated
   by P1-T5's additive design. Risk: if KOM stays Draft for weeks, the
   `_build_trust_gate_report` helper will grow organic responsibilities
   that make the P1-T4 transition harder.

2. **10/10 whitelist case profiles carry tolerance_policy** but the
   tolerances are all verbatim copies of gold YAML `tolerance` fields.
   There is no case yet where the **policy** deviates from the **gold's
   default**, which means the dispatch path is structurally exercised
   but semantically untested against real override scenarios. First
   real deviation (expected: cylinder 10s-endTime precision-limited
   25% St tolerance vs gold's tighter implied 5%) will surface any
   loader/dispatch bugs in production.

3. **Cylinder attempt-7 live run FAIL**. DEC-V61-053 had a background
   task complete during this session (bbuywy0ry · 8628.2s · FAIL at
   `audit_real_run_measurement.yaml`). Not investigated in this arc
   — orthogonal to P1 Metrics layer. Should land as V61-053 retro
   addendum per RETRO-V61-001 post-R3 live-run defect rule.

4. **39 unpushed commits to origin/main**. Git safety protocol requires
   explicit user approval. Delay creates merge-conflict risk if other
   development happens in parallel.

## Open questions

1. Should `_build_trust_gate_report` in src/task_runner.py start calling
   `load_tolerance_policy(task_spec.name)` now, even pre-P1-T4? This
   would make the policy dispatch path visible in production paths
   without waiting for ObservableDef formalization. Cost: would need to
   re-evaluate comparator against policy-overridden tolerance, which is
   a refactor (currently declined in P1-T5 per "minimal slice" scope).

2. Is it time to retire RunReport.comparison_result + attestation in
   favor of trust_gate_report alone? Currently RunReport has all three;
   downstream consumers can choose. Deprecation would clarify API but
   risks breaking external consumers we don't see. Recommendation:
   leave as-is for P1; deprecate in P2.

3. Should there be a "TrustGate decision rubric" DEC formalizing the
   worst-wins rule + WARN semantics? Currently spread across
   METRICS_AND_TRUST_GATES §2/§5, src.metrics.trust_gate docstring, and
   src.task_runner._build_trust_gate_report docstring. Three places
   stating the same rule is healthy redundancy but also drift risk.

## Recommendations

1. **Next DEC should address open question #1**: land
   `load_tolerance_policy` call in `_build_trust_gate_report` as a
   small extension. Tolerance-policy dispatch will then have a
   production consumer before P1-T4 unblocks.

2. **V61-053 retro addendum** should be written next session (not
   this session — attempt-7 FAIL needs investigation first, not
   in-scope for P1 retro).

3. **Push 39 commits to origin/main** requires user approval. Staging
   area is clean (working tree has only reports/ deep_acceptance
   autogen artifacts, which are gitignored or tracked as test outputs).

4. **Do NOT start P1-T4** until KOM promotes to Active via
   SPEC_PROMOTION_GATE. Respect the gate; the deferred design is sound.

5. **Calibration trend** (0.75 → 0.82 → 0.85) suggests self-estimates
   should now hover in the 0.80-0.85 band for similar-complexity work.
   Reset the ceiling at 0.90 until a round returns APPROVE (no comments),
   at which point recalibrate upward.

## Counter accounting

| Point | counter_v61 | Event |
|---|---|---|
| Session start | 40 | pre-P1-T1 |
| V61-054 landed | 41 | P1-T1 MetricsRegistry arc close |
| V61-055 landed | 42 | P1-T2+T3 batched close |
| V61-056 landed | 43 | P1-T5 task_runner integration close |
| Retro-V61-004 (this) | 43 | doc-only, no counter tick |

Next DEC will tick to 44. 20-counter arc-size retro threshold not
re-triggered until counter ≥ 60 (40 + 20 from last RETRO-V61-003 reset
checkpoint).

## Sign-off

- Self-sign by Claude Opus 4.7 1M context under 全权自动推进 mode
- User acknowledgment required on next session touch
- Notion sync to follow via Sessions or Retrospectives DB (pending
  retrospective-DB schema decision)

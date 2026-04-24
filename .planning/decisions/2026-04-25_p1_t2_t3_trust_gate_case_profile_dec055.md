---
decision_id: DEC-V61-055
title: P1-T2 TrustGate reducer + P1-T3 CaseProfile.tolerance_policy loader
supersedes_gate: none
intake_ref: none (P1 task-level DEC, follow-on to DEC-V61-054 P1-T1 arc)
methodology_version: "v2.0 (per RETRO-V61-001 + RETRO-V61-053)"
commits_in_scope:
  - 4410b0c feat(metrics) P1-T2 TrustGate overall-verdict reducer (13 tests)
  - bcea4ec chore(state) P1-T2 STATE stamp
  - 0450df6 feat(metrics) P1-T3 CaseProfile.tolerance_policy schema + loader (16 tests + 2 case profile backfills)
codex_verdict: PENDING_POST_MERGE_REVIEW (batched review of P1-T2+T3)
autonomous_governance: true
autonomous_governance_counter_v61: 42
external_gate_self_estimated_pass_rate: 0.82
external_gate_self_estimated_pass_rate_source: |
  P1-T2 TrustGate: pure function, frozen dataclass, 13-test comprehensive
  worst-wins coverage. Self-confidence ~90%. P1-T3 loader: subtle
  edge cases (NaN, bool-as-int, null tolerance pass-through, empty
  file, defensive copy) all have tests. Real-repo integration tested.
  Self-confidence ~80%. Combined batched estimate ~82%. Above the
  70% pre-merge trigger, so post-merge Codex is procedurally correct.
external_gate_caveat: |
  P1-T3 introduces file-system I/O inside Evaluation-plane module
  (yaml.safe_load from .planning/case_profiles/). ADR-001 governs
  Python import graph only, not file reads, but consumers of
  src.metrics now implicitly depend on the `.planning/` directory
  existing. This is acceptable for dev/CI but may need sandboxing
  when src.metrics is packaged for downstream distribution. Not
  blocking; flag for P2 packaging DEC.
codex_tool_report_path: reports/codex_tool_reports/dec_v61_055_p1_t2_t3_review.log (pending)
notion_sync_status: synced 2026-04-25T04:05 · Status=Proposed (page_id=34cc6894-2bed-81bb-84da-fffed3160327, URL=https://www.notion.so/DEC-V61-055-P1-T2-TrustGate-reducer-P1-T3-CaseProfile-tolerance_policy-loader-34cc68942bed81bb84dafffed3160327)
github_sync_status: pushed (2 feat commits + 1 state stamp on origin/main)
reversibility: MEDIUM — TrustGate reducer is a pure function, easily
  removable. CaseProfile loader touches 2 case profile YAMLs additively
  (tolerance_policy block is optional; removing it leaves existing
  risk_flags untouched).
canonical_follow_up: |
  P1-T4 ObservableDef formalization (TypedDict or dataclass to replace
  ad-hoc `observable_def` dicts passed to Metric.evaluate). Probably
  blocks on KNOWLEDGE_OBJECT_MODEL v1.0 Active (per VCP §8.1 accepting
  clause) since ObservableDef is a Knowledge-schema concern. P1-T5
  integrate TrustGate + CaseProfile into task_runner report pipeline
  (Control-plane wiring).
---

# DEC-V61-055 · P1-T2 TrustGate + P1-T3 CaseProfile Loader

## Scope

Two P1 Metrics & Trust Layer features landed back-to-back:

**P1-T2 TrustGate overall-verdict reducer** (commit 4410b0c):
- `src/metrics/trust_gate.py`: `TrustGateReport` frozen dataclass +
  `reduce_reports` worst-wins aggregator function
- Rule: any FAIL → FAIL; else any WARN → WARN; else PASS (empty input
  = vacuous PASS)
- `TrustGateReport` exposes `overall`, `reports` (defensive copy),
  `count_by_status` (all 3 keys zero-filled), `notes` (formatted
  non-PASS notes in input order), `summary()` one-liner, and
  convenience properties `passed`/`has_failures`/`has_warnings`
- 13 tests covering aggregation matrix + empty + notes ordering +
  dataclass immutability + end-to-end with MetricsRegistry

**P1-T3 CaseProfile.tolerance_policy loader** (commit TBD):
- `src/metrics/case_profile_loader.py`: `load_tolerance_policy` +
  `load_case_profile` + `CaseProfileError`
- Extends G-6 CaseProfile schema with optional `tolerance_policy`
  block: `{observable_name: {tolerance: float, ...}}`
- Absent file / empty file / absent tolerance_policy → `{}`
  (fall-through to observable_def.tolerance semantics)
- Explicit `tolerance: null` → passes through (residual metrics)
- Raises `CaseProfileError` on malformed YAML, schema violations,
  non-numeric tolerance, NaN, bool-as-int
- Plane: Evaluation. YAML file I/O, not Python import. Resolves
  `.planning/case_profiles/` via repo-root walk from `__file__`
- 16 tests covering 4 absence paths + 2 happy paths + 6 schema
  violation paths + 1 null pass-through + 2 real-repo loads + 1 E2E
  dispatch integration

## Why this DEC (not extending V61-054)

V61-054 is the P1-T1 arc DEC (4 metric class wrappers + MetricsRegistry
+ comparator wrapper). V61-054 hit CLEAN CLOSE with R2 APPROVE_WITH_
COMMENTS; extending it with downstream deliverables would confuse the
close audit. V61-055 is the natural downstream DEC — TrustGate
consumes MetricReports from V61-054's MetricsRegistry, and CaseProfile
loader feeds tolerance_policy kwarg to the same registry's
`evaluate_all`.

## Plane + schema additions summary

- `src.metrics.trust_gate` → Evaluation plane (src.metrics.* already
  covered by .importlinter Evaluation source_modules)
- `src.metrics.case_profile_loader` → Evaluation plane (same)
- YAML schema delta: added `tolerance_policy:` optional block to
  CaseProfile v1 (schema_version unchanged — additive, optional,
  forward-compatible). Documented inline in lid_driven_cavity.yaml
  (first concrete example) + circular_cylinder_wake.yaml (DEC-V61-053
  10s-endTime-limited tolerances as second example).

## Test coverage summary

| File | Tests | Covers |
|------|-------|--------|
| `test_trust_gate.py` | 13 | worst-wins aggregation, histogram, notes, summary, frozen dataclass, E2E with MetricsRegistry |
| `test_case_profile_loader.py` | 16 | 4 absence paths, 2 happy paths, 6 schema violations, null pass-through, real-repo loads, E2E dispatch |

Full suite: 651 passed, 1 skipped. 4 import contracts KEPT throughout.

## Post-merge Codex review protocol

Batched review of both features with focus areas:
1. TrustGate reducer semantic correctness (worst-wins edge cases, empty-input vacuous PASS, defensive-copy semantics)
2. TrustGate notes formatting — `"{name} [{status}]: {notes}"` — is this stable / consumable for UI?
3. CaseProfile loader repo-root-walk resolution: fragile vs. robust? What if tests run from a sub-directory where `.planning/` isn't visible?
4. YAML schema-violation coverage — is the NaN guard correct (Python `float('nan') != float('nan')` is True per IEEE 754)?
5. Boolean-tolerance rejection — is the `isinstance(tol, bool)` check order correct? `isinstance(True, int)` is also True in Python
6. Null tolerance pass-through through to MetricReport — downstream `evaluate_via_result_comparator` uses `if tol_override is not None` guard; null-as-None preserves observable_def.tolerance fallback
7. Defensive-copy depth in `load_tolerance_policy` — is `dict(entry)` shallow copy sufficient, or should it be `copy.deepcopy(entry)` for nested dicts?
8. DEC-V61-054 R1 finding #2 invariant preservation: top-level `tolerance` in a loaded policy must NOT leak into metrics without named entries. P1-T3's loader only outputs per-name dict; registry's fix guarantees per-name dispatch. Confirm no regression.

---
retro_id: RETRO-V61-002
type: incident
timestamp: 2026-04-21T08:15 local
trigger: PR #22 (DEC-V61-022) post-merge Codex round 8 returned CHANGES_REQUIRED
governance_rule: "Retrospectives mandatory on ... any `CHANGES_REQUIRED` verdict" (RETRO-V61-001 bundle D)
scope: single-PR incident analysis; not an arc-size retrospective
upstream: DEC-V61-022 (P6-TD-002 duct dispatch), PR #22 (merge 36e3249), PR #27 (round-8 fix, merge 7bbbeb2)
counter_at_incident: 3 (PR #20 + PR #21 + PR #22)
---

# RETRO-V61-002 · PR #22 CHANGES_REQUIRED incident

Small incident retro per RETRO-V61-001 bundle D new rule. Scope is one
PR, one round. Compare to RETRO-V61-001 which spanned 16 DECs and
re-wrote governance — this one is much tighter.

## What the finding was

Codex round 8 flagged one **Blocking** finding on PR #22:

> The new dispatcher signal is not invariant across TaskSpec
> construction paths. `hydraulic_diameter` lives under `parameters` in
> `knowledge/whitelist.yaml`; only `src/task_runner.py` normalizes it
> into `boundary_conditions`. `KnowledgeDB.list_whitelist_cases()` does
> not, so a duct_flow TaskSpec built via that path still silently
> re-routes to the flat-plate Spalding extractor.

The fix originally patched only the symptom (two duct_flow cases
producing identical Cf to 10 decimals) and did not close the
silent-reroute hole repo-wide.

## Why it was missed

Pre-merge self-estimate was 91%. Root cause of the over-estimate:
- Audited the dispatch call site but not the two TaskSpec construction
  paths that feed it.
- Assumed `hydraulic_diameter` was canonically stored in
  `boundary_conditions` because that is where `task_runner.py` puts it.
  Did not verify the whitelist YAML shape directly.
- Integration test coverage used a hand-built TaskSpec fixture, not a
  `KnowledgeDB.list_whitelist_cases()` construction. That gap is the
  reason the unit tests all passed while the repo-wide invariant was
  broken.

In RETRO-V61-001 terminology: **this is a self-pass-rate calibration
miss**. 91% predicted vs 0% actual (CHANGES_REQUIRED with a Blocking).

## What Codex added that I did not

Codex explicitly grepped across construction paths rather than
accepting the call-site abstraction. When reviewing "dispatcher
keyed on X", always ask "where does X get set, and can every caller
set it?" — my review missed that second question.

## Fix applied (PR #27)

- `_is_duct_flow_case(task_spec)` helper using canonical name-identity
  as primary signal, `hydraulic_diameter` as secondary.
- Fail-closed `duct_flow_hydraulic_diameter_missing` flag for the
  ambiguous duct-by-name + BC-absent case.
- Integration test against `KnowledgeDB.list_whitelist_cases()` to
  lock the canonical construction path into CI.
- Naming note applied: `duct_flow_extractor_missing` →
  `duct_flow_extractor_pending` (Codex round 8 naming note, non-blocker).

Merge SHA 7bbbeb2. 101/101 test_foam_agent_adapter.py.

## Governance lessons (for future pre-merge estimates)

1. **Dispatcher review checklist**: when a PR adds a dispatcher keyed
   on field `X`, verify that every in-repo constructor of the relevant
   dataclass sets `X` consistently. Grep for ALL constructors, not just
   the one in the call site under review.

2. **"Silent misrouting holes" category**: under v6.1 governance, any
   PR that changes dispatch logic should be self-estimated ≤ 85%
   regardless of test count, because integration-test gaps here are
   asymmetric (wrong route + right-shape measurement = silent-pass
   hazard).

3. **`hydraulic_diameter`-style parameter-vs-boundary-conditions
   normalization** is a known repo split; PR authors touching adapter
   routing should treat construction-path coverage as a first-class
   gate.

## Counter delta

This incident is in the normal autonomous flow; counter advances
normally. No threshold violations. RETRO-V61-001 bundle D predicted
exactly this situation ("counter = pure telemetry, retros driven by
risk") and the governance held up — CHANGES_REQUIRED was caught
post-merge, fix landed in a follow-up PR with clear trace-ability
(DEC-V61-022 frontmatter updated to RESOLVED by PR #27).

## Self-estimate calibration update

Post-fix calibration for future dispatcher-touching PRs:

| Change class | Previous default | New default |
|---|---|---|
| Dispatcher adds new branch keyed on existing field | 90% | 80% |
| Dispatcher adds new signal field | 85% | 75% |
| Dispatcher refactor with helper extraction | 70% | 70% |

Apply these as starting values; adjust downward further if the
dispatched value feeds byte-reproducibility or signed manifest paths.

## Closes

No DEC close-out needed (DEC-V61-022 already updated frontmatter with
verdict + PR #27 resolution link). This retro is archival — next
retrospective trigger is counter ≥ 20 or phase-close or another
CHANGES_REQUIRED verdict.

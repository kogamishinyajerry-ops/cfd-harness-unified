---
decision_id: DEC-V61-091
title: M5.1 trust-core micro-PR — TrustGate hard-cap on imported user case verdicts
status: Accepted (2026-04-28 · Codex 3-round arc → APPROVE [R1 APPROVE_WITH_COMMENTS · 1 P3 doc-wording / R2 APPROVE_WITH_COMMENTS · 1 doc-nit / R3 APPROVE clean] · Kogami APPROVE_WITH_COMMENTS · recommended_next=merge · 5 findings (3 P2 + 2 P3) addressed inline · CFDJerry explicit ratification 2026-04-28)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-04-28
authored_under: spec_v2 M5.1 narrowing (Pivot Charter Addendum 1 + DEC-V61-089 Track B verdict-ceiling invariant)
parent_decisions:
  - DEC-V61-087 (v6.2 three-layer governance · Kogami high-risk-PR clearance applies here)
  - DEC-V61-088 (pre-implementation surface scan · routine startup discipline)
  - DEC-V61-089 (two-track invariant · Track B PASS_WITH_DISCLAIMER ceiling is the load-bearing rule)
  - DEC-V61-090 (M6.1 · introduced task_spec.mesh_already_provided which this DEC consumes as the imported-case signal)
  - .planning/strategic/m5_kickoff/spec_v2_2026-04-27.md (M5.1 trust-core hard-cap scope)
  - RETRO-V61-001 (risk-tier triggers · trust-core boundary modification → multi-round arc mandatory)
parent_artifacts:
  - src/metrics/trust_gate.py (existing _ceiling_to_warn pattern · M5.1 adds parallel source-origin routing)
  - src/task_runner.py (existing apply_executor_mode_routing wiring · M5.1 adds analogous call)
  - src/models.py (TaskSpec.mesh_already_provided field landed by V61-090)
prerequisite_status:
  m6_1_acceptance: confirmed (DEC-V61-090 Accepted 2026-04-28 · commit 1831a77 + be0cec6 on main · Codex round-8 APPROVE + Kogami APPROVE_WITH_COMMENTS)
  v61_089_acceptance: confirmed (DEC-V61-089 Accepted 2026-04-28 · two-track invariant + Track B PASS_WITH_DISCLAIMER ceiling · Notion synced · this DEC's mechanism is dispatched ONLY by V61-089's invariant being load-bearing)
notion_sync_status: synced 2026-04-28 (https://www.notion.so/34fc68942bed81f0ac8ee925c8b3b5a6)
autonomous_governance: true  # advances counter; trust-core verdict-ceiling change requires Codex + Kogami gates
codex_tool_report_path: reports/codex_tool_reports/m5_1_imported_verdict_cap_2026-04-28.log
kogami_review:
  required: true  # high-risk PR (verdict-graph adjacent · trust-core ceiling logic)
  triggers:
    - trust_gate.py modification (verdict-grade boundary change · RETRO-V61-001 §Q3 codified Codex trigger)
    - new ceiling note added to verdict envelope (consumer-visible audit trail change)
    - Pivot Charter Addendum 1 directly load-bearing — imported cases MUST NOT reach PASS verdict
  status: APPROVE_WITH_COMMENTS · recommended_next=merge
  invocation_date: 2026-04-28
  artifacts: .planning/reviews/kogami/m5_1_imported_verdict_cap_2026-04-27/
  findings_addressed_in_dec:
    - P2 #1 (ADR-001 anchor for constant duplication) → §Scope item 2 expanded with explicit Contract 2 + plane reference
    - P2 #2 (dormant-cap window stop-the-line condition) → §"Why this preserves trust-core boundary" gained a stop-the-line paragraph
    - P2 #3 (multi-cap note shape test + UI dedup contract) → tests/test_trust_gate_source_origin.py adds test_executor_mode_plus_imported_user_records_both_notes_in_application_order; §Out of scope adds explicit UI-dedup deferral
    - P3 #4 (self-pass-rate calibration anchor) → §Verification plan rewritten with V61-090 comparator
    - P3 #5 (prerequisite_status missing V61-089) → frontmatter prerequisite_status now records v61_089_acceptance
---

# DEC-V61-091 · M5.1 · TrustGate hard-cap on imported user case verdicts

## Why

DEC-V61-089 established the two-track invariant: Track B (workbench
imported user cases) verdicts are capped at PASS_WITH_DISCLAIMER
because there is no literature ground truth to validate against. The
underlying mechanism for that cap was deferred to this DEC.

Pivot Charter 2026-04-26 Addendum 1 makes this load-bearing: the
project must not produce a verdict envelope that claims "PASS"
(literature-validated) on a user-uploaded geometry the harness has
no reference data for. M5.0 + M6.0 + M6.1 produced the upstream
machinery to ingest + mesh imported cases; until M5.1 lands, that
machinery has no governance brake on what the run-time verdict can
claim.

## Pre-implementation surface scan (per DEC-V61-088)

Performed 2026-04-28 prior to code work:

1. **ROADMAP scan**: M5.1 maps to ROADMAP §M5.1 trust-core
   verdict-cap. No prior implementation matched.
2. **Existing-implementation grep**:
   - `apply_source_origin_routing`, `imported_user_no_literature_ground_truth`,
     `imported_user.*verdict` — zero pre-existing hits
   - `MetricStatus.PASS_WITH_DISCLAIMER` — does NOT exist as an enum
     value (TrustGate is three-state PASS / WARN / FAIL)
   - existing `_ceiling_to_warn` pattern at `src/metrics/trust_gate.py:158`
     is the architectural precedent — used by `apply_executor_mode_routing`
     for mock and hybrid_init mode caps. M5.1 adds an analogous
     `apply_source_origin_routing` that consumes the same primitive.

## Scope

### Implementation strategy: reuse existing _ceiling_to_warn pattern

Rather than introducing a new MetricStatus enum value, M5.1 reuses
the existing PASS → WARN ceiling primitive with a specific note
string (`imported_user_no_literature_ground_truth_pass_with_disclaimer`).
The UI / audit-package / report layers can render WARN+note as
"PASS_WITH_DISCLAIMER" in user-facing copy without requiring an
enum surgery that would touch every MetricStatus consumer.

### In scope

1. **`src/metrics/trust_gate.py` · new function `apply_source_origin_routing`**:
   ```python
   def apply_source_origin_routing(
       base_report: TrustGateReport,
       source_origin: str | None,
   ) -> TrustGateReport:
       if source_origin == SOURCE_ORIGIN_IMPORTED_USER:
           return _ceiling_to_warn(base_report, _NOTE_IMPORTED_USER_NO_LITERATURE_GROUND_TRUTH)
       return base_report
   ```

2. **`src/metrics/trust_gate.py` · new constants**:
   - `SOURCE_ORIGIN_IMPORTED_USER = "imported_user"` (mirrors the
     M5.0 `case_scaffold.SOURCE_ORIGIN_IMPORTED_USER` constant; the
     duplication is the canonical pattern under ADR-001 four-plane
     import direction — `src.metrics` is in Plane.EVALUATION and
     Contract 2 of `.importlinter` forbids importing from `ui.backend`
     (Plane.UI / line-A). A shared-constants module would itself be
     cross-plane. Future readers tempted to "just import from
     case_scaffold" must instead lift the constant into a third,
     boundary-respecting location with its own DEC.)
   - `_NOTE_IMPORTED_USER_NO_LITERATURE_GROUND_TRUTH = "imported_user_no_literature_ground_truth_pass_with_disclaimer"`

3. **`src/task_runner.py` · wire the routing call**: alongside the
   existing `apply_executor_mode_routing`, derive `source_origin` from
   `task_spec.mesh_already_provided` (per DEC-V61-090 the M6.1 flag
   is exclusively set for imported user cases) and call
   `apply_source_origin_routing`. Composition order: source_origin
   ceiling applied AFTER executor-mode ceiling so both ceilings stack
   correctly (worst-wins invariant preserved).

4. **Tests** (`tests/test_task_runner_trust_gate.py` + new
   `tests/test_trust_gate_source_origin.py`):
   - PASS report + imported_user → WARN with the note appended
   - WARN report + imported_user → WARN unchanged (note appended)
   - FAIL report + imported_user → FAIL unchanged (worst-wins monotone)
   - PASS report + non-imported → PASS unchanged (regression guard)
   - None / unknown source_origin → no ceiling (forward-compat)
   - Composition with executor-mode ceiling: both ceilings independent;
     `_ceiling_to_warn` is severity-idempotent + count-stable (notes
     accumulate honestly on reapplication so the audit trail records
     each cap event)

### Out of scope (deferred)

- New MetricStatus enum value (no enum surgery)
- UI rendering of "PASS_WITH_DISCLAIMER" copy (M8 / dogfood concern)
- UI dedup of multiple cap notes when executor-mode + source-origin
  both fire (e.g. mock-mode imported case): the audit trail records
  both notes separately by design; downstream renderers are
  responsible for presentation. M8 / dogfood concern.
- Manifest-level `source_origin` field schema (already exists in M5.0
  case_manifest.yaml; M5.1 doesn't change schema)
- Per-case verdict-band relaxation (a different Track B concern;
  not all imported cases need the same ceiling, but uniform cap is
  the safe-by-default starting point)
- `audit_package --include-imported` filter (was part of original
  spec_v2 M5.1 scope · split out · imported cases land in the
  audit-package with their disclaimer-noted verdict already; the CLI
  filter is a separate consumer concern, not a trust-core change)

## Why this preserves trust-core boundary

The new `apply_source_origin_routing` function takes a string tag as
input. It does NOT read `case_manifest.yaml` from inside trust-core;
the caller (`task_runner` in line-A) reads the source_origin and
passes it as an opaque parameter. ADR-001 four-plane import direction
is preserved.

The signal-derivation rule `task_spec.mesh_already_provided=True ⟹
source_origin="imported_user"` is exclusive per the M6.1 contract: no
production caller sets the flag for any case other than imported
user. Until M7 wires the flag, the cap is dormant (no caller fires
it). After M7 wires it, the cap fires automatically.

**Stop-the-line condition for the dormant window** (Kogami P2 #2):
during the gap between M5.1 merge and M7 wire-up, any new caller
proposing to set `task_spec.mesh_already_provided=True` outside
M6.1's documented contract (i.e., for any case kind other than
workbench imported user geometry) MUST file a successor DEC. The
M6.1 exclusivity is a contract, not a runtime invariant — silent
expansion of the flag's set of true-callers would silently expand
the cap's blast radius without governance review.

## Verification plan

### Self-test (pre-Codex)
- `pytest tests/test_task_runner_trust_gate.py tests/test_trust_gate_source_origin.py -q` — all new tests green
- `pytest tests/test_foam_agent_adapter.py -q` — M6.1 tests stay green (no executor regression)
- Existing TrustGate test corpus stays green

### Codex review
- Multi-round arc per RETRO-V61-001 (trust_gate.py modification + verdict-graph adjacency)
- Self-pass-rate estimate: **80%** — calibrated against V61-090 M6.1
  (analogous trust-core micro-PR · single bool flag · single guard
  site) which reached APPROVE in 8 rounds with 1 P1 + 5 P2 +
  surface-expansion; this DEC has comparable surface but adds a NEW
  function rather than guarding an existing one (smaller call-site
  blast radius). 80% reflects "code-path likely clean on first pass,
  doc-wording iteration plausible" against that anchor.

### Kogami high-risk-PR clearance
- Strategic package: `.planning/reviews/kogami/m5_1_imported_verdict_cap_2026-04-28/`

### CFDJerry explicit ratification
- Required per DEC-V61-087 — pre-merge gate; STOP point.

## Failure modes considered

| Failure mode | Mitigation |
|---|---|
| Imported case slips through with PASS verdict (no cap fires) | Test `test_imported_case_pass_capped_to_warn_with_disclaimer_note` exercises the cap path. M6.1 contract guarantees `mesh_already_provided=True` ⟺ imported case. |
| Whitelist case incorrectly capped | Default `task_spec.mesh_already_provided=False` keeps the cap dormant. Test `test_whitelist_pass_unchanged` is the regression guard. |
| Caller passes a non-imported source_origin string (e.g., "draft", "whitelist") | Function only fires on the canonical `"imported_user"` constant. All other strings (including None) fall through unchanged — forward-compat. |
| Executor-mode ceiling + source-origin ceiling double-applied | Both go through `_ceiling_to_warn` which is severity-idempotent + count-stable (PASS → WARN, WARN → WARN, FAIL → FAIL; `count_by_status` does not double-bump on reapplication). Composition is monotone. Notes accumulate truthfully on each cap event so the audit trail is preserved. |
| Future imported case categories (imported_step, imported_msh, etc.) | Forward-compat: extending the function is additive (more constants, same primitive). |

## Counter impact

Per V61-087 §5 truth table (autonomous_governance=true · Kogami review
is gate not counter), counter advances per Interpretation B (STATE.md
SSOT canonicalized in V61-087 §5 v2).

- **Pre-advance**: 55 (post-V61-090 Accepted)
- **Post-advance**: 56

RETRO-V61-001 cadence: counter ≥20 triggers arc-size retro;
phase-close triggers phase-close retro. Neither fires from this
single DEC.

## Sync

Notion sync runs only after Status flips to Accepted (i.e., after
Codex APPROVE + Kogami APPROVE + CFDJerry ratification). Pre-merge
state stays Proposed in the repo decisions/ directory.

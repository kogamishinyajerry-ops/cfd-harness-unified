# Kogami Review · v61_088_pre_implementation_surface_scan · 2026-05-02

**Verdict**: `APPROVE_WITH_COMMENTS`
**Recommended next**: `merge`
**Trigger**: autonomous_governance_rule_change_round2
**Artifact**: `.planning/decisions/2026-04-27_v61_088_pre_implementation_surface_scan.md`
**Prompt SHA256**: `ae1b81d97a561b1dc204e083164d9f181d166437838f0e78210f3ef781c3b5e0`

## Summary

DEC-V61-088 is strategically sound: it operationalizes a Notion-Opus P1 finding into a named, low-cost startup discipline that closes a real and demonstrated failure mode (the run-compare API duplication of an existing UI feature). The DEC correctly classifies itself as autonomous_governance:true, correctly invokes Kogami per §4 first item, and the prior Kogami P1/P2/P3 findings are visibly closed inline with sharpened thresholds, §11 interaction rules, commit-trailer discipline, and explicit acceptance-criteria sequencing. Three remaining concerns are scope-clarity items and one minor coherence gap with the §11.4 quota framing — none block APPROVE.

## Strategic Assessment

Decision-arc coherence is strong: this DEC fits naturally between RETRO-V61-V107-V108 R2 ('migration grep before commit') and the broader pattern of methodology evolution from reactive incident-retros to proactive startup-discipline rules (RETRO-V61-006 MP-A pre-Codex checklist precedent, RETRO-V61-053 risk-flag taxonomy precedent). It correctly identifies its Pivot Charter §4.7 framework (autonomous side, not Kogami contract), correctly fires §4 first-item Kogami review, and correctly avoids self-modifying any P-1..P-5 file. Roadmap fit is good: it does not advance any specific milestone (M5–M8) but reduces the probability of M5/M6/M7 starting parallel-to-existing work, which is high-value during the M-sequence where workbench territory is dense and active. The cost (~1 minute per non-trivial work item + commit-trailer discipline) is well within the project's standing methodology overhead budget. The DEC's self-acknowledged 'ritual compliance' risk is mitigated cleanly via the commit-trailer audit trail and the negative exemplar (96e9f46) anchoring. No retrospective completeness gaps: the DEC explicitly accounts for prior Notion-Opus framing risk and the ROADMAP-state-read failure pattern, and it is honest that the autonomous arm currently checks case_profile / DEC numbering / counter audit upfront but not ROADMAP state — which is the precise gap being closed.

## Findings

### [P2] §11.4 quota interaction conflates two independent rules
**Position**: §Interaction with §11 standing rules · second bullet (§11.4)

**Problem**: The §11 interaction section says 'the planned commit counts toward the rolling quota regardless of whether the scan finds prior work' — this is true but tautological; §11.4 already counts every workbench-path commit. The novel interaction is whether surface-scan disposition (extend vs parallel-new) should affect quota accounting (it does not) AND whether the scan's *output* should make the engineer aware of remaining quota (it should). As written, the rule reads as if the scan creates new quota cost, which could confuse readers.

**Recommendation**: Rephrase as: 'The surface scan does not change §11.4 quota accounting (every workbench commit already counts). What changes is engineer awareness — when the scan triggers on §11.4-tracked paths, the engineer SHOULD also check current quota state before committing to a parallel-new disposition, since parallel-new spends a slot that could be saved by extend-existing.' This separates the (unchanged) accounting rule from the (new) awareness practice.

### [P2] Threshold trigger leaves 'top-level page/route/service file' undefined
**Position**: §Decision · trigger paragraph + §Skip clause (d)

**Problem**: The trigger `≥30 LOC OR new top-level page/route/service file` and skip-clause (d) `≤10 LOC AND no new top-level file` both depend on what counts as a 'top-level page/route/service file'. The repo has multiple route-registration patterns (FastAPI APIRouter modules under `ui/backend/routes/`, service modules under `ui/backend/services/`, frontend pages under `ui/frontend/src/pages/**`). Without an enumeration, future ambiguity is likely on edge cases (e.g., a new helper service module called only by an existing route, or a new sub-route file added under an existing routes/ directory).

**Recommendation**: Add a one-line definition: 'Top-level page/route/service file = a new file under one of {ui/backend/routes/*.py, ui/backend/services/*.py top-level (not nested helper), ui/frontend/src/pages/**/*.tsx top-level page component, scripts/*.py user-facing entry point}. Internal helpers under existing modules do NOT count.' This keeps the rule operationally crisp without enumerating exhaustively.

### [P3] Acceptance Criteria #2.1 user-level CLAUDE.md edit is high-blast-radius but no rollback path is named
**Position**: §Acceptance Criteria · post-acceptance step 1

**Problem**: The DEC correctly flags the ~/CLAUDE.md edit as high-blast-radius (affects all projects under ~/CLAUDE.md governance) and requires user confirmation of exact edit text. But it does not name a rollback path if the rule turns out to be over-applied to non-cfd projects (where 'pre-implementation surface scan via grep' may not make sense — e.g., greenfield prototypes, throwaway scripts).

**Recommendation**: Add a sentence: 'If the rule produces friction on non-cfd projects, the user-level edit can be retracted to project-level (CLAUDE.md only) without invalidating this DEC's autonomous-governance scope, since the discipline is justified by cfd-harness-unified evidence and may not generalize.' This makes the project-vs-user-level scope cleanly reversible.

### [P3] Out of Scope does not explicitly disclaim modification of §10.5.4a audit-required surfaces
**Position**: §Out of Scope

**Problem**: The DEC's Out of Scope correctly disclaims Kogami contract / Codex triggers / counter rules / user workflow. But §10.5.4a (audit-required surfaces, currently 7) is methodology-active and arguably adjacent to surface-scan discipline (both are 'check before you write'). A reader could ask whether surface scan replaces or supplements the §10.5.4a audit-required path. It supplements (different purpose: §10.5.4a is for trust-core-adjacent surfaces, surface-scan is for any non-trivial work), but the DEC doesn't say so.

**Recommendation**: Add: '- Does NOT modify §10.5.4a audit-required surface list. Surface scan is a separate, broader-scope discipline (any non-trivial work) that supplements, not replaces, §10.5.4a Codex audit-required gating (which fires on the 7 specific trust-core-adjacent surfaces regardless of surface-scan outcome).'


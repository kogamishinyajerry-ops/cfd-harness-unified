---
decision_id: DEC-V61-046
title: Demo-first convergence + 3-persona Codex iteration loop
status: IN_PROGRESS (round 2 remediation landed 2026-04-23T00:30; round 3 pending)
commits_in_scope:
  - 87b3b39 fix(contracts): Python 3.12 + jsonschema + UNKNOWN note_map
  - 335c4b4 test(cleanup): stale tests aligned with DEC-V61-011/029/040
  - 700dccb feat(ui): / → /learn default; Dashboard → /pro
  - 47bc235 feat(contracts): physics_contract backfill LDC/BFS/plane_channel/impinging_jet + SATISFIED class
  - f89cfd0 fix(export): 3-state precondition marker + contract_status headline
  - a1feef9 chore(dev-server): pin frontend port 5180 (was 5173 default)
  - 5c90ea1 docs(dec): DEC-V61-046 PROPOSAL — demo-first convergence + 3-persona Codex iteration
  - 6c53986 fix(contracts): round-1 batch 1 — factual corrections (LDC/BFS/plane_channel/impinging_jet)
  - fa7d96d fix(dashboard): round-1 batch 2 — unify gold_file on canonical yamls + parity test
  - 6911611 feat(learn): round-1 batch 3 — buyer-facing hero + PhysicsContractPanel + CTA strip
  - 93e84cf fix(robustness): round-1 batch 4 — _precondition_marker helper + edge-case tests
  - 61140c4 docs(dec): round-1 remediation log
  - f50a4e4 docs(dec): round-1 sync-complete marker + round-2 prompt
  - c87a354 fix(precondition): round-3 batch 5 — tri-state through API (R3-B1 blocker)
  - f6d1743 fix(contracts): round-3 batch 6 — BFS anchor internal consistency (R2-M2)
codex_verdict: CHANGES_REQUIRED (round 2 — 1 blocker R3-B1 + 1 major R2-M2; both remediated via batches 5+6; R2-M5/R2-M8 deferrals accepted by codex)
autonomous_governance: true
autonomous_governance_counter_v61: 33 (33rd +1 entry since RETRO-V61-001 counter reset)
external_gate_self_estimated_pass_rate: 0.70
codex_tool_report_path: .planning/reviews/round_2_findings.md (11.5 KB, authored 2026-04-23; round_1_findings.md retained for arc audit)
notion_sync_status: synced 2026-04-23T00:10 (Status=Accepted, round-1 summary appended as page children; https://www.notion.so/DEC-V61-046-Demo-first-convergence-3-persona-Codex-iteration-34ac68942bed81fa909dd8315a7bf7dd, page_id=34ac6894-2bed-81fa-909d-d8315a7bf7dd)
github_sync_status: pushed (61140c4 on origin/main 2026-04-23T00:05; includes 4 remediation batches + round-log update)
related:
  - DEC-V61-035 (flip default run audit_real_run; underpins this round's dashboard distribution)
  - DEC-V61-036 G1/G3/G4/G5 (gates)
  - DEC-V61-038 (convergence_attestor)
  - DEC-V61-040 (UI 3-tier semantics — UNKNOWN surface)
  - DEC-V61-045 (prior full blocker-fix iteration; pattern reference for Codex iteration discipline)
timestamp: 2026-04-22T23:25 local
author: Claude Opus 4.7 (1M context, v6.2 Main Driver)
---

## Why this DEC exists

Six commits landed 2026-04-22 as a "demo-first convergence round": flip `/` to
`/learn`, backfill `physics_contract` for the 4 cases previously rendering
UNKNOWN, honesty-guard the export (3-state marker), collapse stale-test
drift, pin dev-server port. Per user directive, subject the outcome to a
**3-persona Codex review**:

1. **商业立项 demo 评审专家** — is this a credible demo for a funded AI-CFD startup?
2. **CFD 仿真专家工程师** — are the physics contracts I wrote for LDC/BFS/plane_channel/impinging_jet actually correct?
3. **Senior Code Reviewer** — standard diff review of the 6 commits.

Iterate until consolidated verdict is **APPROVE** (or APPROVE_WITH_COMMENTS with
only nits). Each iteration cycle = codex round + triage + fix commits + push +
Notion sync.

## Scope

- **In**: physics_contract content accuracy, demo-path coherence (/learn flow),
  code correctness of 6 commits, export-bundle honesty, Notion/GitHub sync
  discipline at each round boundary.
- **Out**: Phase 9 solver routing (plane_channel/impinging_jet physics fixes —
  documented as contract_status=INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE,
  real fix deferred). Bundle code-split (nice-to-have, 258KB gzip acceptable).
  Pre-existing repo-wide uncommitted state (13 M + 36 untracked under user's
  prior work, not in scope).

## Round log (to be updated per round)

### Round 1 — 2026-04-22T23:25 → T23:57 (remediation landed)
- **Codex exec PID**: 20548 (log at `.planning/reviews/round_1_codex.log`)
- **Prompt**: `.planning/reviews/round_1_prompt.md`
- **Findings**: `.planning/reviews/round_1_findings.md` (31 KB)
- **Verdict**: CHANGES_REQUIRED on all 3 personas, 0 blockers, ~15 MAJOR/MINOR
- **Findings addressed** (4 atomic commits):
  - Batch 1 (factual) `6c53986` — R2-M1 LDC precondition #4/#5 split to explicit
    false; R2-M2 BFS "<2% plateau" → regime-level wording; R2-N1 LDC
    "DNS-quality shoulder" → "Ghia high-resolution reference shoulder"; R2-M3
    plane_channel mesh labels WR-LES/DNS → honest "80³/160³ cells"; R2-M4
    impinging_jet A4 iter-cap surfaced as symptom not root cause; R3-M2 BFS
    turbulence model corrected kOmegaSST → kEpsilon per actual adapter code.
  - Batch 2 (dashboard) `fa7d96d` — R3-M1 source-of-truth unified: 5
    DashboardCaseSpec entries retargeted `gold_file` to canonical yamls
    (LDC_benchmark→LDC, BFS_steady→BFS, plane_channel, impinging_jet,
    cylinder_crossflow→circular_cylinder_wake). report_case_id kept legacy
    because on-disk run fixtures live at legacy paths; gold-side parity
    now holds. R2-M7 same root fix. +2 new tests: gold_file parity invariant
    + `_normalize_contract_class` direct prefix pin.
  - Batch 3 (learn UX) `6911611` — R1-M1/M4 hero rewritten buyer-facing +
    bilingual (AI-CFD workbench + 3-strip differentiation); R1-M2 + R2-M7
    new PhysicsContractPanel at top of Story tab surfacing contract_status
    + preconditions [✓]/[~]/[✗]; R1-M3 buyer CTA strip (GitHub / Pro / pilot
    mailto); R1-M5 two placeholder-alert nav items removed; R1-N1 sidebar
    tagline buyer-readable. R2-M6 "V&V40" wording softened to "inspired by,
    not equivalent".
  - Batch 4 (robustness) `93e84cf` — R3-N2 `_precondition_marker` helper
    extracted, 14 input shapes covered; R3-N3 +2 tests including live [✗]
    render from LDC explicit-false preconditions; R3-N4 two docstring drifts
    about reference-first fixed to audit_real_run-first; R3-N5 ui/frontend/README
    5173 → 5180.
- **Findings deferred** (recorded here with rationale, surfaced as backlog):
  - **R2-M5 contract_status taxonomy refactor** — split base_verdict /
    scope_qualifier / hazard_flags into three fields. Architectural change
    rippling through dashboard + export + typescript types + 10 YAMLs +
    tests. Defer to a dedicated DEC (followup from round N+k). Current
    long-prefix strings are readable and covered by `.startswith()` so no
    active drift risk.
  - **R2-M8 Spalding-fallback hard-hazard** — promote fallback activation
    from internal `cf_spalding_fallback_activated` flag to first-class
    AuditConcern emission for laminar TFP. Requires foam_agent_adapter
    change + concern-code plumbing across attestor/comparator. Defer:
    current fallback path is documented `partial` in TFP gold precondition
    #4 with explicit follow-up audit note, not silently active.
- **New commits**: 6c53986, fa7d96d, 6911611, 93e84cf (all on main, local).
- **Test suite**: 784 → 789 passed / 2 skipped (+5 new, 0 regressions).
- **Schema validator**: 15/15 PASS.
- **Frontend**: typecheck clean; build 1.34s.
- **GitHub sync**: pushed 2026-04-23T00:05 — 5 commits landed on origin/main (6c53986, fa7d96d, 6911611, 93e84cf, 61140c4).
- **Notion sync**: synced 2026-04-23T00:10 — DEC-046 row Status=Proposed→Accepted; round-1 remediation summary appended as page children (5 bullets covering batches 1-4 + deferral rationale + round-2 next-step note).

### Round 2 — 2026-04-23T00:00 → T00:11 (remediation landed T00:30)
- **Codex exec PID**: 28060 (log `.planning/reviews/round_2_codex.log`)
- **Prompt**: `.planning/reviews/round_2_prompt.md`
- **Findings**: `.planning/reviews/round_2_findings.md` (11.5 KB)
- **Verdict**: CHANGES_REQUIRED
  - Role 1 商业立项: APPROVE_WITH_COMMENTS (R1-M1..M5 all verified addressed; 2 new nits R1-N2 browser title + R1-N3 audit-bridge context-drop)
  - Role 2 CFD: CHANGES_REQUIRED — R2-M2 only partially addressed (BFS gold YAML internal inconsistency: header cites 6.28, stores 6.26, still repeats `<2%`)
  - Role 3 Senior Reviewer: CHANGES_REQUIRED — **R3-B1 BLOCKER**: live `build_validation_report("backward_facing_step")` bool()-casts YAML `partial` → `True`; export bundle honest but Story-tab + `/pro` PreconditionList lossy
- **Deferrals accepted by codex**: R2-M5 (taxonomy refactor, long-prefix `startswith()` behaviour pinned by unit test), R2-M8 (Spalding hard-hazard; TFP precondition already labels `partial` with follow-up note).
- **Findings addressed** (2 atomic commits):
  - Batch 5 (R3-B1 blocker) `c87a354` — `ui/backend/services/validation_report.py` new `_normalize_satisfied` helper + `_make_preconditions` tri-state pass-through (replaces `bool(...)` cast); `ui/backend/schemas/validation.py` `Precondition.satisfied` typed `Literal["partial"] | bool`; `ui/frontend/src/types/validation.ts` mirror `boolean | "partial"`; `ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx` `mark()` simplified to 3 branches (evidence-text fallback removed); `ui/frontend/src/components/PreconditionList.tsx` `/pro` component gets tri-state dot/label/tone + header counts split satisfied/partial/unmet; 2 new tests (`test_validation_report_preserves_partial_precondition_tristate` pins BFS live-API surface; `test_normalize_satisfied_tristate_and_unknowns` covers 13 input shapes with fail-visible unknowns).
  - Batch 6 (R2-M2 BFS) `f6d1743` — `knowledge/gold_standards/backward_facing_step.yaml` header + `reference_correlation_context` + reference_values[].description + source field all rewritten to explicitly label the stored 6.26 as a BLENDED engineering anchor (Le/Moin/Kim 5100 DNS 6.28 + Driver & Seegmiller 37500 experiment 6.26 both cited as bracket literature; 10% tolerance absorbs the 0.02 literature spread; the disavowed `<2%` sensitivity claim removed). `ui/frontend/src/data/learnCases.ts` BFS teaching copy removes `<2%` wording and matches the blended-anchor rationale.
- **New commits**: c87a354, f6d1743 (local).
- **Test suite**: 789 → 791 passed / 2 skipped (+2 new tri-state tests, 0 regressions).
- **Frontend**: typecheck clean; build 1.33s; bundle unchanged 803 KB / 259 KB gzip.
- **Notion sync**: pending (to update after push).
- **GitHub sync**: pending (to push).

### Round 3 — TBD
Codex re-review after round-2 remediation. Expected: R3-B1 tri-state and R2-M2 blended-anchor fix verified; R1-N2 (browser title) + R1-N3 (audit-bridge context) judged as nits not blockers. Ideal outcome: consolidated APPROVE or APPROVE_WITH_COMMENTS with deferrals intact.

### Round N+1 — template
(Fill after round N codex APPROVE or CHANGES_REQUIRED)
- **Verdict**:
- **Findings addressed**: (list with commit sha)
- **Findings deferred**: (list with rationale — must not be blockers)
- **New commits**: (shas)
- **Notion sync**: (status + timestamp)
- **GitHub sync**: (sha pushed)

## Exit criteria

- Codex consolidated verdict: **APPROVE** or **APPROVE_WITH_COMMENTS** (only nits)
- All three persona verdicts non-CHANGES_REQUIRED
- `pytest tests/ ui/backend/tests` green (baseline ≥784 passed)
- `npm run typecheck` + `npm run build` green
- GitHub: all iteration commits pushed to `origin/main`
- Notion: DEC-V61-046 row in Decisions DB `fa55d3ed0a6d452f909d91a8c8d218a7`
  updated to COMPLETE with final verdict + codex_tool_report_path

## Sync discipline (per round boundary)

1. Implementation commits created locally.
2. `git push origin main` — GitHub is the canonical code truth.
3. Update this DEC frontmatter: `codex_verdict`, `codex_tool_report_path`,
   `github_sync_status` (with pushed sha), `notion_sync_status`.
4. Append round block to "Round log" section above with dated evidence.
5. Sync to Notion Decisions DB (via manual update or
   `run_notion_hub_sync.py --apply`); record url under `notion_sync_status`.
6. Only then launch next codex round.

Violating order 1→6 (e.g., running round N+1 before pushing round N) makes the
DEC and code drift. Bi-directional sync must hold at every cycle boundary.

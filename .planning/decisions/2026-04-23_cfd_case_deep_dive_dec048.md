---
decision_id: DEC-V61-048
title: 10-case 深度阅读价值评审 · senior CFD reviewer deep-dive · per-case 内容升级
status: AWAITING_USER_READ (all 4 batches landed · exit gate is user subjective pedagogy read)
commits_in_scope:
  - fb83f0d feat(learn): DEC-V61-048 batch 1 — benchmark lineage + next-reading ladder (all 10 cases)
  - e8a2632 feat(learn): DEC-V61-048 batch 2 — TeachingCard 2.0 (10 cases × 4 cards)
  - 80e1c12 feat(learn): DEC-V61-048 batch 3 — reproducibility runbook + troubleshooting (10 cases)
  - 12de4fe feat(learn): DEC-V61-048 batch 4 — flagship physics-intuition deep-dive (LDC/RBC/duct)
codex_verdict: DEEP_DIVE_COMPLETE (round 1 findings landed; no codex round 2 per DEC design — exit gate is user subjective read)
autonomous_governance: true
autonomous_governance_counter_v61: 35
external_gate_self_estimated_pass_rate: 0.45
codex_tool_report_path: .planning/reviews/case_deep_dive_round_1_findings.md
notion_sync_status: synced 2026-04-23T01:42 + batches 2/3/4 children append done (page_id=34ac6894-2bed-8101-b25a-f43a96f8207c, Status=Proposed → will flip to Done on user acceptance)
github_sync_status: pushed (fb83f0d + e8a2632 + 80e1c12 + 12de4fe on origin/main)
related:
  - DEC-V61-046 (demo-first convergence · hero + honesty + tri-state · APPROVE_WITH_COMMENTS)
  - DEC-V61-047 (2-persona pedagogy · narrative truth + teaching cards · APPROVE_WITH_COMMENTS)
  - This DEC **supersedes** the "教学叙事 adequate" assumption in V61-047:
    user's direct read post-V61-047 closeout: "现在几乎没有一个 case 有阅读价值"
timestamp: 2026-04-23T01:40 local
author: Claude Opus 4.7 (1M context, v6.2 Main Driver)
---

## Why this DEC exists

V61-046 closed: hero/demo/CTA/tri-state all APPROVE_WITH_COMMENTS.
V61-047 closed: narrative truth + 4 teaching cards + evidence collapse,
BOTH CFD-expert + CFD-novice personas APPROVE_WITH_COMMENTS.

But user's direct read of the resulting /learn demo:

> 几乎没有一个 case 有阅读价值

This is a harsher bar than "APPROVE_WITH_COMMENTS". Codex judged each
card factually correct and the novice persona readable — but the
**aggregate content per case is still not textbook-grade CFD reading
material**. The gap is not accuracy (V61-046/047 handled that); it's
**depth, narrative density, visualization, historical context, and
pipeline completeness**.

What "阅读价值" probably means in the user's reading:

1. Each case should read like a **chapter from a CFD textbook** —
   historical framing, why it became a benchmark, what it teaches that
   other cases don't, the real engineering tradeoffs.
2. Per case there should be enough **visual density** — mesh block
   diagrams, BC schematic, flow regime map, multiple literature
   reference images, the actual computed contour with annotations.
3. Each case should have a **troubleshooting / failure-mode walk**:
   "if this goes wrong, here's what you'd see; diagnosis steps; what
   the /pro workbench tools would show."
4. The 4 `TeachingCard`s (solver / mesh / BC / extraction) are too
   terse — more like `man-page` entries than pedagogical paragraphs.
5. Most cases have only **1 literature reference image** and **no
   annotated render of actual solver output** — insufficient visual
   anchoring.
6. No **"workflow from 0 to result"** for each case — pre-processing,
   geometry input, meshing commands, solver launch, residual monitor,
   post-processing probes, comparator invocation.

## Scope

- **In**:
  - Per-case narrative depth upgrade (teaser_zh expansion, historical
    context, why-this-case-matters in the benchmark lineage)
  - `TeachingCard` bodies expanded to 4-6 sentences each, with
    concrete numbers + OpenFOAM command snippets + citation-link-back
  - Mesh block diagram ASCII/SVG per case
  - Per-case troubleshooting section (common failure modes, what they
    look like on residuals / contour, how to fix)
  - Per-case CFD pipeline walkthrough (prepare → mesh → solve →
    extract → compare — ordered steps with expected output)
  - Additional literature-reference images where public-domain /
    permissive-licensed imagery exists
  - Annotated real-solver contour with callouts of key flow features
    (stagnation point, separation line, recirculation bubble, etc.)
  - Glossary callouts for jargon (y+, CFL, URF, GCI, Re_τ, Pr, Nu,
    Boussinesq approx) on first use
- **Out**:
  - Tier-C backend refactor (still deferred per V61-047 F3 rationale)
  - Adding new cases to whitelist (still 10)
  - Changing gold-standard numeric values or contract logic
  - V&V methodology changes (V61-046 already settled)

## Single-persona codex review approach

Previous DECs used 2 or 3 personas. This DEC uses **one** deeper
reviewer persona:

**资深 CFD 教学专家 + 技术作家**:
- 15+ years OpenFOAM practice (like V61-047 expert) PLUS
- experience writing published CFD pedagogy (textbook chapters,
  Ansys/COMSOL training material, CFD Online tutorial essays)
- Judges each case against the bar: "if I were assigning reading
  material for a graduate CFD methodology course, would I assign
  this page? If not, what specifically is missing?"

Per-case deep-dive expected — not a global findings list. 10 cases,
each getting 400-800 words of review with specific file:line + "add
X here" recommendations.

## Iteration plan

Unlike V61-046/047, this is NOT a multi-round iterate-until-APPROVE
cycle (we've done two of those; further codex rounds at this stage
are yak-shaving). Plan is:

1. **Round 1** — codex deep-dive, one pass, per-case findings.
2. Claude reads findings, prioritizes by impact-per-LOC, proposes a
   batch plan to user (4-6 batches covering 10 cases).
3. User confirms batch priority order (maybe wants a specific subset
   first — e.g. "do LDC + BFS first, those are the intro cases").
4. Claude implements batches with atomic commits + push + Notion
   sync per batch.
5. No codex round 2 unless user explicitly requests one.

The DEC closes when user says "enough" or when batch plan completes.

## Exit criteria

- User re-read of `/learn` says reading value is now adequate (subjective
  user gate replaces codex gate this DEC)
- `pytest tests/ ui/backend/tests/` still green (baseline 791 passed)
- `npm run typecheck` + `npm run build` green
- GitHub: all batch commits pushed to `origin/main`
- Notion: DEC-V61-048 row Status=Done with codex_tool_report_path +
  final batch roster

## Sync discipline (same as V61-046/047)

Per batch:
1. Implementation commit local
2. `git push origin main`
3. Update DEC frontmatter (github_sync_status, round log)
4. Notion sync (page children append)
5. Only then start next batch

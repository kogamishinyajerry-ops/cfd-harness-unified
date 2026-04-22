# Codex Round 2 — DEC-V61-047: pedagogy remediation re-review

You produced `.planning/reviews/pedagogy_round_1_findings.md` in
round 1. Verdict was CHANGES_REQUIRED across both personas (CFD 仿真
专家 + CFD 仿真新手学徒), 4 blockers + 2 majors. Claude landed 3
atomic remediation commits on `origin/main` and deferred one major
(F3) with explicit rationale.

**Your job this round**: verify whether the 5 round-1 items addressed
(F1, F2, F4, F5, F6) actually closed the pedagogy signal for the two
personas, decide if the F3 deferral is acceptable or must be this
round's work, and call APPROVE / APPROVE_WITH_COMMENTS /
CHANGES_REQUIRED.

## Commits under review (round-2 scope)

On `origin/main`, HEAD=`10a3463`. Re-review window is
`09a4975..10a3463` (+ the DEC/round-log commit that will appear).

- `9d43d6a` **fix(learn): round-1 batch 1 — narrative truth alignment (F5 blocker)**
  - `ui/frontend/src/data/learnCases.ts` — 4 stale entries rewritten:
    - `turbulent_flat_plate` displayName/headline/teaser/bullets now
      say "laminar Blasius regime" + cite DEC-V61-006 regime correction.
      Re_x ≤ 5e4 in laminar band; Cf=0.664/√Re_x exact; solver=simpleFoam
      + turbulenceProperties=laminar.
    - `plane_channel_flow` reframed as "disguised incompatibility"
      teaching case: icoFoam laminar at Re_bulk=5600 → Poiseuille, gold
      is Moser 1999 Re_τ=180 turbulent DNS → ATTEST_PASS is comparator
      artifact, physics-honest verdict is FAIL.
    - `impinging_jet` reframed as two-layer gap teaching:
      (1) axis=empty not wedge → 2D planar slice not axisymmetric;
      (2) p_rgh A4 iteration-cap → not converged.
    - `differential_heated_cavity` rewritten from retired Ra=1e10 to
      canonical de Vahl Davis 1983 Ra=1e6 Nu=8.80 benchmark per
      DEC-V61-006 Path P-2.
- `958d85d` **fix(learn): round-1 batches 2+3 (F1+F2 blockers)**
  - `ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx`:
    - Visual-only Tier-C banner no longer hardcodes "audit_real_run
      verdict 为 FAIL". Backend `_build_visual_only_context` returns
      `verdict=None` and at least `circular_cylinder_wake` +
      `plane_channel_flow` fixtures declare `expected_verdict: PASS`.
      New copy: "Tier C · 过程证据，未做自动化金标准比对 … 不等于
      金标准通过也不等于失败".
    - New `RunResidualsCard` tries real `audit_real_run/renders/
      residuals.png` first; onError falls back to synthetic SVG
      labeled "⚠ 示意图 · illustrative only · not real solver trace".
      Tagline: "收敛不等于'算对'".
- `10a3463` **feat(learn): round-1 batches 4+5 (F4+F6 majors)**
  - `ui/frontend/src/data/learnCases.ts` — `LearnCase` shape extended
    with 4 new fields: `solver_setup_zh`, `mesh_strategy_zh`,
    `boundary_conditions_zh`, `observable_extraction_zh`. Populated
    for ALL 10 cases with concrete numbers pulled from gold YAML +
    `foam_agent_adapter.py`.
  - `ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx`:
    - New "CFD 全流程" section on Story tab renders 4 color-coded
      `TeachingCard` components (sky/emerald/violet/amber) in a 2-col
      responsive grid. Cards support small inline HTML (`<strong>`,
      `<code>`) via `dangerouslySetInnerHTML` — content is authored
      in `.ts` source, not user input.
    - `PhysicsContractPanel` `evidence_ref` now wrapped in
      `<details><summary>▸ 查看审计证据</summary>` — collapsed by
      default so novice sees condition + `consequence_if_unsatisfied`
      first. `consequence_if_unsatisfied` label translated to
      "如果不满足：" for consistency.

## Round-1 findings mapping

| R1 ID | Severity | What you asked for | Where addressed | Your verify expectation |
|---|---|---|---|---|
| F1 | 🔴 | Stop hardcoding FAIL on visual-only branch; derive honestly or drop verdict text | Batch 2+3 (958d85d) | Check `LearnCaseDetailPage.tsx:1490-1525` now reads "Tier C 过程证据" not "verdict 为 FAIL". Verify cylinder/plane_channel visual-only pages no longer show a red FAIL verdict. |
| F2 | 🔴 | Replace synthetic /run residual or label as synthetic | Batch 2+3 (958d85d) | Check `RunResidualsCard` tries real PNG first. If missing (404 on endpoint), fallback synthetic SVG is clearly labeled "⚠ 示意图 · illustrative only". |
| F5 | 🔴 | Rewrite stale narratives (TFP turbulent→laminar, plane_channel, impinging_jet, DHC Ra=1e10→1e6) to match current contracts | Batch 1 (9d43d6a) | Check `learnCases.ts` 4 entries now match the current gold YAMLs. displayName/headline/teaser/bullets/why_validation_matters all coherent? |
| F4 | 🟠 | Student-facing cards for geometry/BC/mesh strategy/solver/schemes/observable extraction | Batches 4+5 (10a3463) | Check new "CFD 全流程" section on Story tab. All 4 cards populated with case-specific concrete content (not generic boilerplate). |
| F6 | 🟠 | Split PhysicsContractPanel into student summary + expandable raw | Batches 4+5 (10a3463) | Check `evidence_ref` now inside `<details>`. consequence_if_unsatisfied stays visible. Inspect impinging_jet page specifically — is the reviewer-grade jargon now collapsible? |
| F3 | 🟠 | Promote 9 visual-only cases from Tier C to minimal teaching report in comparison_report.py | **DEFERRED** | Decide: is adding teaching cards on Story tab (F4 batch 4) a partial surrogate for the missing Tier-B overlay, or is the backend Tier-C upgrade still required for a non-blocker verdict? |

## Deferral judgment — F3

DEC-V61-047 round log deferral rationale:

> F3 (9/10 cases Tier-C) — upgrading `_VISUAL_ONLY_CASES` in
> `ui/backend/services/comparison_report.py` to include gold overlay
> + verdict + metrics for more cases is a backend service refactor
> that ripples through tier-B report assembly + HTML iframe rendering
> + test fixtures. The round-1 blockers (F1/F2/F5 + majors F4/F6)
> were the more urgent cognitive blockers for the novice persona.
> F3 deserves its own scoped batch or round.

**Decide explicitly**: accept the deferral (round-2 judges pedagogy
signal is sufficient on the frontend TeachingCards addition and doesn't
block APPROVE_WITH_COMMENTS) OR reject it (round-2 escalates F3 to a
blocker requiring the backend refactor).

## Verification suggestions (optional, fresh)

If possible, run these yourself during the review to avoid second-hand
trust:

1. `grep -n "FAIL" ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx | head -5`
   — confirm no hardcoded FAIL under visual-only branch.
2. `grep -cE "solver_setup_zh|mesh_strategy_zh|boundary_conditions_zh|observable_extraction_zh" ui/frontend/src/data/learnCases.ts`
   — should return 14 (4 interface lines + 4×10 populated per-case lines = 44? or 4 + 40 = 44). Rough sanity check.
3. `PYTHONPATH=. .venv/bin/pytest tests/ ui/backend/tests/ -q 2>&1 | tail -3`
   — should be 791 passed / 2 skipped.
4. `cd ui/frontend && npm run typecheck && npm run build` — clean,
   bundle ~803 KB / ~259 KB gzip.

## Personas reminder

You still wear 2 hats this round:

1. **CFD 仿真专家工程师** — are the solver/mesh/BC/extraction cards
   factually correct per case? Do they align with gold YAML +
   foam_agent_adapter? Does the TFP "laminar not turbulent" rewrite
   read as engineering-rigorous? Is the plane_channel "disguised
   incompatibility" teaching case faithful to the contract?
2. **CFD 仿真新手学徒 (中文母语)** — is the Story tab now navigable
   without being overwhelmed? Is the "CFD 全流程" section density
   right (2-col grid, 4 cards)? Is the evidence `<details>` click-to-
   expand a helpful UX or does it hide information the novice still
   needs? Can you now form a mental model of "this case's setup" in
   under 2 minutes?

## Output shape (same as round 1)

Write `.planning/reviews/pedagogy_round_2_findings.md` with:

```
# DEC-V61-047 Round 2 — Codex Consolidated Verdict

**Overall**: APPROVE | APPROVE_WITH_COMMENTS | CHANGES_REQUIRED
**Blockers**: N
**Expert verdict**: ...
**Novice verdict**: ...

## Remediation verification
- F1 [verify]: status + evidence
- F2 [verify]: status + evidence
- F5 [verify]: status + evidence (can be per-case brief)
- F4 [verify]: status + evidence (spot-check 2-3 cases)
- F6 [verify]: status + evidence

## Deferral judgment
- F3: accept | reject — reasoning

## New findings (if any)
- ...

## If APPROVE / APPROVE_WITH_COMMENTS
End iteration. Note any follow-up work as backlog.

## If CHANGES_REQUIRED: round-3 directive
Specific file:line + diff intent for minimum-fix.
```

## Bias reminder

You already called CHANGES_REQUIRED once. Resist the temptation to
chain rounds to demonstrate activity — the target is "is this now
textbook-grade for a Chinese-native CFD novice?" If yes: APPROVE or
APPROVE_WITH_COMMENTS. If no: be concrete about what's still missing.

Don't reopen issues the round-1 remediation clearly addressed just
because the remediation isn't exactly what you would have written.

Output only `.planning/reviews/pedagogy_round_2_findings.md`. Do not
edit any other file.

# Codex Round 3 — DEC-V61-046 round-2 remediation re-review

You produced `.planning/reviews/round_2_findings.md` which verdicted
**CHANGES_REQUIRED** with 1 blocker (R3-B1) and 1 major (R2-M2) after
reviewing commits `5c90ea1..61140c4`. Both deferrals (R2-M5 taxonomy,
R2-M8 Spalding hard-hazard) were accepted.

**Your job this round**: verify the 2-commit remediation (`c87a354` +
`f6d1743`) landed the round-2 directives correctly, decide if the
2 new minor nits (R1-N2 browser title, R1-N3 audit-bridge context-drop)
rise to blocker, and call APPROVE / APPROVE_WITH_COMMENTS /
CHANGES_REQUIRED.

## Commits under review (round-3 scope)

On `origin/main`, HEAD=`ba5390b`. Re-review window is `f50a4e4..ba5390b`
(+ `ba5390b` itself as round-log documentation — no code changes).

- `c87a354` **fix(precondition): round-3 batch 5 — tri-state through the API (R3-B1 blocker)**
  - `ui/backend/services/validation_report.py` — new `_normalize_satisfied(raw)`
    helper replacing the `bool(...)` cast. Accepts bool/int/string
    (`"true"/"false"/"yes"/"no"/"partial"/"partially"/"1"/"0"`), returns
    `True`/`False`/`"partial"`. Unknowns fail-visible (False).
    `_make_preconditions` calls it.
  - `ui/backend/schemas/validation.py` — `Precondition.satisfied` typed
    `Literal["partial"] | bool` with a docstring explaining the change.
    `Literal` already imported.
  - `ui/frontend/src/types/validation.ts` — mirror as `boolean | "partial"`.
  - `ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx` — `mark()`
    helper collapsed from 4 branches (with string-fallback detection)
    to 3 explicit branches (`=== "partial"`, `=== false`, else pass).
    The stale evidence-text fallback comment is gone.
  - `ui/frontend/src/components/PreconditionList.tsx` — `/pro` component:
    introduced a `toneFor(satisfied)` helper returning `"pass" | "partial" | "fail"`;
    DOT/LABEL/LABEL_TONE maps per tone; header count reports satisfied/
    partial/unmet separately; header tone reflects the most-severe tone.
  - `ui/backend/tests/test_validation_report.py` — 2 new tests:
    * `test_validation_report_preserves_partial_precondition_tristate`
      hits `/api/validation-report/backward_facing_step`, asserts every
      precondition `satisfied` ∈ {True, False, "partial"}, AND asserts
      at least one is `"partial"` (the round-2 blocker pin).
    * `test_normalize_satisfied_tristate_and_unknowns` covers 13 input
      shapes including `None`/`"maybe"`/`object()` → `False` fail-visible.
- `f6d1743` **fix(contracts): round-3 batch 6 — BFS anchor internal consistency (R2-M2)**
  - `knowledge/gold_standards/backward_facing_step.yaml` header block
    rewritten: BOTH Le/Moin/Kim 5100 DNS (Xr/H=6.28) AND Driver &
    Seegmiller 37500 experiment (Xr/H=6.26) listed as bracket
    literature for the post-transition plateau. The stored
    `reference_values[].value=6.26` is **explicitly labeled a BLENDED
    engineering anchor**, not a pure Le/Moin/Kim number. 10% tolerance
    absorbs the 0.02 literature spread. The `<2%` sensitivity claim is
    removed — plateau framing is qualitative.
  - Same YAML: `reference_correlation_context`, `reference_values[].description`,
    and `source` fields all rewritten to match the blended-anchor story.
  - `ui/frontend/src/data/learnCases.ts` BFS `why_validation_matters_zh`:
    removes the residual `<2%` wording; Chinese teaching copy now
    describes the blended anchor (6.28 DNS / 6.26 experiment) explicitly.
- `ba5390b` docs(dec) — round-2 round-log update + round_2_findings.md
  archived under `.planning/reviews/`. No code changes.

## Round-2 findings mapping (your own round-2 IDs)

| R2 ID | Directive | Where it was addressed | Accept? |
|---|---|---|---|
| R3-B1 | Stop bool()-casting; carry tri-state end-to-end; add service-layer test proving BFS stays partial in live ValidationReport | Batch 5 c87a354 — see commit block above | Run the test yourself: `pytest ui/backend/tests/test_validation_report.py::test_validation_report_preserves_partial_precondition_tristate -x`. Verify BFS `/api/validation-report/backward_facing_step` returns preconditions with at least one `"partial"` string on the wire (not `true`). |
| R2-M2 | Either change ref_value to 6.28 (pure Le/Moin/Kim) OR explicitly relabel 6.26 as blended engineering anchor with regime-level wording only; remove the disavowed `<2%` claim | Batch 6 f6d1743 — chose Option B (blended anchor) | Verify: header block + narrative + description now treat 6.26 as a deliberate blend, not a contradiction. No `<2%` language should remain in the gold YAML or in learnCases.ts. |
| R1-N2 | Browser title still "CFD Harness — Validation Report" at index.html:7 | **NOT FIXED** in this round | Decide: is browser title a round-3 blocker for a demo-first convergence phase, or a pure nit? Suggested verdict is nit (no user-visible copy in /learn route; fixable later). |
| R1-N3 | Advanced-tab audit-package bridge drops case/run context at LearnCaseDetailPage.tsx:234-237 vs header CTA at :1372-1374 | **NOT FIXED** in this round | Decide: inconsistency but not misinformation. Is a blocker or minor? Suggested verdict is minor. |

## Optional — items explicitly NOT in round-2 feedback

- Backwards-compat: any round-1 items you previously verified should
  still be verified under round-3 HEAD (make sure the round-2 fixes
  didn't regress round-1 remediation). A spot-check of 1-2 items is
  enough; exhaustive re-verification not required.
- New regressions: run `pytest tests/ ui/backend/tests/` and `pnpm
  typecheck && pnpm build` under HEAD=`ba5390b` if you want to pin
  the baseline; baseline should be 791 passed / 2 skipped.

## What you must output

Write `.planning/reviews/round_3_findings.md` with this structure:

```
# DEC-V61-046 Round 3 — Codex Consolidated Verdict

**Overall verdict**: APPROVE | APPROVE_WITH_COMMENTS | CHANGES_REQUIRED
**Blocker count**: N

## Remediation verification
- R3-B1 [verify]: addressed | partially | not addressed
  — evidence: file:line + test-run outcome
- R2-M2 [verify]: addressed | partially | not addressed
  — evidence: file:line
- R1-N2 [carry-over]: status + severity call (blocker / minor / nit)
- R1-N3 [carry-over]: status + severity call

## Role 1 — 商业立项 demo 评审专家
**Verdict**: ...

## Role 2 — CFD 仿真专家工程师
**Verdict**: ...

## Role 3 — Senior Code Reviewer
**Verdict**: ...

## New findings (if any, any persona)
- ...

## Deferrals (carry forward from round 2)
- R2-M5: still accept
- R2-M8: still accept

## If APPROVE or APPROVE_WITH_COMMENTS
Call it. End the iteration loop.

## If CHANGES_REQUIRED: round-4 directive
Minimum set of changes + specific file:line + diff intent.
```

## Severity scheme (same as rounds 1-2)

- 🔴 **Blocker** — must fix before APPROVE
- 🟠 **Major** — should fix, but APPROVE_WITH_COMMENTS acceptable if
  deferral is explicit
- 🟡 **Minor** — nice to have
- 🟢 **Nit** — no action needed

## Bias reminder

You wrote rounds 1 + 2. Resist the temptation to chain rounds to
demonstrate activity. The user's mandate is:
> **如此迭代，直至 Codex 对你足够满意.**

The bar is demo-first convergence delivered honestly, not perfection.
If R3-B1 tri-state works end-to-end and R2-M2 reads internally
consistent, APPROVE_WITH_COMMENTS is the right call even if R1-N2 /
R1-N3 remain.

Output only `.planning/reviews/round_3_findings.md`. Do not edit any
other file.

# DEC-V61-046 Round 3 — Codex Consolidated Verdict

**Overall verdict**: APPROVE_WITH_COMMENTS
**Blocker count**: 0

## Remediation verification
- R3-B1 [verify]: addressed
  — evidence: `ui/backend/services/validation_report.py:423-463`, `ui/backend/schemas/validation.py:138-155`, `ui/frontend/src/types/validation.ts:52-60`, `ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:460-471`, `ui/frontend/src/components/PreconditionList.tsx:9-63`, `ui/backend/tests/test_validation_report.py:482-538`. Fresh verification in the repo venv passed: `PYTHONPATH=. .venv/bin/python -m pytest ui/backend/tests/test_validation_report.py::test_validation_report_preserves_partial_precondition_tristate -x` and `PYTHONPATH=. .venv/bin/python -m pytest ui/backend/tests/test_validation_report.py::test_normalize_satisfied_tristate_and_unknowns -x` both returned `PASSED`. Direct TestClient probe on `/api/validation-report/backward_facing_step` returned `['partial', 'partial', 'partial', false]` on the wire.
- R2-M2 [verify]: partially addressed
  — evidence: `knowledge/gold_standards/backward_facing_step.yaml:10-29`, `knowledge/gold_standards/backward_facing_step.yaml:48-52`, `ui/frontend/src/data/learnCases.ts:53-67`. The substantive contradiction is fixed: `6.26` is now explicitly framed as a blended engineering anchor bracketed by `6.28` DNS and `6.26` experiment, and the header/context/description/source now tell the same story. Residual wording debt remains because the literal string `<2%` still appears in negated form at `knowledge/gold_standards/backward_facing_step.yaml:21,29` and `ui/frontend/src/data/learnCases.ts:66`.
- R1-N2 [carry-over]: still present; severity call = nit
  — evidence: `ui/frontend/index.html:7`. This is browser-chrome copy only; it does not change the buyer-facing `/learn` route content.
- R1-N3 [carry-over]: still present; severity call = minor
  — evidence: `ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:234-237`, `ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1362-1367`. The top CTA preserves `case` + `run=audit_real_run`; the Advanced-tab bridge drops both and sends the user to a generic builder entrypoint. That is friction, not misinformation.

## Role 1 — 商业立项 demo 评审专家
**Verdict**: APPROVE_WITH_COMMENTS
- The round-2 blocker that most directly harmed demo honesty is fixed: the Story tab now receives and renders literal `partial` preconditions instead of silently painting them green.
- The core buyer-facing ordering from round 1 still holds: `PhysicsContractPanel` remains the first block inside `StoryTab` (`ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:332-338`).
- `R1-N2` is cosmetic tab text, and `R1-N3` is a context-carrying inconsistency rather than a false promise. Neither justifies another remediation loop for a demo-first convergence pass.

## Role 2 — CFD 仿真专家工程师
**Verdict**: APPROVE_WITH_COMMENTS
- The important physics-contract repair landed: the BFS anchor is no longer self-contradictory. `6.26` is presented as a deliberate blended engineering anchor, bracketed by Le/Moin/Kim `6.28` DNS and Driver/Seegmiller `6.26` experiment (`knowledge/gold_standards/backward_facing_step.yaml:10-29`, `knowledge/gold_standards/backward_facing_step.yaml:48-52`).
- I am not reopening `R2-M2` as a blocker or major. The remaining `<2%` mentions are negated cleanup debt, not an active quantitative claim. The current text is physically honest even if the literal string removal is incomplete.
- The accepted round-2 deferrals still stand: `R2-M5` taxonomy debt and `R2-M8` Spalding hard-hazard promotion remain legitimate follow-up work, not blockers to this DEC closeout.

## Role 3 — Senior Code Reviewer
**Verdict**: APPROVE_WITH_COMMENTS
- The round-2 blocker is fixed end-to-end across service normalization, backend schema, TS types, Story-tab rendering, `/pro` rendering, and backend regression coverage (`ui/backend/services/validation_report.py:423-463`, `ui/backend/schemas/validation.py:138-155`, `ui/frontend/src/types/validation.ts:52-60`, `ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:460-471`, `ui/frontend/src/components/PreconditionList.tsx:9-63`, `ui/backend/tests/test_validation_report.py:482-538`).
- Required targeted verification is fresh and real. I did not rely on prior rounds: the repo venv test commands passed in this review, and the live API probe returned three literal `"partial"` values for BFS.
- I did not rerun the optional full `pytest tests/ ui/backend/tests/` plus `pnpm typecheck && pnpm build` matrix for this round. This verdict is based on targeted diff review plus the required remediation checks. Local `HEAD=6ad131d` is docs-only beyond `ba5390b`, so code scope did not drift past the requested remediation window.

## New findings (if any, any persona)
- Minor — the literal `<2%` phrase still remains in negated form in the BFS gold YAML and Chinese teaching copy (`knowledge/gold_standards/backward_facing_step.yaml:21,29`, `ui/frontend/src/data/learnCases.ts:66`). This no longer creates an anchor contradiction, so I am treating it as wording cleanup debt, not as a reopened blocker.

## Deferrals (carry forward from round 2)
- R2-M5: still accept
- R2-M8: still accept

## If APPROVE or APPROVE_WITH_COMMENTS
APPROVE_WITH_COMMENTS. End the iteration loop.

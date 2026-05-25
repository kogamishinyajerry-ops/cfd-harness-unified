# M3.14 milestone close · 2026-05-25

> Parent: `DEC-V61-203` §Follow-up · verification milestone (no code change)
> 1 cycle · 0 Codex · 0 Kogami · final commit (doc-only)

## 做了什么 (what)

Verified DEC-V61-203's "mirror the tsc gate in CI" follow-up and closed it as
**ALREADY SATISFIED**. No CI change made. Updated DEC-V61-203 §Follow-up (local
+ Notion) and RESUME with the corrected finding + the one genuine residual.

## 为什么 (why)

- **CI already mirrors the gate.** `.github/workflows/ci.yml` has a
  `frontend-build` job (lines 155-178) running `npm run typecheck`
  (`tsc --noEmit`) **and** `npm run build` (`tsc -b && vite build`) on
  `push:[main]` + `pull_request:[main, codex/stack-*]`. The M3.11 error surfaces
  in both tsc invocations, so CI's typecheck step would have caught it. Adding a
  redundant tsc step would be pointless duplication — so I added nothing.
- **Corrected root cause**: the M3.11 red-build slip was NOT "CI lacks the
  check." It was the branch sitting ~87 commits ahead and **unpushed**, so CI
  never executed. The M3.13 local pre-commit gate is exactly the layer that
  closes that gap (catches pre-commit, before push). Local gate + existing CI =
  complete two-layer coverage.
- **Verify-before-fabricate discipline** (same as M3.9/B4): the "continue per
  recommendation" instruction pointed at a CI mirror that turned out to already
  exist. The honest outcome is to report that and close it, not manufacture a
  duplicate edit to look busy.

## v2.3 governance check

| Gate | Status | Note |
|---|---|---|
| DEC scope | ✅ verification | no code change; doc-only closeout of DEC-V61-203 §Follow-up |
| Codex / Kogami | ✅ N/A | nothing to review |
| Four-question gate | ✅ Y/n-a | no functional change |
| Visual spot-check | ✅ N/A | no UI/code change |
| Notion | ✅ updated | DEC-V61-203 page Follow-up property synced to the finding |

## 下次候选 (next)

- **Branch protection (GitHub admin · NOT a code change · needs user):** make
  `frontend-build` a **required, merge-blocking** status check + require PRs into
  `main`. Today a `--no-verify` + direct push of a red build lands before CI goes
  red (CI runs post-push on direct pushes). This is a GitHub repo setting, not a
  yaml edit — flagged for the user; I can guide/`gh api` it only with explicit
  authorization (outward-facing repo change).
- DRY `VtkCanvasV3` onto `webgl_support` (low-priority code item).
- M4 charter scoping — deferred (multi-day · Kogami opt-in / user召唤).

## Bottom line

The recommended CI mirror already exists; the genuinely-open hardening is a
branch-protection setting only the repo admin can flip. Closed the follow-up
honestly with zero redundant code. The frontend build is now guarded at two
layers that were already (CI) or are now (M3.13 pre-commit) in place; the third
layer (required-check enforcement) is a GitHub setting awaiting user action.

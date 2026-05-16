---
decision_id: DEC-V71-4
title: V71.4 · AdvisorTab right-panel peer + V130/V132 contract test · V71.M/N/O LANDED
status: Accepted
parent_dec: DEC-V71-charter
phase: V71
notion_sync_status: pending
predecessor: DEC-V71-3
batch: B173
confidence: high
autonomous_governance: true
verdict: LANDED
v_row_landed: V71.4 (Done dimension #4 of 9)
substrate: V71.3 LANDED B172 · iter-2 weighted=92.32 · functional=33
---

# DEC-V71-4 · V130/V132 advisor contract test

## 1 · Decision

Land a comprehensive V130/V132 contract regression test for the v3 Advisor surface — six test cases that exhaustively assert no mutating affordance exists in any AdvisorContent lifecycle state.

## 2 · Scope

New file: `ui/frontend/src/pages/workbench/v3/__tests__/AdvisorContent.contract.test.tsx` (240 LOC). Six lifecycle states asserted:

1. **idle** — no consult yet
2. **after review** — review findings rendered
3. **after diagnose** — diagnose hypotheses rendered (suggested_fix as `<p>`)
4. **citation chip expand** — corpus chunk text appears inline
5. **offline (503)** — calm `advisor-offline-banner` appears (not red error)
6. **4xx error** — harsh `advisor-error` appears + still no mutating buttons

Assertion primitives:
- `assertNoForbiddenButtons(label)` — runs 10 regex patterns (en/zh) through `queryByRole("button", { name })`
- `assertNoForbiddenFormControls(label)` — counts descendant `<input>/<textarea>/<select>` of any `advisor-*` testid

Forbidden patterns: `apply / submit / execute / auto-fix / ^run$ / 应用 / 提交 / 执行 / 自动修复 / ^运行$`.

The `^run$` boundary (not just `run`) preserves the legitimate `consult advisor` and `diagnose run` button labels which contain "run" as a substring.

## 3 · V130 / V132 enforcement

This is the **load-bearing** invariant of the v3 surface. The test failures carry per-state labels so regressions are diagnosable:

> `[after review] V130/V132 violation: button matching /apply/i exists`

Any developer (including future Opus) who accidentally adds an Apply button anywhere in AdvisorContent will see this fail immediately. Reverse-stop applies: such a violation **must** revert the offending commit before merge.

## 4 · Tests

`npx vitest run` → **425 pass** (was 419 · +6 V71.4 contract tests). `npx tsc --noEmit` → **PASS**.

## 5 · Goal-backward map

Charter Done dim #4 ("AdvisorTab + V132 contract test — right-panel peer tab · paragraph + citations + preview-apply text links · ZERO auto-execute buttons regression-protected via e2e") → **LANDED**.

V71.M (AdvisorTab) + V71.N (AdvisorFinding) were LANDED during V71.1. V71.O (regression test) now LANDED here.

## 6 · Risks

- The forbidden-pattern list is closed at writing time. New Chinese / non-English mutating verbs added by future developers may slip through. Mitigation: retrospective addition when discovered.
- Form-control scan uses `[data-testid^='advisor-']` prefix selector — if a future component drops the prefix, the scan misses. Mitigation: parent `<section data-testid="advisor-content-root">` could be added to anchor the scope.

## 7 · Counter

Counter +1. Cumulative arc counter for V71: **5** (charter + V71.1 + V71.2 + V71.3 + V71.4).

## 8 · Next

V71.5 — ResultsCanvas + TrustGate verdict surface (Image 07 · V71.P/Q). The TruthChain tab already renders a verdict pill; V71.5 adds the report-canvas comparison and a HUGE PASS verdict block when results land.

---

**Co-Authored-By**: Claude Opus 4.7 (1M context)

---
decision_id: DEC-V68-C.2
title: V68-C.2 · LLM-offline graceful fallback · classifyAdvisorFailure + offline banner in AIAdvisorPanel
status: Accepted
parent_dec: DEC-V68-C-charter
phase: V68-C
notion_sync_status: pending
predecessor: DEC-V68-C-charter
batch: B143
confidence: high
autonomous_governance: true
verdict: SUB_DEC_LANDED
v_row_landed: none (sub-DEC)
substrate: V68-C charter §3 Done dim #2/#3/#4 + §5 sub-DEC V68-C.2
---

# DEC-V68-C.2 · LLM-offline graceful fallback

## 1 · Decision

Land V68-C.2 by adding a failure classifier to `AIAdvisorPanel`:

- **New exported `classifyAdvisorFailure(exc)`** in `ui/frontend/src/pages/workbench/step_panel_shell/AIAdvisorPanel.tsx`:
  - 5xx (incl. 500/502/503/504) + 408 timeout → `{ kind: "offline", detail, status }`
  - 4xx other than 408 → `{ kind: "error", detail, status }`
  - `TypeError` (fetch network failure, DNS, CORS) → `{ kind: "offline", detail, status: null }`
  - Other Error → `{ kind: "error", detail, status: null }`
- **Two UI states** instead of one:
  - `data-testid="ai-advisor-offline"`: calm amber banner ("AI advisor offline · rest of workbench unaffected · click again later to retry") — for transient backend issues that don't signal an engineer-actionable contract bug
  - `data-testid="ai-advisor-error"`: harsh red banner — kept for 4xx contract errors (bad case_id, invalid problem hint, etc.) the engineer must fix
- **State refactor**: `error: string | null` → `failure: ClassifiedAdvisorFailure | null` (single source of truth; offline vs error is a discriminant inside the same state field).

**Done dim mapping**:
- **DONE-2 · ProposalCard AI review real route** → MET by V68-A inheritance (already shipped DEC-V61-160 / N6.4)
- **DONE-3 · ProposalCard AI diagnose real route** → MET by V68-A inheritance (same)
- **DONE-4 · LLM-offline graceful fallback** → **NEWLY MET** at this sub-DEC

## 2 · Rationale · why charter "ProposalCard" = AIAdvisorPanel

V68-C charter §3 north star says: "打开 ProposalCard，点 [审 review] 真实 GET /ai-review · 返回 review verdict + comments；点 [诊 diagnose] 真实 GET /ai-diagnose · 返回 diagnosis + 建议。"

The repo has two components that could match:
- `ProposalCard.tsx` — chat-emitted proposal apply card (DEC-V61-121) — semantic = "engineer accepts/rejects AI-emitted tool calls"; surface = chat thread
- `AIAdvisorPanel.tsx` — [AI 审查] / [AI 诊断] buttons + finding/hypothesis display (DEC-V61-160) — semantic = "engineer reads citation-grounded advisor output"; surface = right-rail body

The charter's "click [审 review]" → fetch `/ai-review` → display ReviewResponse is **structurally** what AIAdvisorPanel does, not what ProposalCard does. ProposalCard is for *applying* parsed chat proposals; it doesn't fetch advisor routes at all. The charter shorthand "ProposalCard" should be read as "the advisor proposal display" — i.e., AIAdvisorPanel. This sub-DEC honors the charter intent by extending AIAdvisorPanel.

Renaming AIAdvisorPanel → "ProposalCard" is rejected: it'd collide with the existing ProposalCard semantic and break 23 import sites + 30+ existing tests.

## 3 · Rationale · why 5xx classifies as offline

Engineer mental model when clicking [AI 审查] / [AI 诊断]:
- 200 → I got advice, time to read.
- 4xx → I sent something wrong (bad case id, missing param). Fix the URL.
- 5xx → The advisor (LLM provider / backend) is having a moment. **It is not my fault. The workbench should still let me work.**

Pre-V68-C.2, all non-2xx surfaced as red `ai-advisor-error` regardless of whether it was the engineer's fault. That's both visually alarming and misleading — a 503 from a transient OpenAI/Anthropic upstream blip looked identical to a 422 invalid case_id. V68-C.2 separates these so:
- Offline state: amber, calmer copy, signals "advisor is the broken piece, you keep working"
- Error state: red, sharp copy, signals "you sent a bad request, fix it"

`TypeError` from `fetch` (network failure) classifies as offline because functionally the engineer can't distinguish it from "advisor offline" — both leave the rest of the workbench intact.

## 4 · Implementation summary

- **LOC**: 154 insertions / 24 deletions (only AIAdvisorPanel.tsx + its test file)
- **API surface change**: 0 — same component props, same testids retained, only **new** testid added (`ai-advisor-offline`)
- **MUTATING_ROUTES net diff**: 0 (no route changes; this is pure frontend classifier)
- **Tests added**: 5 new vitest (vitest 397 → 402)
  - 503 → offline banner
  - 500 → offline banner
  - network failure (TypeError) → offline banner (status="network")
  - 422 contract error → harsh error (not offline)
  - V130 invariant on offline: no Apply/Submit buttons surface
- **Test modified**: 1 (existing "renders error banner on API failure" was testing 502 which now correctly classifies as offline; updated to assert offline banner — more accurate semantic)

## 5 · Acceptance · LLM-offline UX flow verified

| Scenario | Pre-V68-C.2 | Post-V68-C.2 |
|---|---|---|
| LLM provider 503 | red error "503: ..." | amber offline "AI advisor offline · rest of workbench unaffected · click again later to retry" |
| Backend 500 crash | red error "500: ..." | amber offline |
| Network unreachable | red error "Failed to fetch" | amber offline (status=network) |
| Bad case_id (422) | red error "422: ..." | red error "422: ..." (unchanged — engineer's fault) |
| LLM available=false in 200 body | yellow degradation banner | yellow degradation banner (unchanged — response semantic, not transport failure) |

V130 invariants preserved at component test level:
- Test "V130 invariant preserved on offline (no Apply UI surfaced)" walks every button in the panel and asserts no `apply|submit|execute|应用|提交` matches
- `data-testid="ai-advisor-advisory-badge"` ("advisory only · no mutation") still present in all states

## 6 · Files changed

| File | Status | Purpose |
|---|---|---|
| ui/frontend/src/pages/workbench/step_panel_shell/AIAdvisorPanel.tsx | M | + classifyAdvisorFailure + offline banner + state shape refactor |
| ui/frontend/src/pages/workbench/step_panel_shell/__tests__/AIAdvisorPanel.test.tsx | M | + 5 new fallback tests + 1 modified (502 now offline) |

## 7 · Risk register · what could break

| Risk | Probability | Mitigation |
|---|---|---|
| Engineer dismisses offline banner thinking it's fine while backend is genuinely broken for hours | low-med | Banner is sticky until next click; copy explicitly says "click again later to retry"; loopback-guard already blocks remote LLM quota burn |
| Future 5xx that IS actionable (e.g., 507 storage full) gets buried as "offline" | low | 5xx semantic class is "server-side, not your fault"; storage-full surfaces in audit log not advisor panel |
| Test brittleness: status code mock changes break unrelated tests | mitigated | `statusCode` module-level var defaults to 502, resets in beforeEach; new tests set explicitly |

## 8 · Honest scope · what's NOT in V68-C.2

- **No retry button**: charter says "click again later"; explicit retry button would invite double-fire concerns. Engineer re-clicking [AI 审查] re-triggers the existing flow naturally.
- **No backoff/polling**: V130 invariant is "advisor is on-demand". Auto-retry against an upstream that's down would be a quota-burn liability.
- **No backend changes**: routes already classify cleanly; this is pure frontend UX refinement.

## 9 · Confidence: high

- All 7-pillar regression green: 402 vitest PASS · typecheck clean · lint 0 errors
- V130 invariant explicitly tested at panel level (assert no mutation affordance on offline)
- Done dims #2/#3 honest re-anchor: pre-V68-A shipped the wiring; V68-C.2 adds the missing graceful-fallback finishing touch
- Component-level change (no route, no schema, no contract) — blast radius local

— V68-C.2 sub-DEC · 2026-05-16 · B143

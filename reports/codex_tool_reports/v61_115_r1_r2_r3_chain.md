# V61-115 · Codex pre-merge chain (R1 APPROVE_WITH_COMMENTS → R3 APPROVE)

**DEC**: DEC-V61-115 — Workbench-first default landing + hero CTA
**Backend**: 86gs `gpt-5.4` (xhigh) · governance baseline per RETRO-V61-001
**Trigger**: Multi-file frontend change (RETRO-V61-001 risk-tier · "multi-file frontend changes >1 HTML/JS/CSS/TSX file")
**Self-estimated pass rate**: 70% (HIGH baseline; UI default-landing flip with 3 small files)
**Actual**: 3 rounds — calibration honest, slight underestimate (predicted ≥1 round, expected possible R2 nits; actual landed at 3 rounds because R2 fix introduced a sibling regression)

---

## R1 (commit a19f553) — APPROVE_WITH_COMMENTS · 2 P2

> "The landing-page flip exposes the workbench as the app's first screen without addressing its current first-load limitations."

**P2 #1 (App.tsx:42 → Layout.tsx)**: Layout's hard-coded `w-56` sidebar regresses narrow-viewport UX. At 375px viewport the new hero gets ~150px main pane, vs old `/learn` which was responsive.

**P2 #2 (WorkbenchIndexPage.tsx:48)**: Hero gated behind `api.listCases()` query. Slow or hanging `/api/cases` leaves the newly-promoted 新建案例 / 导入 STL CTAs unreachable from the default landing.

---

## R2 (commit c517687) — APPROVE_WITH_COMMENTS · 1 P2 (sibling regression from R1 fix)

> "The workbench hero change is fine, but collapsing the sidebar for all `<Layout />` routes introduces a mobile navigation regression that leaves several existing flows stranded on small screens."

**P2 #1 (Layout.tsx:52)**: R1 fix was overly aggressive — `hidden md:block` on the sidebar dropped global nav entirely below md, but Layout-mounted routes (DashboardPage / CaseListPage / DecisionsQueuePage / AuditPackagePage) don't render their own back-nav. A mobile user reaching one of those routes (via `/learn → /pro` or case-detail → audit-package links) would be stranded with no in-app navigation.

R2 hero fix (P2 #2 from R1) accepted clean: hero rendered before query branching, refCasesBody handles its own loading/error/data states.

---

## R3 (commit 6568164) — APPROVE clean

> "The change appears to implement the intended below-md top-bar reflow without introducing a clear functional regression in the modified code. I did not find a deterministic routing, state, or layout breakage attributable to this commit."

R2 P2 fix landed: sidebar reflows to a horizontal scrollable top-bar below md instead of being hidden. Same NavLinks remain reachable from every viewport. Phase-label chips + buyer-bridge subtitle + footer attribution collapse below md to keep the top-bar single-line.

---

## Substantive convergence audit

| Round | Commit | Verdict | P1 | P2 | P3 | Total | Notes |
|-------|--------|---------|----|----|----|-------|-------|
| R1 | a19f553 | APPROVE_WITH_COMMENTS | 0 | 2 | 0 | 2 | original landing-flip findings |
| R2 | c517687 | APPROVE_WITH_COMMENTS | 0 | 1 | 0 | 1 | sibling regression from R1 fix |
| R3 | 6568164 | APPROVE clean | 0 | 0 | 0 | 0 | converged |

**Substantive convergence**: R3's clean APPROVE confirms the responsive sidebar reflow + hero unconditional-render pattern stabilized. No new findings on the modified surface.

---

## Methodology validation · "preemptive-audit calibration anchor revisited"

V61-115 deviates from the V61-113 / V61-114 1-round preemptive-audit pattern. Why:

- V61-113 / V61-114 were *applying lessons from prior chain reports* to a sibling surface — the audit was the work, the implementation was mechanical
- V61-115 is a *new product-decision surface* — UI default-landing flip with a fresh acceptance contract (engineer-first vs. buyer-first). Codex caught two real product-quality issues (responsive UX regression + loading-gate stranding CTAs) that no prior chain report would have surfaced because they're specific to the new contract.

This validates that the preemptive-audit anchor (~80-90% pass rate) is **scoped to "applying known methodology to known sibling surface"** — fresh product surfaces revert to the broader UI-change baseline (~50-70% pass rate, 2-3 rounds typical).

R1 finding density (2 P2 / 0 P1) is the natural cost of "engineer-first UI redesign" — visible-from-day-1 changes catch responsiveness + loading-gate concerns that backend-only DECs don't surface. RETRO-V61-001 candidate intake: track "round count by DEC category" so future arcs can predict round count from DEC type.

---

## Sibling-regression learnings

R1 → R2 introduced a regression: fixing the responsive UX (`hidden md:block`) created a new accessibility issue (stranded mobile users on Layout routes). This is the **classic "remediation creates sibling defect" pattern** that V61-053 RETRO addendum identified for post-R3 defects. Here it surfaced inside the chain (Codex caught it at R2) — a positive case for chain-driven remediation:

- The R1→R2 fix worked at the local level (workbench hero became responsive) but failed at the cross-cutting level (other Layout consumers)
- Codex's R2 review explicitly traced the strand-points: 4 routes (Dashboard / Cases / Decisions / AuditPackage) without their own back-nav
- The R2→R3 fix took the harder-but-correct path (reflow, not hide) addressing all 4 strand-points uniformly

**Lesson for future UI changes**: when fixing a layout primitive (Layout / TopBar / Sidebar), enumerate ALL routes that consume the primitive before fixing — Codex implicitly did this enumeration in R2 P2 finding text. Future DEC intake template can preemptively list "Layout consumers count" as a risk_flag.

---

## Self-pass-rate calibration

Predicted: 70% (HIGH baseline · 3 small files, ~100 LOC, possible 1-2 rounds, possible P3 nits)
Actual: 3 rounds, 2 P2 + 1 P2 (no P1, no P3)

Predicted P3 nits, got P2s instead — calibration miss on **finding-severity** but accurate on round-count direction. Lesson: UI changes default to P2 not P3 because they're user-visible.

**NEW calibration anchor**: "engineer-first UI redesign with new contract" → ~70% / 2-3 rounds typical. Distinct from preemptive-audit anchor (~80-90% / 1 round).

---

## Counter impact + arc retro trigger

V61-115 acceptance advances `autonomous_governance_counter_v61` 73 → 74. RETRO-V61-001 cadence rule #2 (counter ≥20 since prior retro · last anchor RETRO-V61-V107-V108 at counter 53 → arc retro at counter 73) was **already triggered before this DEC** — explicitly deferred per user 2026-05-04 mandate "全都按你的建议来" with the 5-DEC arc plan A→C→B→D→E. Retro slot is between arc items C and B (task #23, after V61-116 lands). Counter at retro time will be 76 (74 V61-115 + 75 V61-116 + arc retro itself counts as +0 per RETRO-V61-001).

---

## Cross-referenced artifacts

- DEC-V61-115: `.planning/decisions/2026-05-04_v61_115_workbench_default_landing_hero.md`
- Implementation commits:
  - R1: `a19f553` — feat(workbench): default landing flip + hero CTA
  - R2: `c517687` — fix(workbench): address Codex R1 P2 findings
  - R3: `6568164` — fix(layout): reflow sidebar to top-bar below md
- Surface scan: `ui/frontend/src/App.tsx:39 + :103` + `ui/frontend/src/pages/workbench/WorkbenchIndexPage.tsx:41-67` + `ui/frontend/src/components/Layout.tsx` (later required after R1 P2 #1) · disposition `extend existing`
- Files touched: `ui/frontend/src/App.tsx` (redirects) · `ui/frontend/src/pages/workbench/WorkbenchIndexPage.tsx` (hero + responsive padding) · `ui/frontend/src/components/Layout.tsx` (responsive sidebar reflow)

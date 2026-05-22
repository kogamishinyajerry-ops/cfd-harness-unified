---
decision_id: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
title: Workbench dynamic guided UX — strategic pivot from audit-engine depth to full-flow usability
status: Accepted
proposed_date: 2026-05-22
accepted_date: 2026-05-22
parent_dec: null
phase: M3.0 (post-audit-engine-deepening phase open)
notion_sync_status: synced 2026-05-22 (https://www.notion.so/368c68942bed8101addfec935a50691a)
autonomous_governance: false
counter_status: v6.1 N/A (external gate · user-ratified pivot)
charter_class: true
scope_class: charter
ssot: .planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md
supersedes_in_scope:
  - "Future audit-engine `<X>_contract` charters (frozen)"
  - "blueprint v3 region 'fixed-content' interpretation (content now dynamic)"
preserves:
  - DEC-V61-198 (advisor-not-driver)
  - DEC-V61-133 (v2.3 governance simplification)
  - V130 four-question gate
  - Blueprint v3 4-region layout (REGIONS stable; CONTENT dynamic)
---

## Why (the strategic shift)

User explicit pivot 2026-05-22 (verbatim in memory `feedback_cfd_workbench_dynamic_guided_pivot`):

> "我认为不能重蹈覆辙，之前就是过早的加深强化项目本身的CFD能力，但是我的竞争优势实际上应该在全流程的可用性上，也就是新手用户或者中等的CFD工程师能不能在项目的指导下，能在项目里被逐步引导完成自己想做的一般复杂度的CFD仿真（类似于自动化，逐步在项目给的动态UI界面里，完成case的逐步搭建），工作台不要被固化，而是根据当前步骤，算例最需要解决的问题、补充的信息、关注的区域来决定当前UI显示什么内容。"

Translated as governance:
- **Stop deepening audit engine.** Cycles 3 / 5 / 6 hit diminishing returns: each charter closes one physics regime but the AVERAGE CFD user still can't construct a case in the first place. The competitive advantage is NOT "the deepest audit schema" — it is "the workbench that walks beginners through complete workflows."
- **Competitive advantage = full-flow usability for CFD beginners + mid-engineers.** Expert users don't need the workbench. The target market is people who have done one CFD class and need help getting from empty directory to converged result.
- **Dynamic workbench, NOT static layout.** UI content (per V3's 4 regions) MUST be driven by: (1) current step, (2) the case's most-pressing problem, (3) the next info gap, (4) what area of the case the user is focused on.

This is the project's most consequential strategic pivot since DEC-V61-198
(advisor-not-driver, 2026-05-06). Both are charter-class because both
**redefine what makes the product valuable**, not just what it does.

## What (charter scope)

### In scope (this charter establishes)

**1. SSOT document**: `.planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md`
   (landed 2026-05-22, this DEC's load-bearing artifact). It defines:
   - The 4 UI-content drivers (step / problem / info-needed / focus)
   - The 5-step spine + dynamic-content semantics
   - Anti-patterns (固化 in disguise)
   - Honored invariants (V130 / advisor-not-driver / artifacts-as-truth)
   - Success criteria for first guided-UX iteration

**2. Freeze on audit-engine deepening.** After DEC-V61-201-SUB-INGEST-VOF-CONTRACT
   (Accepted 2026-05-22 · the LAST audit-engine charter), no new `<X>_contract`
   charters until user explicitly reopens this track. Allowed audit work:
   - Bug fixes for issues exposed by workbench dogfooding
   - Spike-class (≤30 LOC + 1 test) fixes unblocking workbench users
   - Regression closures (CHANGES_REQUIRED from already-shipped Codex chains)

**3. Forbidden actions** (until user reopens):
   - Proposing new audit-engine `<X>_contract` sub-DECs
   - Spawning project-governor / marketing-director / codex-relay for new audit-engine arcs
   - Adding new fields/regimes to manifest schema beyond what existing workbench flow needs
   - Deepening any single audit gate (bc_contract / mesh_contract / solver_execution / etc.) beyond what existing flow needs

**4. Amendment to blueprint v3**: "UI 四区域稳定布局" is amended —
   regions stay stable but **content within each region MUST be dynamic per step + case state.** Static-layout interpretations are explicitly anti-pattern.

**5. Extension to the 4Q gate**: add a 5th informal question to every
   workbench-track PR / DEC / UI change:
   > Does this serve the guided UX scenario (beginner/mid CFD engineer
   > constructs a case step-by-step in the dynamic UI)?

   If "no, it deepens the audit engine" → reject. If "yes, plus it has a
   side benefit of audit-engine improvement" → accept the side benefit
   only if it lands as a spike-class commit, not a new charter.

### Out of scope (deferred to sub-charters / sub-DECs)

- **Implementation of the dynamic state machine** (`decide(CaseState)` backend + frontend) — separate sub-DEC chain (M3.0 cycle 1+).
- **Manifest PATCH endpoints** — separate sub-DEC.
- **case_007 dogfood of full guided flow** — verification step at end of M3.0 cycle 1.
- **Non-OpenFOAM backends** — even further out; not in this charter's footprint.

## Authorities & gating

- **autonomous_governance: false** — this is a user-ratified strategic pivot
  (the user said it explicitly), not autonomous. External-gate class per
  v6.1 telemetry. Counter += 0.
- **No Codex review required for the SSOT + this DEC** — the SSOT is
  product-spec text describing a user requirement; nothing to verify
  against code. Sub-DECs that implement the dynamic state machine WILL
  go through Codex per risk-tier (frontend + backend routes likely
  trigger 1-sync touchpoints for security boundary if any new API surface).
- **No Kogami review required** — Kogami opt-in only (v2.3). This pivot
  is large but the rationale is direct quote from user; Kogami add value
  here would be re-litigating a decision already made.

## Why charter-class (not sub-DEC)

Per v2.3 §"DEC scope-driven":
- **Affects ≥3 shared code paths**: workbench frontend (multiple pages) +
  workbench backend (route descriptors + manifest patch endpoints) +
  audit-engine consumption layer (problems list → UI). Far more than
  3 modules.
- **Governance-rule-change**: freezes a class of future work (audit-engine
  charters). This is the precise kind of decision the charter-class
  rule exists to capture.
- **Strategic redefinition**: same class as DEC-V61-198 (advisor-not-driver)
  and DEC-V61-133 (v2.3 governance pivot). Both were charter-class.

## Closure criteria

This DEC becomes Accepted (and the pivot operative) when:

- [x] SSOT doc landed at `.planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md`
- [x] Memory anchor saved at
      `~/.claude/projects/-Users-Zhuanz/memory/feedback_cfd_workbench_dynamic_guided_pivot.md`
- [x] This DEC body lands with status=Accepted + frontmatter complete
- [x] DEC frontmatter flipped Proposed → Accepted (this commit)
- [ ] Notion sync (Decisions DB) — batched at session end per v2.3 rule "Notion only mirrors Accepted DECs"
- [x] DEC-V61-201-SUB-INGEST-VOF-CONTRACT confirmed as the last
      audit-engine charter (Accepted 2026-05-22; if any new audit-engine
      sub-DEC slips through before this DEC's Accepted flip, it must be
      withdrawn or rebased onto the spike-class exemption).

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| Pivot gets bypassed by "just one more" audit-engine charter | This DEC explicitly enumerates forbidden actions. Catch in PR review. |
| Dynamic UX implementation degrades into LLM-driven (V130 violation) | SSOT §6 explicitly preserves "advisor-not-driver"; `decide(CaseState)` is a pure function of state, not an LLM call. |
| State machine becomes overcomplicated (over-engineering risk per V133 retro lessons) | Start with 3 dynamic slots (rail.primary / viewport.overlays / bottom.cards). Add more only when dogfooding shows need. |
| Audit-engine bug fixes get blocked because "no new audit work" | Charter explicitly carves out spike-class fixes + regression closures. Bug fixes are allowed; new charters aren't. |
| Pivot is too abstract; engineering team has nothing concrete to start | Sub-DEC for M3.0 cycle 1 follows immediately: minimum `decide(CaseState)` + 3 dynamic slots + case_007 dogfood. |
| User reopens audit-engine track mid-implementation | Allowed — they're the user, and the pivot is explicitly THEIR call. Reopening just flips this DEC's "forbidden actions" off. |

## Related artifacts

- **SSOT**: `.planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md` (the load-bearing product spec)
- **Memory**: `feedback_cfd_workbench_dynamic_guided_pivot` (the rule)
- **Predecessor strategic pivot**: DEC-V61-198 (advisor-not-driver, 2026-05-06)
- **Predecessor governance simplification**: DEC-V61-133 (v2.3, 2026-05-07)
- **Final audit-engine charter**: DEC-V61-201-SUB-INGEST-VOF-CONTRACT (Accepted 2026-05-22)
- **Blueprint v3 INDEX** (4-region layout, amended)
- **Blueprint v9 INDEX** (post-run advisor surface — composes; advisor cards become bottom-panel content per driver 2)

## Status

**Accepted (2026-05-22).** User-ratified strategic pivot — the pivot itself
was direct user utterance, the SSOT was written + landed per Q2, the
charter body lands per Q3, and the audit-engine freeze is operative as of
DEC-V61-201-SUB-INGEST-VOF-CONTRACT's Accepted flip (also 2026-05-22).

Notion sync queued for session-end batch per v2.3 rule.

## Provenance

User message capturing the pivot (verbatim, 2026-05-22 mid-cycle-6):

> 我认为不能重蹈覆辙，之前就是过早的加深强化项目本身的CFD能力，但是我的竞争优势实际上应该在全流程的可用性上，也就是新手用户或者中等的CFD工程师能不能在项目的指导下，能在项目里被逐步引导完成自己想做的一般复杂度的CFD仿真（类似于自动化，逐步在项目给的动态UI界面里，完成case的逐步搭建），工作台不要被固化，而是根据当前步骤，算例最需要解决的问题、补充的信息、关注的区域来决定当前UI显示什么内容。

User AskUserQuestion answers (2026-05-22 same exchange):
- Q1 (Cycle 6 disposition): "推完当最后一个 audit charter 收尾"
  → cycle 6 ships as FINAL audit-engine charter (done · DEC-V61-201-SUB-INGEST-VOF-CONTRACT Accepted)
- Q2 (Next focus): "先写'新手用户引导流程'SSOT文档"
  → SSOT doc landed first (done · `GUIDED_CASE_CONSTRUCTION_FLOW.md`)
- Q3 (Pivot DEC): "写完整 charter-class DEC"
  → this DEC (charter-class, full body)

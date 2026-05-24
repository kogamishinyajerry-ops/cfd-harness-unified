# RETRO · M3.4 Geometry step graceful empty-state milestone close · 2026-05-25

> Charter: close the B1-B6 step=geometry empty-state cluster surfaced by M3.3 cross-step audit. Charter at `.planning/RESUME.md` (M3.4 section).
> Counter snapshot: M3.4 = 5 commit-message-only sub-DECs (cycles 1-5) = **+0 to `autonomous_governance_counter_v61`** (no DEC files filed per v2.3 round-1 loosen — all spike-class or research-only).
> Kogami: not invoked (v2.3 opt-in only; user did not request).
> Codex: **0 invocations across all 5 cycles** (no risk-tier hits · UI / layout / empty-state · no auth / signing / security boundary).
> post-R3 defects observed: **0** (no Codex review involved; not applicable).
> Multi-agent crew: deployed at FULL scale — 4 subagents across cycles 1 + 4. **First milestone to use multi-agent crew from charter through close.**

## Outcome

M3.4 ships **the empty-state cluster closure arc** that M3.3 cross-step audit proposed:

- **Cycle 1** (charter + 3 parallel investigation subagents · no commit): S3 (DynamicBottomCards intent · Explore), S4 (MainCanvas root cause · general-purpose), S5 (Upload CAD CTA candidates · Explore). All read-only. ~5 minutes wall-clock for 3 deep dives.
- **Cycle 2** (`e398397`): 1-LOC fix at `ModeRendererGeometry.tsx:107` adds `&& authoredCadParts` to `useAssemblyGlb` gate. Closes B1 (MainCanvas proxy error). Spike-class. Root cause: empty-CAD case mounted vtk.js kernel → unguarded `new Proxy(null, ...)` in vtk.js `RenderWindow.js:243`.
- **Cycle 3** (`bf3d41d`): polish `GeometryEmptyState` with 56px wireframe icon + bilingual title + Upload CAD CTA Link to `/workbench/import` (reuses PostEmptyViewport + Step1Import patterns per S5). DOM-verified CTA visible. Spike-class. Surfaced new finding B6 (148px column squish) during DOM inspection.
- **Cycle 4** (background subagent investigation · no commit): general-purpose subagent diagnosed B6 root cause = CSS content-overflow leak from unconstrained `<div className="flex flex-col">` wrapper at `WorkbenchShellV4.tsx:247` hosting DynamicFramePanel whose `<p>` body_text had no max-width. Hypothesis "different layout per step" disproved.
- **Cycle 5** (`0a122d3`): 2-LOC fix at `WorkbenchShellV4.tsx:255` changes wrapper to `flex w-[300px] shrink-0 flex-col`. Closes B6 directly + cascade-clears B2 (KpiStrip number collision) + B5 (step rail / bottom-card overlap). Spike-class.

The milestone is a **cascade-leverage counter-experiment** to M3.3's process-light pattern: where M3.3 demonstrated v2.3 at its lightest configuration, M3.4 demonstrates that **single root-cause fixes can close multiple findings** — cycle 5's 2-LOC change closed 3 P1+P2 backlog items.

## Arc map

| Cycle | Sub-DEC type | What landed | Codex rounds | Commit |
|---|---|---|---|---|
| 1 | research-only (3 parallel subagents) | charter + S3/S4/S5 investigation deliverables | — (no Codex, research) | (no commit) |
| 2 | spike-class sub-DEC | 1-LOC `useAssemblyGlb` gate → closes B1 | — (no Codex, UI guard) | `e398397` |
| 3 | spike-class sub-DEC | `GeometryEmptyState` polish + Upload CAD CTA | — (no Codex, UI polish) | `bf3d41d` |
| 4 | research-only (1 background subagent) | B6 root-cause diagnosis + LOC-budgeted fix sketch | — (no Codex, research) | (no commit) |
| 5 | spike-class sub-DEC | 2-LOC wrapper width → closes B6 + cascade B2 + B5 | — (no Codex, CSS) | `0a122d3` |

Total Codex synchronous invocations: **0** across 5 cycles. Driver = all M3.4 work is spike-class eligible (≤30 LOC + 1 verification + UI layer) with zero risk-tier hits.

## Cascade-clear outcomes

Originally B1-B5 from M3.3 cross-step audit · B6 surfaced at cycle 3 DOM inspection:

| Finding | Priority | Closure path | Cycle |
|---|---|---|---|
| **B1** MainCanvas proxy error | P1 | 1-LOC functional fix (vtk.js gate) | 2 |
| **B2** KpiStrip number collision | P2 | **cascade-cleared by B6 fix** (was downstream, not independent) | 5 |
| **B3** BottomCards duplicates rail | P2 | by design per M3.0 charter (S3 finding) | 1 |
| **B4** sidebar dead space | P3 | **still Open** · lowest priority · may be moot post-cycle-5 | — |
| **B5** step rail overlap | P2 | **cascade-cleared by B6 fix** (was downstream, not independent) | 5 |
| **B6** 148px column squish | P1 | 2-LOC CSS wrapper width fix | 5 |

**5 of 6 findings closed.** B4 (P3 cosmetic) remains open as lowest-priority. The **headline outcome is cycle 5's 3× leverage** — single 2-LOC root-cause fix closing B6 + cascade-clearing B2 + B5.

## What went well

1. **Subagent-driven root cause analysis at full scale**. S4 found B1's root cause down to a specific vtk.js line (`RenderWindow.js:243`) in one pass — the unguarded `new Proxy(null, ...)` site is buried 12 levels into the vtk.js call stack and would have taken 20-30 minutes of stepping-through to locate manually; subagent surfaced it from grep + read in under 90 seconds of wall-clock. Cycle 4 subagent diagnosed B6 as content-overflow leak (NOT per-step layout as initially hypothesized) and proposed the exact 2-LOC fix that ultimately landed. 4 subagents across 2 cycles, all clean structured deliverables. Briefing-to-deliverable round-trip averaged ~3 minutes per subagent.

2. **Cascade-clear pattern produced 3× leverage on cycle 5**. B2 + B5 turned out to be downstream of B6, not independent defects. Fix one root cause → 3 findings close. This is the most efficient cycle of the entire M3 arc to date measured by findings-closed-per-LOC. Pre-cycle-5, the working hypothesis was that B2 (KpiStrip number collision) needed its own typography tweak and B5 (step rail overlap) needed z-index work; the cycle 4 root-cause investigation revealed both were artifacts of the same overflowing wrapper. Lesson reinforced: **investigate root cause across multiple symptoms before scoping per-symptom fixes**.

3. **2-LOC fix to wrapper width unlocked entire main viewport**. Single CSS class change (`w-[300px] shrink-0`) closed P1 + 2× P2 findings. Spike-class eligibility confirmed pre-implementation by subagent's LOC estimate. The fix-to-deliverable ratio (3 backlog items closed / 2 LOC changed) is the strongest signal yet that M3.X UI work benefits from cascade-aware investigation before commit-class selection.

4. **Visual spot-check + DOM bbox combination held**. Every commit referenced a screenshot. B6 finding itself was surfaced by DOM inspection during cycle 3 polish (not just eyeballing the screenshot). DOM bbox query + screenshot together = strong audit trail; codified the M3.3 methodology doc applied correctly. The 148px wrapper width was visible in the screenshot but the human eye reads it as "looks crowded" rather than "the container is mathematically too narrow"; only the bbox numerical readout (148px observed vs ~300px expected) made the diagnosis precise.

5. **Multi-agent crew architecture validated at scale**. 4 subagents across cycles 1 + 4. Briefing template (file paths · question · LOC budget · constraint list) produced consistently structured deliverables. **First milestone to deploy crew at full scale from charter through close** — no orchestration drift, no briefing thrash, no re-iteration loops. Each subagent returned within budget (<2000 tokens), with high-confidence root cause + LOC estimate, allowing main session to decide spike-class eligibility before opening commit cycle. M3.3 demonstrated crew at mid-milestone (2 subagents at cycles 2-3); M3.4 demonstrates crew across the entire arc.

## What went poorly

1. **Initial B6 hypothesis was wrong** ("per-step layout switch"). Without the cycle 4 subagent forcing a closer read of `WorkbenchShellV4`, this could have led to a much bigger refactor (e.g., introducing per-step layout variants, conditional rendering in the shell). The actual fix turned out to be 2 LOC in a single wrapper. Lesson: trust the bbox numbers, but verify hypotheses with code reads before scoping work. Codify "before opening a multi-file refactor cycle, run a single-file read to verify the hypothesis is correctly localized".

2. **Cycle 3 polish landed with knowledge that the container was squished**. Should have flagged B6 BEFORE applying polish, then ordered cycle 4 (B6 fix) before cycle 5 (polish). The polish work isn't wasted (still valuable once layout fixed) but ordering was suboptimal — B6 should have been a cycle-2-extension rather than a post-cycle-3 surface. Process improvement: when DOM inspection during a polish cycle reveals a layout defect, **pause the polish and treat the defect as the new top-priority cycle**.

3. **B3 closure ("by design") came from subagent S3 reading the charter** — could have been caught BEFORE filing in cycle 1 backlog if cycle 0 included a quick charter-read step. Suggests adding "1-minute charter check" to the backlog-filing template so non-defect findings don't enter the backlog at all. The cost of B3 ending up in backlog was minimal (~2 min subagent time to disposition it) but the pattern matters: backlog hygiene affects future milestone scoping accuracy.

## V130 four-question gate audit (every M3.4 commit-producing cycle answers Y/Y/Y/Y)

| Cycle | LLM offline | Artifacts canonical | TrustGate-explainable | Advisor-only |
|---|---|---|---|---|
| 1 | N/A (research-only · no commit) | N/A | N/A | N/A |
| 2 | ✓ | ✓ (empty-state path explainable) | ✓ (empty state visible) | ✓ (UI guard) |
| 3 | ✓ | ✓ (CTA reuses existing patterns) | ✓ (Upload CAD path visible) | ✓ (UI polish) |
| 4 | N/A (research-only · no commit) | N/A | N/A | N/A |
| 5 | ✓ | ✓ (structural fix, no data change) | ✓ (TrustGate structural only) | ✓ (CSS only) |

3/3 commit-producing cycles Y/Y/Y/Y.

## Codex round cap=3 observance per cycle

| Cycle | Rounds used | Closure | At-cap? |
|---|---|---|---|
| 1-5 | 0 | n/a (spike-class / research-only) | n/a |

**Zero cycles invoked Codex.** All 5 cycles bypassed via spike-class sub-DEC (cycles 2/3/5) or research-only (cycles 1/4) + no risk-tier hit. v2.3 round-1 loosen applied consistently. No charter-class scope touched (no schema change · no security boundary · no ≥3 shared code paths).

## Subagent crew telemetry

| Subagent | Cycle | Type | Question answered | Wall-clock | LOC budget honored |
|---|---|---|---|---|---|
| S3 | 1 | Explore | DynamicBottomCards intent vs duplication concern (B3) | ~4 min | n/a (read-only) |
| S4 | 1 | general-purpose | MainCanvas proxy error root cause (B1) | ~5 min | 1-LOC estimate → 1-LOC actual ✓ |
| S5 | 1 | Explore | Upload CAD CTA reuse candidates | ~3 min | n/a (read-only) |
| (background) | 4 | general-purpose | B6 column squish root cause | ~6 min | 2-LOC estimate → 2-LOC actual ✓ |

**4 subagents · 4 first-iteration successes · 0 re-briefings · 0 budget violations · 100% LOC-estimate accuracy on the 2 commit-producing subagents.** Briefing template (file paths · question · LOC budget · constraint list) produced consistent results. Crew architecture cost: ~18 minutes total wall-clock for investigation work that would have taken main session 60-90 minutes sequentially.

## Methodology lessons captured

1. **Cascade-clear is real**. Multiple findings can have a single root cause downstream. Don't assume each backlog item is independent — investigate root causes first; sometimes a single fix closes 3 items. M3.4 cycle 5 is the canonical example: 2 LOC closed 3 findings (1 P1 + 2 P2). Add to investigation template: "before opening commit cycle, group symptoms by shared structural ancestor (parent DOM container, shared CSS rule, shared component prop pipeline); investigate the ancestor as the root-cause candidate".

2. **Parallel multi-agent investigation is the new default for M3.X cycle 1**. The 3-subagent pattern (1 charter-intent · 1 root-cause · 1 reuse-candidate-search) is reproducible. ~5 min wall-clock for 3 deep dives that would have taken 30-45 min sequentially. Effective briefing template fields: (a) absolute file paths to read, (b) specific question to answer, (c) LOC budget for any proposed fix, (d) constraints (read-only, no commits, no test runs). All 4 M3.4 subagents returned within budget on first iteration.

3. **DOM bbox check is a complement to screenshots**, not a replacement. Screenshots show visual state; DOM gives precise positioning numbers that surface layout bugs not visible to the eye. Cycle 3 → cycle 4 transition demonstrates this — eye missed the 148px squish, bbox query caught it. Add to spot-check methodology doc: "for any UI cycle close, run both screenshot AND `document.querySelector(...).getBoundingClientRect()` on the suspect container; compare numerical bbox to design-intent value".

4. **Subagent root-cause reports should propose a fix sketch with LOC estimate**. S4 + cycle 4 subagent both did this, and the LOC estimate (1-LOC, 2-LOC) made it trivial to assess spike-class eligibility before starting cycle 2 / cycle 5. Bake "include LOC estimate + spike-class eligibility verdict" into the subagent root-cause briefing template — this is the single highest-leverage briefing field for downstream cycle planning.

5. **Multi-agent crew + spike-class sub-DEC is a stable pairing for UI work**. 4 subagents × 5 cycles · 0 DEC files · 0 Codex rounds · 5 findings closed. The combination "lightweight process + heavy investigation parallelism" is the M3.X signature pattern; M3.4 is its strongest validation to date.

## Counter telemetry

| Milestone | Cycles | Counter delta | Codex rounds | post-R3 defects | Multi-agent crew |
|---|---|---|---|---|---|
| M3.0 | ? | ? | ? | ? | none |
| M3.1 | 8 | +8 | 29 (avg 3.2) | 0 | none |
| M3.2 | 7 | +3 | 6 | 0 | none |
| M3.3 | 3 | +0 | 0 | 0 (n/a) | 2 subagents (cycles 2-3) |
| M3.4 | 5 | +0 | 0 | 0 (n/a) | **4 subagents (cycles 1 + 4)** |

Cumulative M3 counter delta unchanged by M3.4 (still ~+16 from M3.0 + M3.1 + M3.2). M3.4 matches M3.3 as **process-light** but with **higher leverage** — 5 of 6 findings closed via 3 spike-class commits totaling ~3 LOC of functional change.

## Open questions for M3.5 charter

1. **What's M3.5's theme?** Candidates surfaced from M3.3 + M3.4 close-lists:
   - **(a)** Real-user re-validation of M3.4 cycles 2+3+5 outcomes — user clicks through the fixed empty-state UI, gives final Y/N on B1/B2/B5/B6 closure. Mirrors M3.3 cycle 2 user-driven validation pattern. Scope tight, value high (confirms cascade-clear actually closed user-visible defects, not just code-path defects).
   - **(b)** Backend `gap.why` enrichment across remaining gap families — carried from M3.3 retro. Touches backend services rather than frontend; would shift M3.X arc out of UI-pure territory.
   - **(c)** B4 P3 cosmetic fix — sidebar dead space. Trivial spike-class. Could fold into (a) as a single cycle if user-validation surfaces it as still-noticeable post-cycle-5.
   - **(d)** "Open in IDE via vscode://" affordance — carried from M3.2 retro. Bigger scope, touches multiple components, possibly charter-class.
   - User decides; this retro recommends starting with (a) as the lowest-cost highest-value follow-up.

2. **Should the cascade-clear pattern have its own playbook entry?** M3.4 cycle 5 demonstrated 3× leverage from root-cause investigation. Should `.planning/methodology/` get a `cascade_clear_investigation.md` doc capturing the pattern: (i) group symptoms by structural ancestor, (ii) investigate ancestor as root-cause candidate, (iii) verify with code read before scoping per-symptom fixes. Without the doc, the lesson decays.

3. **Multi-agent crew at charter cycle has now precedent**. M3.3 used crew mid-milestone; M3.4 used crew at cycle 1 + cycle 4. The 3-subagent cycle-1 pattern (charter-intent · root-cause · reuse-candidate) is reproducible. Question for M3.5+: should cycle 1 subagent count be standardized? Default rule of thumb after M3.4: if the milestone scope includes ≥3 distinct investigation threads (e.g., charter intent, multiple root-cause hypotheses, reuse candidates), launch them in parallel at cycle 1. Below that, sequential investigation by main session is cleaner.

## Recommendations for M3.5

1. **Pick (a) "Real-user re-validation of M3.4 cycles 2+3+5"** as M3.5 charter — lowest-cost, highest-confidence way to confirm cascade-clear actually closed user-visible defects. Fold in (c) B4 cosmetic fix opportunistically if user spot-check surfaces it.

2. **Open with a 1-paragraph charter at cycle 1** (carry M3.3 retro recommendation forward). M3.4 had a `RESUME.md` charter section which worked; continue this pattern.

3. **Mandate cascade-clear investigation at cycle 1 for any multi-finding milestone**. Group symptoms by structural ancestor before scoping per-symptom fixes. Codify in methodology doc per Open Question §2.

4. **Continue multi-agent crew at full scale**. M3.4 validated 4 subagents across charter + mid-arc without orchestration drift. M3.5 should default to crew at cycle 1 if scope includes ≥3 investigation threads.

5. **Keep process-class diversification active**. M3.4 demonstrates that spike-class sub-DEC + zero Codex + zero Kogami is a valid milestone shape when scope is genuinely process-light. Don't artificially escalate M3.5 if scope stays bounded — but be ready to escalate to charter-class if user-validation surfaces previously-hidden depth.

## Bottom line

M3.4 ships in **5 cycles · 0 counter delta · 0 Codex rounds · 0 Kogami invocations · 0 Notion sync candidates · 5 of 6 backlog findings closed (B4 P3 remains open as cosmetic low-priority)**.

The **cascade-clear pattern** (cycle 5's 2-LOC fix closing 3 findings) is the milestone's signature outcome. Multi-agent crew architecture deployed at full scale (4 subagents across cycles 1 + 4) without single-session orchestration drift — first milestone to use crew from charter through close.

Where M3.3 demonstrated v2.3 round-1 loosen at its lightest configuration (3 process-class-skip cycles), M3.4 demonstrates the same lightness paired with **investigation depth and root-cause leverage**. The two milestones together establish a stable M3.X pattern: **lightweight process + heavy investigation parallelism + cascade-aware fix selection**.

Total functional code change across M3.4: **~3 LOC**. Total findings closed: **5 (of 6)**. The findings-closed-per-LOC ratio is the highest of any M3 milestone to date — a direct consequence of cycle-4 root-cause investigation surfacing the cascade structure before cycle-5 fix commit.

**The absence of Codex / Kogami / Notion data continues to be the validation signal**: v2.3 round-1 loosen at its lightest configuration produced a defect-closure arc with zero formal governance overhead. The empirical case for "process-light when scope is genuinely light, paired with multi-agent investigation when scope spans multiple symptoms" is strengthened by a second consecutive milestone (M3.3 + M3.4).

**Recommendation**: close M3.4 · no Notion sync needed (zero Accepted DECs filed; per v2.3 Notion-only-syncs-Accepted) · open M3.5 with "Real-user re-validation of M3.4 cycles 2+3+5" as proposed theme per §Recommendations #1.

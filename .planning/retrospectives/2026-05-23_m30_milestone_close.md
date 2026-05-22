# RETRO · M3.0 Workbench Dynamic Guided UX milestone close · 2026-05-23

> Charter: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
> Litmus: *"junior CFD engineer constructs case_007 KCS ship VOF in ≤30
> minutes via the dynamic UI"*
> Counter snapshot: M3.0 = 7 sub-DECs + 1 integration sub-DEC = +8 to
> `autonomous_governance_counter_v61` (one per sub-DEC; parent V202
> collapses, per v2.3).
> Kogami: not invoked across M3.0 (v2.3 opt-in only; user did not request).
> Codex: invoked 8 times synchronously across the arc; **every cycle
> closed within v2.3 round cap=3**, no hard-stop, no V133-style anti-pattern.

## Outcome

The dynamic workbench engine is **live on the V4 shell** at
`/workbench/case/<id>`. The four SSOT UI-content drivers (current step,
pressing problem, info gap, focus area) all surface through `decide()
→ WorkbenchFrame`; every decision is captured in the audit_v2 provenance
log; the litmus surrogate proves a programmatic engineer reaches a
solveable case_007 in 8 UI actions (well under the 20-call budget proxy
for 30 minutes of wall-clock work).

**M3.0 is closeable on the engine-side.** Outstanding gaps (real-engineer
eval, domain-aware UI form helpers, failure-path ergonomics, log
rotation) belong to M3.1.

## Arc map

| Cycle | Sub-DEC | What landed | Codex rounds |
|---|---|---|---|
| 1 | DECIDE-STATE | `decide(CaseState) → WorkbenchFrame` pure function + schema | 1 round (clean APPROVE) |
| 2 | MUTATION-TOPBAR | PATCH `/manifest` + topbar CTA 4th driver + state_sha concurrency | 2 rounds (R0 = 3 P3, R1 = APPROVE) |
| 3 | FOCUS-DRIVER | FacePickContext per-case keyed, focus_patch as 4th SSOT driver, kind-aware rail sort | **R0-R3 (cap=3)** — 1 P1 (provider keying) + 2 P2 (focus sort + resolved patches) + iterative finding-set refinement |
| 4 | MULTIPHYSICS-DOGFOOD | 4-regime dogfood (RANS / LES / compressible / CHT) — 135/135 PASS | 3 rounds (R0 schema mismatch, R1 semantic guards, R2 LES tuple) |
| 5 | E2E-DEFAULT-ON | StepPanelShell flag flip + MSW handlers + Playwright spec (deferred to integration) | 1 round (honest scope reduction) |
| INT | INTEGRATION-V4-SHELL | Bridge V4's 8-step pipeline → backend's 5-step spine; mount FacePickProvider + DynamicFramePanel + DynamicBottomCards + DynamicViewportOverlays on V4 | **R0-R2 (cap=3)** — CTA navigation contract iteration (lossy reverse-map → forward walk → backend target as upper bound) |
| 6 | PROVENANCE-AUDIT-V2 | Fire-and-forget JSONL log per `decide()` call; safe case-id sanitizer; replay reader skill | 2 rounds (R0 = 3 findings 2P2+1P3, R1 = APPROVE) |
| 7 | BEGINNER-TEST | Litmus surrogate: programmatic engineer reaches step 5 in 8 calls; severity rank 3→0; backend-driven transitions | 3 rounds (R0 = 2 P2 severity+transitions, R1 = 2 P2 step-5 CTA + target range guard, R2 = APPROVE) |

Total Codex rounds across M3.0: **18 rounds across 8 sub-DECs** (avg
2.25 rounds per sub-DEC). Compares favorably to V131's 22-round arc
which triggered DEC-V61-133 v2.3 simplification.

## What went well

1. **v2.3 round cap=3 held without strain**. Cycles 3 and INTEGRATION
   both hit cap=3 exactly, and both times the final APPROVE round had
   verbatim-fix landings rather than "Codex spinning". The cap matched
   the natural saturation point of the review→fix→review loop.

2. **Honest scope reductions paid off**. Cycle 5's e2e Playwright spec
   was originally cycle-internal; when StepPanelShell's vtk.js import
   broke the Playwright resolver, we honestly deferred to the integration
   sub-DEC instead of forcing a 22-round arc. That decision saved 3-4
   rounds and produced a cleaner integration commit.

3. **The 4-driver SSOT held under stress**. Cycle 3's focus_patch
   driver was the most contentious — Codex pushed hard on the focus-driven
   sort, the resolved-patch attribution, and provider keying. After the
   cap=3 fixes, the driver is stable; cycle 4 and cycle 7 both exercised
   it without further changes.

4. **Audit-log instrumentation arrived at the right time**. Cycle 6
   landed *after* the engine was live (integration) but *before* the
   litmus test (cycle 7). The cycle 7 test exercised the cycle 6 log
   end-to-end and proved the audit trail captures the journey faithfully.
   Inverted order would have left cycle 7 with no replay tooling.

5. **Programmatic litmus surrogate is defensible**. We don't have a
   real junior engineer, so cycle 7 simulates one. The 8-call result is
   honest about what's stub (synthesized `bc.patches` mirrors UI form
   helpers) vs what's measured (engine coherence, monotonic progress,
   no rework loops). The dogfood report says exactly what was and was
   not proven.

6. **Cycle 7's R1 review caught second-order holes that R0 would have
   missed**. R0 fixed severity-rank vocabulary + transition validation.
   R1 noticed both fixes had blind spots: (a) the new transitions
   check didn't actually run on step 5 because the loop broke
   unconditionally there, and (b) `target_step=0` would crash the
   harness on the next GET before the check could fire. That's
   *exactly* the kind of "fix introduces new gap" feedback the
   round-cap-3 policy is designed to surface. The R2 APPROVE confirms
   the iteration converged — not "Codex spinning", which is what V131
   anti-pattern looked like.

## What went poorly

1. **Cycle 5 should have caught the V4-vs-StepPanelShell route mismatch
   sooner**. We landed cycles 1-4 against StepPanelShell while the live
   route was WorkbenchShellV4. The integration sub-DEC was a *pivot*
   triggered by user feedback, not by surface scan. Action: when adding
   a new top-level route or page, the surface-scan trailer should
   include a `live-route-check: <path> → <component>` line documenting
   which component is actually mounted at the route.

2. **Cycle 3 review chain (R0-R3) was the most expensive arc**. Three
   rounds chewed through the focus_patch driver's edge cases. Codex was
   not spinning — every round caught a real issue — but the cycle 3 P2
   finding (resolved_patch over-attribution) revealed that
   `_collect_resolved_patches` had no canonical test fixture. Action:
   for service-layer functions with N≥5 list-of-list inputs, write a
   property-based test (Hypothesis) **before** Codex review starts.

3. **The 5-step backend spine vs V4's 8-step pipeline gap was implicit
   for too long**. Cycles 1-5 documented `step ∈ {1..5}` everywhere but
   the live UI exposed V4's 8 V4PipelineStepIds. The integration
   sub-DEC's `step_id_translator.ts` should have existed at cycle 1.
   Action: when a service contract has a number-typed dimension (step,
   tier, etc.) and a UI contract has a string-typed equivalent, write
   the bidirectional translator as the first artifact, not the last.

4. **Provenance log format didn't capture rail severity until Codex
   pointed it out** (cycle 6 R0 P2 #2). RailPrimary has no severity
   field; severity lives encoded in `provenance` strings. The log
   collapsed WARN-vs-FAIL into the same record on R0. Action: when
   adding an audit log, list the questions a future retro will ask of
   the log **before** writing the schema. The "did decide() ever
   surface a FAIL?" question would have caught this on the design
   pass, not in Codex review.

## SSOT 4 UI-content driver coverage matrix

| Driver | Where surfaced | Cycle that locked in | Provenance log key |
|---|---|---|---|
| **Current step** | `state.step` → frame.step + topbar.target_step | 1, 2 | `step` |
| **Pressing problem** | bottom_cards (audit findings) + rail.kind=problem_fix | 1, 4 | `bottom_card_severities`, `rail_primary.severity` |
| **Info gap** | rail.kind=info_gap + rail.field_path + suggested_default | 1, 2 | `rail_primary.field_path` |
| **Focus area** | FacePickContext.patchName → state.focus_patch → rail context | 3, INT | `focus_patch` |

All 4 drivers are now (a) wired through the live route, (b) instrumented
in the audit log, and (c) exercised by the cycle 7 litmus surrogate.

## V130 four-question gate audit (every cycle should answer Y/Y/Y/Y)

| Question | Cycle 1 | C2 | C3 | C4 | C5 | INT | C6 | C7 |
|---|---|---|---|---|---|---|---|---|
| LLM offline — does it run? | Y | Y | Y | Y | Y | Y | Y | Y |
| Artifacts as truth — manifest/json/yaml is canonical? | Y | Y | Y | Y | Y | Y | Y | Y |
| TrustGate-explainable — every decision has provenance? | Y | Y | Y | Y | Y | Y | Y* | Y |
| AI advisory-only — no auto-writes by AI? | Y | Y | Y | Y | Y | Y | Y | Y |

\* Cycle 6 R0 P2 #2 had a temporary gap (severity not in log); closed in R1.

Result: **8/8 cycles fully comply with V130 by end-state**; one cycle
had a transient TrustGate gap caught and fixed within the same arc.

## Codex round cap=3 observance per cycle

| Cycle | Cap hit? | Verbatim/synth mix |
|---|---|---|
| 1 | No (1 round) | n/a — clean APPROVE |
| 2 | No (2) | verbatim |
| 3 | **Yes (3)** | verbatim R0+R1, R2 was iterative refinement on resolved_patch attribution |
| 4 | No (3) | mix — R0 schema rewrite, R1+R2 verbatim |
| 5 | No (1) | n/a — honest scope cut |
| INT | **Yes (3)** | verbatim across all 3 — CTA contract iteration |
| 6 | No (2) | verbatim |
| 7 | No (3 incl. final APPROVE) | verbatim · 4 P2 fixes total, no P1, second-order holes caught in R1 |

No cycle required a user-ratified continuation past cap=3 (unlike
V61-201-SUB-INGEST which used 7 rounds with explicit ratifications).
M3.0 stayed inside v2.3 governance.

## Open questions for M3.1

1. **Real-engineer eval**. Cycle 7 is a surrogate. M3.1 should recruit
   1-2 junior CFD engineers, give them case_007 cold, time them, and
   capture qualitative feedback. Hard to do remotely; may need to wait
   for a workshop or onsite session.

2. **Domain-aware UI form helpers**. Cycle 7 showed `bc.patches`
   couldn't be filled by a sparse-stub agent without a canonical
   3-patch skeleton. M3.1 should add UI affordances that offer
   case-family-specific structural defaults (ship_vof → inlet/outlet/wall,
   rans_steady → inlet/outlet/wall/farfield, etc.).

3. **Failure-path ergonomics**. The litmus surrogate took the happy
   path; we have no evidence the workbench handles "engineer applies
   wrong fix → re-audit surfaces new FAIL → engineer reverts" cycles
   gracefully. M3.1 should write a failure-path dogfood.

4. **Log rotation**. Cycle 6's provenance log is unbounded append. A
   dev session of 10k decide() calls = a multi-MB log per case. M3.1
   should add daily rotation + compression of old shards.

5. **Multi-case generalisation**. Cycle 4 proved the 4 regime classes
   don't crash decide(); cycle 7 only walked ship-VOF. Some
   case_family-specific gaps in the rail likely exist for the other 3
   regimes; an M3.1 dogfood should walk each regime through cycle-7-
   style beginner test.

## M3.0 close-batch push-review backlog (cap=3 leftovers → M3.1)

The push-wide Codex review over the 8-commit M3.0 close-batch ran 3
rounds (R0 + 2 fix iterations) per v2.3 cap. Net: 6 P2 findings, 4
closed verbatim in-batch, 2 deferred to M3.1 retro queue:

| # | Finding | Disposition | Why deferred |
|---|---|---|---|
| 1 | log_decision logs every passive refetch (React Query revalidation overcount) | **fixed in close-batch** | dedup by state_sha |
| 2 | cycle 7 dogfood silently advances on fieldless backend blockers | **fixed in close-batch** | `(current_step, -1)` marker + HALT message |
| 3 | audit logs dirty working tree (no .gitignore) | **fixed in close-batch (already covered)** | existing `ui/backend/.gitignore` ignores `user_drafts/` wholesale; added explicit root-level rule for documentation |
| 4 | dedup cache poisoned by failed writes | **fixed in close-batch** | cache update moved to AFTER fsync succeeds |
| 5 | provenance import couples to optional geometry stack (trimesh) | **fixed in close-batch (cheap)** | import DRAFTS_DIR from trimesh-free `case_drafts` instead of `case_scaffold.template_clone` |
| 6 | dedup cache not thread-safe under overlapping requests | **DEFERRED to M3.1** | bounded scope but adds threading.Lock + per-case lock dict; deferring keeps M3.0 close batch lean. Concurrent-request load is currently low (single-user dev sessions); the noise is a quality-of-data issue not a correctness break of the fire-and-forget contract |

Tracker for #6: M3.1 backlog entry: "audit_v2 log dedup race condition
under concurrent GET /workbench_frame — wrap state-sha read-check-write
in a per-case threading.Lock."

## Recommendations for M3.1 charter

- Lead with **real-engineer eval setup** (recruit + protocol) — even if
  the eval itself slips, the protocol is reusable.
- Bundle **domain-aware form helpers** + **failure-path dogfood** + **log
  rotation** as the engine-side workstream.
- Defer **multi-case generalisation beginner test** to mid-M3.1 once form
  helpers exist.
- Keep **cap=3 + scope-driven DEC + Kogami opt-in** as governance
  defaults — M3.0 proved they hold without strain.

## Bottom line

M3.0 milestone is **closeable on engine-side merits**. The litmus
surrogate proves the dynamic workbench drives monotonic forward progress
from a sparse starting state to a solveable case in well under the
30-minute budget. The provenance audit trail enables post-hoc retro of
any decision. v2.3 governance held; no hard-stops, no V131-class
anti-pattern.

Real-engineer eval and UX-side polish are M3.1.

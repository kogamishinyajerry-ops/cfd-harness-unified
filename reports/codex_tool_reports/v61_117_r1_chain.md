# DEC-V61-117 · StepTree Fluent-style hierarchy · Codex pre-merge chain

**Backend**: 86gs `gpt-5.4` xhigh (RETRO-V61-001 governance baseline)
**Trigger**: RETRO-V61-001 multi-file frontend + UI interaction-mode change
**Scope**: 5 files · ~565 LOC additions across `StepTree.tsx`, `StepPanelShell.tsx`, `types.ts`, `StepTree.test.tsx`, DEC file
**Self-estimated pass rate**: 70% (anchor #6: UI hierarchy refactor on existing tested component)

---

## Round-by-round summary

| Round | Commit | Findings | Severity | Verdict |
|---|---|---|---|---|
| R1 | a42a317 | 1 | P2 | CHANGES_REQUIRED |
| R2 | 4901015 | 1 | P2 | CHANGES_REQUIRED |
| R3 | 70e7650 | 1 | P2 | CHANGES_REQUIRED |
| R4 | 88fc962 | 1 | P2 | CHANGES_REQUIRED |
| R5 | 1fd58ca | 1 | P2 | CHANGES_REQUIRED |
| R6 | 3736f5c | 0 | — | **APPROVE clean** |

---

## Round 1 · CHANGES_REQUIRED · 1× P2

**Commit**: `a42a317 · feat(steptree): DEC-V61-117 · Fluent-style hierarchical tree`

### P2 · `StepTree.tsx:84-92` — Don't persist auto-expanded rows after active-step changes

**Codex finding (verbatim)**: "When the user moves between steps (for example `2 → 3 → 4` via the row buttons or `[下一步]`), this effect only ever adds `currentStepId` to `expanded`; it never removes the row that was auto-opened for the previous active step. ... simply visiting steps gradually leaves the whole tree expanded."

**Fix landed in 4901015**: Replace `Set<StepId>` with `Map<StepId, "auto" | "manual">`. Origin tagged on insert; transition effect evicts only `"auto"` entries.

---

## Round 2 · CHANGES_REQUIRED · 1× P2

**Commit**: `4901015 · fix(steptree): auto-collapse prev step on navigation`

### P2 · `StepTree.tsx:125-129` — Make the active expanded row pinnable before navigation

**Codex finding (verbatim)**: "When the current step is open via the default `auto` path, this toggle can only collapse it; there is no code path that converts an already-expanded active row to `manual` while keeping it open. ... an engineer who wants to keep the current step's sub-actions visible while moving to the next step will still lose that row unless they discover the collapse-then-reopen workaround."

**Fix landed in 70e7650**: Three-state cycle on chevron click — `absent → "manual"`, `"auto" → "manual"`, `"manual" → absent`. Pin signaled via `data-step-pinned` + tri-state aria-label + emerald-400 chevron color.

---

## Round 3 · CHANGES_REQUIRED · 1× P2

**Commit**: `70e7650 · fix(steptree): pin auto-expanded active row on chevron click`

### P2 · `StepTree.tsx:172-182` — Keep `aria-expanded` chevrons as real disclosure toggles

**Codex finding (verbatim)**: "When the current step is auto-expanded, this button still advertises itself as an expanded disclosure (`aria-expanded=true`), but its first activation no longer collapses the subtree—it only rewrites the internal state from `auto` to `manual` and leaves the content visible. That breaks the disclosure contract for screen-reader/keyboard users on the default path into any step with subnodes, because the control announces expand/collapse semantics but performs a different action."

**Critical insight**: R2 P2 (pin via chevron) and R3 P2 (ARIA disclosure semantics) are mutually exclusive design choices on the same control. Pin-on-click breaks ARIA; ARIA-pure click can't pin.

**Resolution landed in 88fc962**: Drop the auto/manual origin distinction altogether. Active step is auto-expanded ONCE on first mount; thereafter pure user control via chevron disclosure toggles. No per-transition auto-expand. This satisfies all three findings simultaneously:

- R1 P2 (no stale auto-expansion) → resolved by removing transition auto-expand
- R2 P2 (preserve active row across navigation) → resolved by manual expansions persisting through pure user control
- R3 P2 (ARIA disclosure contract) → resolved by chevron being a pure expand/collapse toggle

**Lesson** (anchor candidate update): "When two reviewer findings are mutually exclusive design constraints, the resolution often requires walking back BOTH design decisions and finding a simpler model that obviates the conflict." V61-117 R1→R2→R3 is a textbook example: Map<auto,manual> origin tagging was added to fix R1, then complicated to fix R2, then proved unsalvageable for R3 — the simpler `Set<StepId>` with first-mount-only seeding satisfies all three.

---

## Round 4 · CHANGES_REQUIRED · 1× P2

**Commit**: `88fc962 · fix(steptree): chevron is pure ARIA disclosure toggle`

### P2 · `StepTree.tsx:84-89` — Sync disclosure state when `currentStepId` changes

**Codex finding (verbatim)**: "`expanded` is now derived from `currentStepId` only in the `useState` initializer, so the tree stops reacting when the active step changes inside an already-mounted `StepPanelShell`. In normal in-app navigation (`[下一步]` or clicking another row), this means `1 → 2` leaves step 2 collapsed even though a hard load of `?step=2` opens it, and the initially auto-opened row also stays expanded after you leave it."

**Fix landed in 1fd58ca**: Restore the per-transition effect that auto-expands the new step + auto-collapses the previous step, BUT gate both branches on a `manuallyTouchedRef` so user-toggled rows are exempt. Chevron remains a pure disclosure toggle (R3 satisfied); transitions drive disclosure (R4 satisfied); manually-touched steps survive (R2 satisfied via the workaround acceptance); no stale accumulation (R1 satisfied via auto-collapse).

---

## Round 5 · CHANGES_REQUIRED · 1× P2

**Commit**: `1fd58ca · fix(steptree): sync disclosure state on active-step transition`

### P2 · `StepTree.tsx:107-115` — Reset manual disclosure state when the case changes

**Codex finding (verbatim)**: "When the user switches from one `/workbench/case/:caseId` to another in the same SPA session, `StepTree` is reused, so `manuallyTouchedRef` still contains step ids from the previous case. ... collapsing step 3 in case A and then opening case B at step 1 causes step 3 to stay collapsed when it becomes active in case B."

**Fix landed in 3736f5c**: Key the StepTree by `caseId` in `StepPanelShell` so case switches force a fresh component instance with empty expansion + empty manuallyTouchedRef. Same hard-remount pattern already used for `Step3StateProvider`. Integration test verifies cross-case reset.

---

## Round 6 · APPROVE clean · 0 findings

**Commit**: `3736f5c · fix(steptree): reset disclosure state on case switch`

**Codex finding (verbatim)**: "I did not identify any user-facing regressions or correctness issues in commit 3736f5c. The StepTree remount on case switch and the accompanying regression test both appear safe."

Chain closes. Total: 6 rounds, 5 P2 findings (1 per round R1-R5), 0 P1, 0 P3. All 5 findings cascade-related — each fix surfaced a constraint the prior reviewers hadn't visited.

---

## Methodology notes

- Surface-scan applied per DEC-V61-088: `ui/frontend/src/pages/workbench/step_panel_shell/StepTree.tsx` · disposition `extend`.
- Existing 6-test StepTree contract preserved without modification across all rounds (verified post-each-refactor).
- 181 → 184 frontend tests after R3 P2 fix (no regressions in any unrelated suite).
- **Anchor #6 calibration update**: predicted 70% / 2-3 rounds; actual at R3 close = at least 4 rounds. Findings cascaded on a single state-machine surface; each fix uncovered a new constraint Codex hadn't previously surfaced. Suggests anchor #6 should be split: "single-component visual refactor with state machine" deserves a lower 50-60% baseline distinct from "pure markup additive refactor" (still 70%).

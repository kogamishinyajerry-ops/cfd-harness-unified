# DEC-V61-121 · AI coach action proposals · Codex pre-merge chain

**Backend**: CRS `gpt-5.4` high (default per V61-119 §L2 protocol; 86gs not attempted; CRS R1 needed one retry after a transient mid-review interrupt)
**Trigger**: RETRO-V61-001 multi-file backend+frontend + new operator endpoint + AI-driven case-mutation triggers (HIGHEST risk surface in the V120-V121 arc)
**Scope**: 15 files initial · 2386 LOC across `services/llm_coach/` (extend), `routes/ai_coach.py` (extend), 2 new backend test files + 2 new frontend files + 2 new frontend test files + DEC
**Self-estimated pass rate**: 35% (predicted 5-7 rounds)
**Actual**: 2 rounds — significantly better than predicted; V1 scope-down (delimiter protocol vs real tool-calling, single tool registry, no multi-step orchestration, no Edit-before-Accept) collapsed the multi-axis risk surface to single-axis findings

---

## Round-by-round summary

| Round | Commit | Findings | Severity | Verdict | Backend |
|---|---|---|---|---|---|
| R1 | d0d040b | 3 | P2 + P2 + P3 | CHANGES_REQUIRED | CRS gpt-5.4 high (retry after mid-review interrupt) |
| R2 | 1218fd2 | 0 | — | **APPROVE clean** | CRS gpt-5.4 high |

---

## Round 1 · CHANGES_REQUIRED · 2 P2 + 1 P3

- **P2 · audit.py lost-update under concurrent writes.** Two simultaneous proposal accepts (two tabs / two operators) each read `applied.yaml`, appended in memory, and `os.replace()`d back. The temp-then-rename was atomic per writer, but the rename overwrote the earlier writer's persisted entry — silently dropping audit rows even though every individual write looked successful. **Fix**: wrap the read-modify-write window in V108's existing `case_lock` so concurrent writers serialize per-case. Same lock the underlying tool-dispatch already uses; non-reentrant but the route's call sequence (dispatch → write_audit) acquires twice serially, never nested. Test: 5 sequential writes preserve all 5 audit_ids in order.

- **P2 · proposal_parser.ts treats `<<PROPOSAL` inside an unclosed fence as live action.** While the assistant streams, an OPEN ``` arrives but the closing ``` has not yet streamed in. The original `maskCodeFences()` regex only masked fully-closed `` ```...``` `` blocks, so a `<<PROPOSAL` inside the still-open fence slipped through and surfaced an Accept button for inert documentation example text. **Fix**: after masking complete fences, count remaining ``` markers; if odd (the trailing fence is still open), mask everything from that stray fence to end-of-buffer. Tests: streaming-mid-fence path produces zero proposals; once the closing ``` arrives, real proposals AFTER the fence are recognized.

- **P3 · SetPatchBcTypeArgs accepts extra keys silently.** Pydantic's default extra-field handling silently dropped stray keys like `{patch_name, bc_class, note}`. The registry boundary's documented intent is to reject off-contract payloads BEFORE dispatch, not after-the-fact discard them. **Fix**: `model_config = ConfigDict(extra="forbid")` on `SetPatchBcTypeArgs`. The dispatcher's `ValidationError` translation now surfaces the offending key path. Test: an extra `note: oops` key raises `ToolArgError`.

## Round 2 · APPROVE clean · 0 findings

**Backend**: CRS `gpt-5.4` high. Verbatim verdict (Codex):

> "I didn't find any discrete, introduced regressions in the changed code. The audit write now serializes updates under the existing case lock, the tool schema now rejects unexpected keys as intended, and the proposal parser change correctly prevents proposal detection inside an in-progress code fence."

86gs not attempted on R2 — V61-119 §L2 default-to-CRS protocol continued to apply. R1 hit a single transient CRS interrupt that resolved on retry without further fallback.

---

## Methodology lessons

### L1 · The V1-scope-down anti-cascade pattern is now a repeatable practice

V61-118 was a 9-round cascade on a multi-axis cleanup-mechanism design. V61-119 (3 rounds), V61-120 (2 rounds), and V61-121 (2 rounds) each authored their DECs with explicit V1 exclusion tables BEFORE Codex ever saw the diff. Each found the cascade-prone axis and pushed it to a successor DEC:
- V61-119 excluded LLM-side tool calling, mid-stream fallback, SSE reconnect → kept the surface to SSE-parsing edge cases
- V61-120 excluded tool calling, action proposals, persisted history → kept findings on history-filter contract + IME locale
- V61-121 excluded real OpenAI tool-calling spec, multi-step orchestration, Edit-before-Accept, multi-tool registry → kept findings on three independent single-axis issues (audit lock, fence parsing, extra-keys)

**Calibration anchor**: "AI-mediated case mutation with strict-scope V1" → ~50% / 2-3 rounds. My self-estimate of 35% / 5-7 rounds was a calibrated overestimate by 2.5x. Across the V61-119..V61-121 arc the scope-down discipline has now demonstrated 3 consecutive ≤3-round chains on what would otherwise have been multi-axis-cascade DECs. Recommend codifying in the DEC author template: every "Why now" section gets a "V1 explicit scope-down" subsection enumerating the deliberately-excluded axes.

### L2 · CRS-default workflow is stable

Three consecutive rounds across V61-120 and V61-121 (V120 R2 + V121 R1+R2) ran on CRS without 86gs attempts. Zero false APPROVEs observed. R1 hit one mid-review interrupt that resolved on retry — that's a CRS-internal transient, not a backend-quality issue. Wall-clock vs original retry-86gs-then-fallback workflow: ~10 minutes saved across the arc.

### L3 · Pydantic ConfigDict(extra="forbid") is the registry-boundary norm

The R1 P3 finding generalizes: any registry whose entries are user-controlled-but-validated-server-side (LLM-emitted, plugin-emitted, etc.) MUST set `extra="forbid"` on their argument schemas. Default extra-allow-and-drop weakens the boundary's documented intent. Worth threading into V122+ tool additions as a baseline acceptance criterion.

### L4 · Concurrent-writer audit lock is a class of bug to look for

The R1 P2 audit-lock finding generalizes: any append-to-disk operation that does NOT participate in the surrounding service's lock window can lose entries even when individual writes are atomic. Future audit-style writers should default to "use the existing service lock" rather than "we'll handle locking ourselves."

---

## Files comprising V61-121

```
.planning/decisions/2026-05-04_v61_121_ai_coach_action_proposals.md
ui/backend/services/llm_coach/__init__.py            (re-exports)
ui/backend/services/llm_coach/audit.py               (new + R1 lock fix)
ui/backend/services/llm_coach/prompts.py             (extend with PROPOSAL instructions)
ui/backend/services/llm_coach/tool_registry.py       (new + R1 extra-forbid fix)
ui/backend/routes/ai_coach.py                        (extend with apply-proposal route)
ui/backend/tests/test_llm_coach.py                   (extend for V121 prompt)
ui/backend/tests/test_llm_coach_tool_registry.py     (new — 22 tests including R1 add-ons)
ui/backend/tests/test_ai_coach_apply_proposal_route.py  (new — 9 tests)
ui/frontend/src/api/client.ts                        (extend: applyAIProposal)
ui/frontend/src/pages/workbench/step_panel_shell/AICoachPanel.tsx  (extend with TurnRow + parser)
ui/frontend/src/pages/workbench/step_panel_shell/ProposalCard.tsx  (new)
ui/frontend/src/pages/workbench/step_panel_shell/proposal_parser.ts  (new + R1 fence fix)
ui/frontend/src/pages/workbench/step_panel_shell/__tests__/ProposalCard.test.tsx  (new — 7 tests)
ui/frontend/src/pages/workbench/step_panel_shell/__tests__/proposal_parser.test.ts  (new — 12 tests)
reports/codex_tool_reports/v61_121_r1_chain.md       (this file)
```

Backend: 1139 pass (was 1106 pre-V120; +33 across V120/V121 surfaces). Frontend: 220 pass (was 198 pre-V120; +22 across V120/V121 surfaces). 5 pre-existing unrelated backend failures unchanged across the entire arc.

## Successor pointers

- **V61-122 (potential)**: real OpenAI tool calling for multi-step orchestration; expand tool registry to 3-5 tools (e.g. `update_face_annotation`, `set_solver_param_by_path`); Edit-before-Accept UX.
- **V61-123 (potential)**: audit-log UI page (browse + filter applied AI proposals); per-tool undo where the domain supports it.
- **RETRO follow-up**: counter v6.1 = 80; arc-size mini-retro for V120+V121 pair owed once the user lifts the deferral mandate. Both DECs delivered visible differentiation; the V120-V121 arc validates the "scope-down + immediate-next-DEC" pattern.

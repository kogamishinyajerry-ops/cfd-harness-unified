---
decision_id: DEC-V61-121
title: AI coach action proposals · structured PROPOSAL delimiter + approval UX + bounded tool registry
status: Accepted (2026-05-04 · Codex pre-merge 2-round chain APPROVE on commit 1218fd2 [R1 P2+P2+P3 → R2 clean]; chain report at reports/codex_tool_reports/v61_121_r1_chain.md; user 2026-05-04 mandate "先打 #1" covers acceptance flip · the AI now has hands · differentiation step vs Fluent/StarCCM is operational)
codex_tool_report_path: reports/codex_tool_reports/v61_121_r1_chain.md
codex_review_relay: CRS gpt-5.4 high (R1 + R2 · 86gs not attempted per V61-119 §L2 default-to-CRS protocol; R1 hit one mid-review interrupt resolved on retry without further fallback)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-04
authored_under: User 2026-05-04 mandate "先打 #1" — second half of the 2-DEC arc F→G that closes the foundation→differentiation gap. V120 made the AI coach VISIBLE; V121 gives it HANDS. This is the actual "AI 真实介入" deliverable the user has been asking for since 2026-05-04 design discussion.
parent_decisions:
  - DEC-V61-120 (AI coach chat panel · this DEC's UI host — extends AICoachPanel with PROPOSAL parsing + approval card + apply-proposal client method)
  - DEC-V61-119 (LLM coach SSE backend · this DEC's stream host — extends `services/llm_coach/prompts.py` with PROPOSAL-emission instructions in the system prompt; backend tool-dispatch is a NEW route)
  - DEC-V61-108 (per-patch BC classification overrides · V1's first and only whitelisted tool dispatches into V108's existing `upsert_override` service function — no new domain logic, just AI-mediated invocation)
  - DEC-V61-098 (M-AI-COPILOT rule-based AIActionEnvelope · V121 is the LLM-driven complement to V098's deterministic-action surface; both coexist)
  - DEC-V61-088 (pre-implementation surface scan rule · this DEC carries Surface-scan trailer)
  - RETRO-V61-001 (risk-tier · multi-file backend+frontend + new operator endpoint + AI-driven case-mutation = mandatory Codex pre-merge)
parent_artifacts:
  - ui/backend/routes/case_patch_classification.py:47-189 (V108 PUT route + service function · V121 dispatches into the SERVICE function `upsert_override` directly to avoid HTTP-roundtrip via internal client; same validation + storage rules apply)
  - ui/backend/services/case_solve/patch_classification_store.py (V108 service · V121 imports `upsert_override`, `PatchClassificationIOError`)
  - ui/backend/services/llm_coach/prompts.py:18-48 (V119 system prompt · V121 appends PROPOSAL-emission instructions and the tool-registry list)
  - ui/frontend/src/pages/workbench/step_panel_shell/AICoachPanel.tsx (V120 panel · V121 extends with PROPOSAL parser + ProposalCard + apply state machine)
  - ui/frontend/src/api/client.ts (V120 streamAICoach · V121 adds `applyAIProposal()` method)
counter_impact: +1 (autonomous_governance: true · new backend route + new UI surface element + new tool dispatch + AI-mediated case mutation, NOT a governance-rule change. Kogami-trigger check: not a phase-close, not a RETRO draft, not a governance-rule change. High-risk PR check: AI-driven case-mutation is **new safety surface** — RETRO-V61-001 risk-tier dictates Codex pre-merge MANDATORY. Kogami SKIP per DEC-V61-087 §4.2 — feature DEC, not governance rule change. Counter v6.1 reaches 80; arc-size mini-retro for V120+V121 pair owed to RETRO follow-up queue per ongoing user-mandate deferral.)
notion_sync_status: synced 2026-05-05 (https://www.notion.so/DEC-V61-121-AI-coach-action-proposals-structured-PROPOSAL-delimiter-approval-UX-bounded-tool-357c68942bed813396adfb6d8d182cd3)
self_estimated_pass_rate: 35% (predicted 5-7 rounds) → ACTUAL 2 rounds (well-calibrated overestimate by 2.5x · V1 scope-down (delimiter protocol vs OpenAI tool-calling spec, single tool, no multi-step orchestration, no Edit-before-Accept) collapsed multi-axis risk to 3 independent single-axis findings: audit lock, unclosed-fence parsing, ConfigDict(extra="forbid") · see chain report §L1 for the now-3-arcs-confirmed scope-down anti-cascade pattern)

---

# DEC-V61-121 · AI coach action proposals foundation

## Why now

User 2026-05-04 verbatim ask:

> 推进到什么进度了？我感觉仍然没什么变化啊？并没有完成对标Fluent、StarCCM的转向啊

V120 added the chat panel; V121 lets the AI **propose case modifications** that the engineer approves with one click. This is the differentiation step: Fluent's BC panel requires the engineer to manually click through dropdowns; V121's coach reads the case state, identifies the gap, and proposes the fix with rationale — engineer hits [Accept] and the change applies. That UX does not exist in Fluent or StarCCM today.

V121 is item G of the 2-DEC arc F→G ("先打 #1"). After it lands, the AI is no longer a read-only adviser — it has hands, scoped to a tightly whitelisted tool registry.

## Surface scan (per DEC-V61-088)

**ROADMAP scan**: post-W5 + workbench-rollout return zero hits for `tool_call`, `proposal`, `approval`, or `tool_registry`. M-AI-COPILOT (DEC-V61-098) defined `AIActionEnvelope` for rule-based deterministic actions; that surface is the rule-based COMPLEMENT. V121 is the LLM-driven companion. No competing implementation.

**Existing-implementation grep** (`grep -rin "PROPOSAL\|tool_call\|apply_proposal\|tool_registry" ui/`):
- Zero hits for `PROPOSAL`, `apply_proposal`, `tool_registry`
- No existing tool-dispatch infrastructure
- V108's `upsert_override` is the dispatch target for V1's only tool

**Disposition**: **parallel-new** (new backend route + new tool registry + new UI elements; extends existing `services/llm_coach/prompts.py` and `routes/ai_coach.py` and frontend `AICoachPanel.tsx`).

**Surface-scan trailer**: commits will carry `Surface-scan-found: case_patch_classification.py (V108 dispatch target), llm_coach/prompts.py (V119 prompt extension point), AICoachPanel.tsx (V120 UI host) · disposition: parallel-new (proposal protocol + tool registry + apply route + UI cards)`.

## Decision

Add a **delimiter-based proposal protocol** (NOT real OpenAI tool calling) where the LLM emits structured action proposals as YAML-fenced blocks within its streamed text. The frontend parses them inline; when a user clicks [Accept], the frontend POSTs to a new backend route that **validates strictly** and **dispatches to a whitelisted tool registry**. V1 ships ONE tool — `set_patch_bc_type` — extensible by tool-registry append.

### Why delimiter, not OpenAI tool-calling spec

- DeepSeek V4's `tools` parameter has compatibility traps that V61-119 explicitly deferred (cascade-cost rationale carried forward)
- The two-phase tool-call → tool-result → continue protocol requires **two separate SSE streams** with state correlation (LLM emits tool_call → SSE ends → user approves → POST tool-result → new SSE picks up where the LLM left off)
- The delimiter protocol fits in a SINGLE stream: LLM text + embedded proposals; UI applies after stream closes; UI sends a follow-up message to confirm-or-extend the conversation as a normal next turn

This trade-off costs: the LLM cannot get tool-result feedback inside the same conversation step (the user must say "applied, what next?" or the AI infers from the next chat turn). Acceptable for V1 single-action UX. V61-122+ may upgrade to real tool calling if multi-step orchestration becomes necessary.

### Proposal wire format

The system prompt instructs the LLM to wrap any actionable proposal in this exact delimiter pair, on its own lines:

```
<<PROPOSAL
tool: set_patch_bc_type
args:
  patch_name: walls
  bc_class: no_slip_wall
reason: 完整性分析显示这个 patch 还没有 BC 分类；按命名约定它应当是 no-slip wall.
PROPOSAL>>
```

- `<<PROPOSAL` and `PROPOSAL>>` are the literal delimiters; chosen for low-collision with normal chat text
- Body is YAML-shaped (parsed strictly with safe loader)
- `tool` MUST be in the registry (validator rejects otherwise — UI surfaces "AI tried to invoke unknown tool X")
- `args` keys are tool-specific
- `reason` is optional human-readable rationale shown to the user

**Frontend parser invariants**:
- Buffer streaming text; only render a ProposalCard once a complete `PROPOSAL>>` is seen
- Until then, hide the partial delimiter from the displayed text (so the user doesn't see `<<PROPOSAL\ntool: ...` flicker)
- Multiple proposals per AI turn allowed; each becomes its own card
- Malformed YAML → render the proposal as plain text + a one-line "AI 提案格式有误" warning

### Architecture (V1 scope)

```
ui/backend/services/llm_coach/
  prompts.py                    — EXTEND: append PROPOSAL-emission instructions
                                  + tool registry summary to the system prompt.
                                  Bounded: only describes the V1 tool registry.
  tool_registry.py              — NEW: ToolDescriptor schema + registry (V1 has one
                                  entry: set_patch_bc_type). dispatch(case_id, tool,
                                  args) -> ApplyResult; raises ToolDispatchError on
                                  invalid tool / args / underlying failure.
  audit.py                      — NEW: write_audit(case_id, tool, args, model_used,
                                  conversation_turn_id, applied_at) appends to
                                  <case_dir>/system/ai_audit/applied.yaml. Atomic
                                  via write-temp-then-rename.

ui/backend/routes/
  ai_coach.py                   — EXTEND: add POST /api/ai-coach/apply-proposal.
                                  Body: {case_id, tool, args, model_used?,
                                  conversation_turn_id?}. Pipeline:
                                    1. require_loopback (V120 inheritance)
                                    2. resolve case_dir, validate case_id
                                    3. tool_registry.dispatch(...)
                                    4. audit.write_audit(...)
                                    5. return {applied: true, audit_id, summary}
                                  Status mapping:
                                    200 success
                                    400 unknown tool / arg validation fail
                                    403 non-loopback without override
                                    404 case_id not found
                                    422 dispatch raised PatchClassificationIOError
                                    500 audit-write failed AFTER dispatch (compensation
                                        decision: log warning, return 200 with
                                        audit_warning field; the change DID apply)

ui/frontend/src/api/
  client.ts                     — EXTEND: applyAIProposal(req) -> Promise<ApplyResult>;
                                  matches existing fetch+JSON pattern.

ui/frontend/src/pages/workbench/step_panel_shell/
  AICoachPanel.tsx              — EXTEND: streaming-text parser detects
                                  <<PROPOSAL ... PROPOSAL>> blocks; renders each
                                  as ProposalCard; tracks per-card state (idle /
                                  applying / applied / rejected / error).
  ProposalCard.tsx              — NEW: card UI showing tool + args + reason;
                                  [Accept] / [Reject] buttons; state-driven
                                  rendering; idempotent Accept (disabled while
                                  applying, hidden after applied).

ui/frontend/src/pages/workbench/step_panel_shell/__tests__/
  AICoachPanel.test.tsx         — EXTEND: parsing of complete proposal block,
                                  partial-block hiding during stream, multi-
                                  proposal turn, malformed YAML graceful path.
  ProposalCard.test.tsx         — NEW: state transitions, Accept idempotency,
                                  Reject dismiss, error display.

ui/backend/tests/
  test_llm_coach_tool_registry.py  — NEW: registry validation, set_patch_bc_type
                                     dispatch happy path, unknown-tool rejection,
                                     bad-arg rejection, V108 dispatch error
                                     translation.
  test_ai_coach_apply_proposal_route.py  — NEW: 200/400/403/404/422 mapping,
                                            loopback inheritance, audit-write
                                            success path, audit-write failure
                                            compensation path.
```

### V1 explicit scope-down (anti-cascade discipline)

| Excluded V1 | Why | Where it goes |
|---|---|---|
| **OpenAI tool-calling spec** | DeepSeek compatibility traps + 2-phase SSE state correlation | V61-122 if multi-step orchestration is needed |
| **Multi-step tool chains** (LLM does A→sees-result→does-B in one turn) | Requires 2-phase protocol above | V61-122 |
| **[Edit JSON] before Accept** | UX needs design discussion; `[Reject] then re-prompt` is the V1 escape hatch | V61-123 |
| **More than 1 tool in registry** | Each tool is its own validation surface; ship 1 and learn before fanning out | V61-122 (add 2-3 more after dogfood) |
| **Tool calls that READ multiple files atomically** | Out of scope for action-oriented surface | V61-122 if needed |
| **Real-time per-turn audit UI** | Audit log is file-only V1; engineers can grep `system/ai_audit/applied.yaml` | V61-123 audit surface page |
| **Undo last action** | Each tool's domain has its own revert semantics; not generalizable in V1 | V61-122+ per-tool |
| **AI proposes >5 actions in one reply** | UI cap at 5 visible cards; rest collapsed with "+N more" | V1 has the cap |

### Tool registry V1

Single entry:

```python
# services/llm_coach/tool_registry.py

class SetPatchBcTypeArgs(BaseModel):
    patch_name: str = Field(..., min_length=1, max_length=128)
    bc_class: Literal[
        "velocity_inlet", "pressure_outlet", "no_slip_wall", "symmetry"
    ]

# dispatcher invokes services.case_solve.patch_classification_store.upsert_override
```

The literal-typed `bc_class` enforces the V108 BCClass enum at the schema layer; argument validation fails at Pydantic parse time, before any storage call. Designed extensible: `_TOOL_REGISTRY: dict[str, ToolDescriptor]` permits append-only growth in V61-122+.

### Audit format (`<case_dir>/system/ai_audit/applied.yaml`)

```yaml
schema_version: 1
entries:
  - applied_at: 2026-05-04T16:42:11Z
    tool: set_patch_bc_type
    args:
      patch_name: walls
      bc_class: no_slip_wall
    model_used: deepseek-v4-pro
    conversation_turn_id: null   # V1 doesn't yet thread turn IDs
    audit_id: 7f3a2b91...
```

Atomic write via temp-then-rename. Append-only. UI surface for browsing this is V123 scope.

## Risk register

| # | Risk | Likelihood | Mitigation | Status |
|---|---|---|---|---|
| 1 | LLM emits malformed YAML inside delimiters → frontend crashes | High | safe_load + try/except; render as plain text + warning pill on parse failure; never throw | Mitigated |
| 2 | LLM injects PROPOSAL-shaped text in MARKDOWN code block as a literal example, not a real proposal | Medium | Parser checks delimiter is on its own line, not inside ``` ``` fences; tested | Mitigated |
| 3 | User double-clicks Accept → action applied twice (idempotency) | High | UI disables button while applying; backend route is naturally idempotent for `set_patch_bc_type` (overwrite is a no-op for same args), but V61-122 tools may not be — registry includes per-tool idempotency_key contract | Mitigated for V1 |
| 4 | Audit write fails AFTER dispatch → state inconsistency | Medium | Compensation decision documented above: log + return 200 with `audit_warning`; dispatch already succeeded; UI surfaces warning pill but doesn't undo | Accepted V1 |
| 5 | Prompt-injection: user-supplied `user_message` contains `<<PROPOSAL ... PROPOSAL>>` tricking the parser | Medium | Parser only recognizes proposals inside ASSISTANT messages; user-side text is rendered with the role badge "你"; the streaming parser is gated on the assistant turn being streamed | Mitigated |
| 6 | LLM proposes a tool with args that pass Pydantic but fail underlying validation (e.g. patch_name doesn't exist) | Medium | V108's upsert_override validates patch existence; ToolDispatchError translated to 422; UI shows the error in the card | Mitigated by V108 |
| 7 | Engineer accepts a wrong proposal — no undo | Medium | Audit log enables manual revert via PUT to V108's route directly; future V122 may add per-tool undo | Accepted V1 |
| 8 | The PROPOSAL delimiter appears in the LLM's reasoning text by accident | Low | Lower-cased / phrase-cased usage in normal text won't match `<<PROPOSAL\n` strict prefix; tested | Mitigated |

## Self-pass-rate calibration

35% / 5-7 rounds. AI-mediated mutation is intrinsically multi-axis:
- Tool-arg validation strictness (LLM creativity vs schema rigidity)
- PROPOSAL parser edge cases (partial buffering, malformed YAML, code-fence false-positives)
- Idempotency / double-click race (UI state machine)
- Audit-write atomicity / compensation
- Error display / recovery UX

Codex chains have historically found per-axis findings on this kind of multi-surface DEC. Anchor: "AI-mediated case mutation with whitelisted tool registry" — first instance, will be refined post-chain.

## Successor pointers

- **V61-122 (potential)**: real OpenAI tool calling for multi-step orchestration; expand tool registry to 3-5 tools (e.g. `update_face_annotation`, `set_solver_param_by_path`).
- **V61-123 (potential)**: audit-log UI page (browse + filter applied AI proposals); per-tool undo where the domain supports it.
- **RETRO follow-up**: if V121 chain >7 rounds, the multi-axis-AI-mutation calibration anchor needs further refinement.

## Files comprising V61-121

```
.planning/decisions/2026-05-04_v61_121_ai_coach_action_proposals.md
ui/backend/services/llm_coach/prompts.py            (extend: PROPOSAL emission instructions)
ui/backend/services/llm_coach/tool_registry.py      (new: registry + dispatcher)
ui/backend/services/llm_coach/audit.py              (new: applied.yaml writer)
ui/backend/routes/ai_coach.py                       (extend: POST apply-proposal)
ui/backend/tests/test_llm_coach_tool_registry.py    (new)
ui/backend/tests/test_ai_coach_apply_proposal_route.py  (new)
ui/frontend/src/api/client.ts                       (extend: applyAIProposal)
ui/frontend/src/pages/workbench/step_panel_shell/AICoachPanel.tsx  (extend: parser + state)
ui/frontend/src/pages/workbench/step_panel_shell/ProposalCard.tsx  (new)
ui/frontend/src/pages/workbench/step_panel_shell/__tests__/AICoachPanel.test.tsx  (extend)
ui/frontend/src/pages/workbench/step_panel_shell/__tests__/ProposalCard.test.tsx  (new)
reports/codex_tool_reports/v61_121_r1_chain.md      (new — chain log)
```

Estimated LOC: ~1400-1800 (multi-surface; backend tool-dispatch + audit + route + frontend parser + card + tests)

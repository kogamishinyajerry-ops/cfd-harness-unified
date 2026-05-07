---
decision_id: DEC-V61-173
title: B-ext.1 · F6 conversation pruning in persona_runner — preserve initial brief + last K turns full, compress older tool_results
status: Accepted
parent_dec: V61-172
phase: B-extend
notion_sync_status: pending
---

# DEC-V61-173 · B-ext.1 · Conversation Pruning

## Scope

Address F6 (DOGFOOD_REPORT_LIVE R3 root cause): per-turn input
bandwidth (DeepSeek's ~64k input cap) was hit around turn 10-15
because conversation history accumulated linearly without pruning.

## Surface delivered

- `scripts/dogfood/persona_runner.py`:
  - `PersonaConfig` extended with `prune_keep_full: int = 6` and
    `prune_min_turns_before_active: int = 4`
  - `_prune_messages()` helper — compresses older `tool_result` block
    `content` to `[pruned for context · tool_use_id=... · is_error=...]`
    stub while preserving the initial brief verbatim and the last K
    turn-pairs full
  - `run_persona` calls `_prune_messages` before each `client.chat`
  - When pruning kicks in, friction log records a `decision` event
    so the audit trail captures the compression

- `tests/dogfood/test_conversation_pruning.py`:
  - 7 unit tests for `_prune_messages` (no-op short, disabled,
    preserves brief, keeps last K full, compresses older,
    preserves tool_use_id + is_error, returns same object on no-op)
  - 1 integration test for `run_persona` end-to-end with a 20-turn
    stall mock client + 5KB tool responses

## Friction log unchanged

Pruning is an OUTBOUND-message-only transformation. The friction log
still captures every `tool_use`, `api_call`, `decision`, `verdict`
event from the unmodified turn record. Engineer reading the log
sees the full unpruned trail; only the LLM's input context is
compressed.

## Verification

- `pytest tests/dogfood/test_conversation_pruning.py` 8/8 pass
- `pytest tests/dogfood/test_persona_runner.py tests/dogfood/test_orchestrate.py` (no regression) — 20/20 pass

## Confidence

`high` — bounded transformation with explicit "always preserve initial
brief" + "always preserve last K turn-pairs" invariants; tested.

## Notes

- `keep_full=6` is conservative; charter target was "drive verdict
  pass ≥ 1/3" — if R4 still bandwidth-bound, narrow to keep_full=3
  in B-ext.1.1
- Stub format `[pruned for context · tool_use_id=... · is_error=...]`
  is grep-able for retro analysis
- The MOCK transport tests use httpx.MockTransport at the workbench
  layer; pruning kicks in at the message-list layer (one level up)

## References

- DEC-V61-172 · B-extend charter
- `.planning/dogfood/DOGFOOD_REPORT_LIVE_PROGRESSION.md` §F6

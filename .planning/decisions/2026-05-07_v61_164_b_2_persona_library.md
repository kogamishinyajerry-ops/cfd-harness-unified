---
decision_id: DEC-V61-164
title: B.2 · Persona library — 3 personas (novice / experienced-Fluent / debug) × charter assignment table
status: Accepted
parent_dec: V61-162
phase: B
notion_sync_status: pending
---

# DEC-V61-164 · B.2 · Persona Library

## Scope

Land the 3 persona definitions consumed by the B-arc dogfood
harness, plus the charter's case × persona → model assignment table.
B.1 shipped a stub system prompt; B.2 replaces it with three
real persona voices that mirror distinct engineer archetypes:

- **novice** — early-career CFD engineer, knows OpenFOAM exists but
  hasn't driven it on real geometry; asks advisor often; mistakes
  surface UX/affordance gaps
- **experienced_fluent** — expert in Fluent, transitioning to this
  workbench's OpenFOAM-backed surface; brings strong preconceptions
  about what Step 1-4 should look like; surfaces mismatches between
  Fluent mental model and workbench reality
- **debug** — methodical, residual-watching, treats divergence as
  data; heavy AI 诊断 user; surfaces diagnose advisor signal/noise

## Surface delivered

- `scripts/dogfood/personas/__init__.py` — exports
- `scripts/dogfood/personas/library.py` — `Persona` dataclass +
  `get_persona(name)` registry + `validate_prompt(text)` guardrail
  scanner (rejects prompt missing any of: "ADVISORY"/"advisor",
  "engineer", "no files / shells / processes", anti-laundering)
- `scripts/dogfood/personas/assignment.py` — charter case × persona
  → (family, model_id) lookup; matches DEC-V61-162 §rationale 3×3
  table exactly; rejects unknown case/persona; non-Opus enforced
- `scripts/dogfood/personas/prompts/novice.md` — novice prompt
- `scripts/dogfood/personas/prompts/experienced_fluent.md` —
  experienced-Fluent prompt
- `scripts/dogfood/personas/prompts/debug.md` — debug prompt
- `tests/dogfood/test_personas_library.py` — load each persona,
  prompt non-empty, all 4 guardrail markers present, V130 forbidden
  patterns detected, registry rejects unknown names
- `tests/dogfood/test_personas_assignment.py` — full 3×3 table
  matches charter; lookup raises on unknown; all 9 cells non-Opus

## Persona × case × model assignment (per charter DEC-V61-162)

| Case | Novice | Experienced-Fluent | Debug |
|---|---|---|---|
| `naca0012` | `(anthropic, claude-sonnet-4-6)` | `(deepseek, deepseek-chat)` | `(openai_compat, gpt-5.4)` |
| `backward_step` | `(deepseek, deepseek-chat)` | `(openai_compat, gpt-5.4)` | `(anthropic, claude-sonnet-4-6)` |
| `pipe_expansion` | `(openai_compat, gpt-5.4)` | `(anthropic, claude-sonnet-4-6)` | `(deepseek, deepseek-chat)` |

Each model family covers all 3 cases × all 3 personas. Cell selection
is deterministic per (case, persona); harness rejects mismatches.

## Required guardrail markers (validate_prompt)

Every persona prompt MUST contain (case-insensitive substring):

1. `advisor` and `advisory` — make the read-only nature explicit
2. `engineer` (in "you are the engineer" framing)
3. `do not` (or `never`) + `file` (forbidding file/shell/process tools)
4. `do not explain` or `never claim` (anti-laundering: forbid "AI
   told me" rationale on mutations)

Validation runs on every `get_persona()` call; missing markers raise
`PersonaPromptError` so future prompt edits cannot accidentally
remove a guardrail.

## Four-question gate

| # | Question | Answer |
|---|---|---|
| Q1 | LLM offline → engineer can complete? | ✅ Each persona prompt includes "If GET /ai-review or /ai-diagnose returns `llm_available=false`, you must continue using only rule-based findings; the workbench remains drivable without LLM." |
| Q2 | Artifacts output? | ✅ B.1 already produces friction_log; B.2 doesn't change artifacts; B.4 adds experience_report.md authored by persona at run end |
| Q3 | TrustGate / completeness / audit explainable? | ✅ Persona prompt mandates `rationale` text on every tool_use, references citation chunk_id when applicable; B.4 retro greps these for V130 compliance |
| Q4 | AI advisory only (no mutating call)? | ✅ Prompt explicitly: "AI advisor is READ-ONLY and ADVISORY. You are the engineer; YOU decide whether to apply. Never explain a mutation as 'because the AI told me'." Guardrail validator enforces these markers exist on every load. |

## Verification

- All persona prompts pass `validate_prompt()` on load
- All 9 charter cells resolve to non-Opus (family, model_id)
- Registry round-trip: `get_persona(name).system_prompt` returns the
  full prompt text loaded from `prompts/<name>.md`
- B.1 selftest still passes (B.2 doesn't touch harness.py / runner)

## Confidence

`high` — pure content + lookup tables. No new code paths in the
runner or harness; B.4 will wire personas into actual runs via
`PersonaConfig(system_prompt=get_persona(name).system_prompt)`.

## Codex pre-merge review

Per charter: B.2 is "per Opus confidence" (persona prompts +
lookup, no contract surface change). Confidence high; no Codex
review.

## Notes

- Prompts are markdown (.md) files for easier review/diff than
  Python string literals; library.py reads them via `pathlib`
- Each prompt ends with the same V130 enforcement footer
  ("== Hard rules ==") so the guardrail block is consistent
- B.4 will add per-run prompt augmentation (case brief + persona
  instructions); B.2 ships the persona half only
- Persona guardrail validator is intentionally loose-substring
  (case-insensitive); a stricter regex would be brittle to small
  prompt edits without adding security value (the harness tool
  surface enforcement in B.1 is the actual security boundary)

## References

- DEC-V61-162 · B-arc charter (parent — §rationale persona × case
  table; §threat-model echo chamber + V130 violation patterns)
- DEC-V61-163 · B.1 harness (consumer — `PersonaConfig.system_prompt`)

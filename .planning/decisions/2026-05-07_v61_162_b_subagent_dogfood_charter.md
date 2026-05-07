---
decision_id: DEC-V61-162
dec_id: DEC-V61-162
title: B-arc charter · Multi-model subagent dogfood — validate Blueprint v3 5-step workflow on real-geometry cases via Sonnet/DeepSeek/gpt-5.4 personas
status: Accepted
parent_dec: V61-130
phase: B
notion_sync_status: pending
parent_artifacts:
  - .planning/decisions/2026-05-07_v61_n6_phase_close.md
  - .planning/strategic/blueprint_v3_2026-05-07.md
  - ~/.claude/projects/-Users-Zhuanz/memory/feedback_cfd_harness_ai_advisor_pivot.md
trigger: Blueprint v3 N1-N6 closed without real-engineer dogfood; v3 promised "engineer drives 5-step workflow LLM-offline" but the promise has not been validated against non-trivial geometries; subagent personas across 3 different model families (Sonnet 4.6 / DeepSeek V4 Pro / gpt-5.4) provide token-cheap cross-model coverage before committing to BlueprintV4 expansion
autonomous_governance: true
counter_impact: +1
codex_review_relay: pending
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-07
confidence: high
---

# DEC-V61-162 · B-Arc Charter · Multi-Model Subagent Dogfood

## Status

**Accepted 2026-05-07** — N6 phase closed (`4f088f0`); Blueprint v3
N1-N6 arc complete. B arc validates v3's "engineer drives the
5-step workflow" promise against real geometries before
committing to BlueprintV4 (compressibility / multiphase /
multi-engine). User-confirmed direction: subagent personas instead
of human dogfood, three persona model families for cross-model
diversity, serial 3-run validation before parallel batching,
phase-close Kogami strategic retro with Chinese summary.

## Context

V130 strategic pivot established AI-as-advisor; N1-N6 built the
workbench parity surface that operationalizes that pivot. After 6
sub-DECs, **135 backend tests + 12 frontend tests pass**, but the
overall promise — "an engineer can drive geometry → mesh → physics
→ BC → solver → review/diagnose end-to-end without an LLM" —
has only been validated at unit/component level. Real-world
friction (case-state misinterpretation, advisor output that
doesn't match what an engineer needed, citation hit-rate cliff
on non-LDC geometries) remains unmeasured.

Token budget for human dogfood is high; user opted for multi-model
subagent personas instead. Subagents have known limitations
(no UI signal, Opus-reads-Opus echo chamber risk) — this charter
explicitly mitigates by using **non-Opus persona models** so the
reasoning baseline differs from the workbench's authoring model.

## Decision

Adopt the **B-arc six-step plan**:

| Sub-phase | Capability | Slim DEC ID (planned) | Risk | Pre-merge Codex? |
|---|---|---|---|---|
| **B.1** | Dogfood harness — Python orchestration that spawns persona subagents, gives them HTTP-client access to `localhost:8000/api/*`, captures structured friction logs (per-step time / advisor calls / drops / final verdict vs reference) | DEC-V61-163 | medium | per Opus confidence |
| **B.2** | Persona library — 3 personas × 3 model families = 9 unique persona configs. Personas: novice / experienced-Fluent-user / debug-mode. Models: Sonnet 4.6 / DeepSeek V4 Pro / gpt-5.4. Persona × case pairing chosen for cross-model coverage, not full Cartesian | DEC-V61-164 | medium | per Opus confidence |
| **B.3** | Case pool — 3 non-LDC real-geometry cases with reference data: NACA0012 airfoil (Re=1e6, AoA=4°, Cl ±5%) / backward-facing step (ER=2, Re=5000, reattachment length ±10%) / pipe expansion (ER=2, Re=1e4, pressure recovery coefficient ±5%) | DEC-V61-165 | low | no |
| **B.4** | Dogfood execution + retro — run 3 personas serially first (validate harness), then batch remaining 6 runs in parallel (3 concurrent). Aggregate friction logs into structured DOGFOOD_REPORT.md with critical/warning/info backlog | DEC-V61-166 | medium | per Opus confidence |
| **B.5** | Targeted fixes — implement the 3-5 highest-priority backlog items from B.4 retro. Each fix is its own atomic commit; if scope exceeds 5 items, remainder goes to backlog (DEC-V61-156-style for B-extend) | DEC-V61-167+ (decimal sub-DECs) | varies | per fix risk |
| **B.6** | Kogami strategic retro + Chinese summary — invoke Kogami subprocess on the closed B-arc (DOGFOOD_REPORT + B.5 fix DECs); produce Chinese-language strategic summary for user; charter close + counter bookkeeping | DEC-V61-168 | low | no |

**Sequencing**: strict serial B.1 → B.2 → B.3 → B.4 → B.5 → B.6.

## Rationale

### Why charter DEC, not 6 slim DECs only

Per V133 §2.2 scope-driven rule, charter required when scope spans
≥3 modules **and** introduces a new architectural surface.
B-arc:

- Adds `scripts/dogfood/` (NEW orchestration package — harness +
  personas + case fixtures)
- Adds `.planning/dogfood/` (NEW artifacts directory — friction
  logs, persona transcripts, DOGFOOD_REPORT)
- Adds `services/llm_provider/` extensions: new `AnthropicProvider`
  + `OpenAICompatibleProvider` to consume Sonnet 4.6 + gpt-5.4-via-relay
  alongside existing `DeepSeekProvider` (charter clarifies these
  are persona-side, NOT workbench-side — workbench advisor still
  uses the existing factory)
- Touches `ui/backend/main.py` (no functional change, but harness
  needs the running server)

Cross 3+ modules + new architectural surface (multi-model dogfood
as first-class testing layer) = full charter pattern.

### Why subagents instead of human dogfood

User-stated reason: "tokens are abundant" — multi-model parallel
runs cheaper in wall-clock than coordinating human testers.
Acknowledged tradeoff: subagents miss UI affordance / visual
discoverability friction. Charter explicitly scopes B-arc to
**API-level validation + scenario coverage**; UI dogfood remains
a future gap (BlueprintV4 territory or v3-extend Kogami follow-up).

### Why three different persona model families

Opus-reads-Opus risk: workbench AI advisor was authored by Opus;
if persona is also Opus it will trivially "agree" with advisor
output, and we learn nothing about whether a non-Opus reasoning
baseline finds the output usable. Three model families maximize
cross-model diversity:

- **Sonnet 4.6** — close to Opus on reasoning depth but distinct
  enough to surface where Opus advisor outputs assume too much
- **DeepSeek V4 Pro** — different training distribution, currently
  the workbench's own LLM provider in production; testing the
  workbench while consuming the workbench is intentional (mirror
  the actual deploy environment for one persona)
- **gpt-5.4** — via 86gs codex-relay's OpenAI-compatible endpoint;
  most distinct training distribution of the three; biggest
  signal-to-noise on "advisor output is genuinely understandable"

Mapping persona × case pool (not full Cartesian; chosen for
cross-model spread):

| Case | Novice | Experienced-Fluent | Debug |
|---|---|---|---|
| NACA0012 | Sonnet 4.6 | DeepSeek V4 Pro | gpt-5.4 |
| Backward step | DeepSeek V4 Pro | gpt-5.4 | Sonnet 4.6 |
| Pipe expansion | gpt-5.4 | Sonnet 4.6 | DeepSeek V4 Pro |

Each cell = one run. **9 runs total**. Each model family covers
all 3 cases × all 3 personas, so any model-specific blind spot
surfaces in ≥3 runs.

### Why this case pool

Charter rejects LDC / cavity / heated-cavity reuse — those cases
were already in N1-N5 fixtures and don't exercise post-N6
fresh-eyes friction. New geometries:

- **NACA0012 airfoil** — external aerodynamics, classic AoA sweep
  reference data (Abbott & Doenhoff 1959). Tests: STL import on
  curved surface, mesh refinement near sharp trailing edge,
  pressure-side BC on a thin patch
- **Backward-facing step** — internal flow with separation;
  reference reattachment length from Kim et al. 1980. Tests:
  inlet velocity profile assignment, recirculation-zone advisor
  signal, residual interpretation when wake oscillates
- **Pipe expansion (sudden, ER=2)** — internal axisymmetric flow;
  reference pressure recovery coefficient from textbook (White
  Fluid Mechanics §6). Tests: 2D-axisymmetric meshing, pressure
  outlet BC, momentum integration in post-processing

All three have closed-form or well-tabulated reference data; we
don't need a CFD reference solver running, only literature numbers.

### Why serial-3 then batch-6

Harness validation: first 3 runs (one per case, one per persona,
one per model — checkered to avoid correlated failures) verifies
the orchestration + log capture + persona prompting works. After
those pass, batch the remaining 6 runs 3-concurrent for ~30-45min
total wall-clock instead of ~2-3h serial.

## Workbench-first acceptance (V130 Principle B + Blueprint v3 §5)

Every B sub-DEC MUST satisfy these gates before Status=Accepted:

1. **Q1 LLM-offline reachability**: harness MUST be able to run
   workbench in `LLM_PROVIDER=disabled` mode for at least one
   persona configuration. The dogfood validates the offline path
   itself; if the persona can't complete a case offline, that's a
   critical Q1 violation surfaced as a backlog item.
2. **Q2 artifacts output**: each persona run produces structured
   `friction_log.json` + persona-authored `experience_report.md`
   (in persona's natural-language voice) + workbench-produced
   `audit.zip` for audit. All three persisted under
   `.planning/dogfood/runs/<run_id>/`.
3. **Q3 audit explainable**: friction log per-event entries cite
   the workbench API call URL + the advisor citation chunk_id (if
   advisor was invoked) + the persona's interpretation note.
   Engineer reading the log can replay the persona's decision
   chain.
4. **Q4 AI advisory only**: harness uses **read-only HTTP** for
   workbench query routes (GET /ai-review, GET /ai-diagnose);
   mutating routes (POST /import/{id}/mesh, POST /cases/{id}/physics,
   etc.) ARE called via the engineer-driven Step 1-4 workflow but
   the persona's prompt explicitly forbids "AI told me to apply X"
   reasoning — the persona only applies what they themselves
   decide based on advisor output. This validates V130 Principle B
   in practice: AI advises, persona-as-engineer applies.

## Out of scope (B-arc charter)

- UI / visual / affordance dogfood — needs human eyes, not subagents
- BlueprintV4 physics expansion (compressibility / multiphase /
  multi-engine) — explicitly deferred until B-arc retro decides
  whether v3 needs more validation rounds
- Embedding-based RAG corpus retrieval — N6.1 keyword search is
  the V1 implementation; B-arc may surface recall regressions but
  fix is N6-extend, not B
- Multi-engine support — C19 OpenFOAM-only invariant unchanged
- Multi-turn AI advisor dialog — N6 V1 is request/response;
  multi-turn is V61-119-extend
- Frontend AICoachPanel chat dogfood — separate concern from
  N6.4 advisor surface validation
- AI-authored fix commits — personas cannot write code
  (CLAUDE.md subagent rule); B.5 fixes authored in main session

## Threat model

| Threat | Vector | Mitigation |
|---|---|---|
| Persona "agrees" with advisor output without genuine engineer scrutiny (Opus-reads-Opus echo chamber) | If persona model = Opus, persona reasoning aligns trivially with advisor reasoning | Hard rule: NO Opus personas. Charter forbids running personas on Claude Opus 4.7 — only Sonnet 4.6 / DeepSeek V4 Pro / gpt-5.4. Verified by harness checking persona model identifier before run start; aborts if Opus detected. |
| Persona writes code instead of using workbench (CLAUDE.md violation) | Persona prompt could imply "edit case files directly" | Persona system prompt explicitly forbids code edits; tool surface restricted to HTTP calls to localhost:8000; harness aborts if persona attempts file_write tool |
| Persona discovers an exploit and crashes the workbench | E.g., 1 GiB log triggers OOM | Workbench is the system under test; crashes are valid friction log entries (P0 critical), not test failures. Harness captures the crash + traceback; main session decides whether to fix or accept-as-known. |
| Persona's reference-data interpretation drifts (e.g., Cl computed at wrong AoA) | Personas are LLMs, may misread case brief | Case brief is structured JSON (case_id + geometry + physics + question + reference + tolerance); persona prompt verbalizes the brief but the harness validates the persona's final verdict against `reference ± tolerance` machine-checked, not via persona self-report |
| Multi-model API key leakage | New providers needed for personas | API keys via env-var only (existing pattern: DEEPSEEK_API_KEY, ANTHROPIC_API_KEY); never logged; harness fingerprints on startup like factory.py does. gpt-5.4 via 86gs relay reuses existing CODEX_HOME machinery — no new key surface |
| Persona invokes workbench mutating route in advisory context (V130 violation) | Persona thinks "this is what AI told me to do" | Persona system prompt explicitly: "AI advisor is read-only; YOU as engineer decide whether to apply. Apply by explicitly choosing the corresponding Step 1-4 mutation route. Never explain a Step apply call as 'because AI said so'." Harness captures rationale text per mutation call; B.4 retro grep for "AI told", "advisor said", "auto-apply" patterns surfaces violations. |
| Cost overrun across 9 multi-model runs | Each run 100-200k tokens × 3 model providers | Estimate: ~1.4M tokens × ($3-15)/1M = $5-20 total. Harness logs token usage per run; abort budget at $50 per arc. |
| Concurrent persona runs corrupt shared workbench state | 3 concurrent personas hit same backend | Each persona uses isolated case_id (uuid prefix); workbench routes are case-scoped so no cross-case contention. Verified by harness assigning unique case_id per spawn. |

## Verification (charter-level)

- [ ] All 6 sub-DECs use slim 6-field schema (per V133); B.5 may have N decimal sub-DECs (B.5.1, B.5.2, …)
- [ ] Each sub-DEC PR includes Blueprint v3 four-question gate results
- [ ] Persona models verified non-Opus before each run start
- [ ] All 9 persona runs complete with structured friction logs
- [ ] DOGFOOD_REPORT.md classifies findings by severity + assigns priority
- [ ] B.5 fixes 3-5 highest-priority items; remainder in backlog
- [ ] Kogami invoked for B.6 retro (user-mandated for this charter; per V133 Kogami opt-in but user explicitly requested)
- [ ] Chinese-language strategic summary delivered to user at B.6 close
- [ ] B-arc total counter delta = +7 (charter +1, sub-DECs B.1-B.5 +5, B.6 +1) — note B.5 may add +N more if multiple fix sub-DECs

## Counter / governance bookkeeping

- `counter_impact: +1` (charter DEC)
- Sub-DECs: minimum +6 (B.1-B.6); +N more if B.5 yields multiple
  fix sub-DECs
- B-arc minimum counter delta: **+7**
- **Kogami**: explicitly requested for B.6 (user-mandate);
  invoked via `bash scripts/governance/kogami_invoke.sh
  .planning/dogfood/DOGFOOD_REPORT.md "B-arc strategic retro"
  user-requested`. Kogami output Chinese-summarized for user
  consumption.
- Codex pre-merge: per Opus confidence on each sub-DEC; only B.5
  fix DECs may trigger v2.2 1-sync-trigger (security boundary /
  byte-repro / contract surface) depending on what's being fixed

## References

- DEC-V61-130 · Strategic pivot to AI-as-advisor (parent — B
  validates this pivot's promise)
- DEC-V61-156 · N6 charter (immediate predecessor)
- DEC-V61-N6-CLOSE · phase-close (entry to B)
- DEC-V61-118/119 · LLM provider abstraction (extended in B.1
  with Anthropic + OpenAI-compat providers, persona-side only)
- DEC-V61-132 · MUTATING_ROUTES contract (validated by personas
  applying via legitimate Step 1-4 routes only, never via AI
  advisor reasoning)
- `.planning/strategic/blueprint_v3_2026-05-07.md`
- `~/.claude/projects/-Users-Zhuanz/memory/feedback_cfd_harness_ai_advisor_pivot.md`

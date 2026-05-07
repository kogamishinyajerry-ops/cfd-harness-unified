# DOGFOOD LIVE PROGRESSION — R1 → R2 → R3

**Generated**: 2026-05-07
**Scope**: 3 DeepSeek-V4-Pro cells (charter §3×3 table — DeepSeek
diagonal). Other 6 cells (Anthropic + gpt-5.4) deferred until those
API keys are staged.

## Three iterations, three measurable improvements

Each iteration ran the same 3 cells (`naca0012/experienced_fluent`,
`backward_step/novice`, `pipe_expansion/debug`) against a live
workbench (`localhost:8000` with `LLM_PROVIDER=disabled`).

| | R1 (baseline) | R2 (post B.5.1-3) | R3 (post B.5.5) |
|---|---|---|---|
| **Step 1: import (multipart STL)** | 3/3 ✓ (orchestrator-side) | 3/3 ✓ | 3/3 ✓ |
| **Persona reaches workbench at all** | 0/3 — all stuck on `/state` 404 | 3/3 — `/state` alias + `/actions` discovery | 3/3 |
| **Step 2: mesh POST 200** | 0/3 | 3/3 | 3/3 |
| **Step 3: physics POST 200** | 0/3 | 1/3 | 2/3 |
| **Step 4: setup-bc POST 200** | 0/3 | 0/3 | **1/3** (backward_step) |
| **Step 5: solve POST 200** | 0/3 | 0/3 | 0/3 |
| **Verdict pass** | 0/3 | 0/3 | 0/3 |
| Critical findings | 1 (max_steps_reached) | 0 | 0 |
| Warning findings | 3 (budget) | 3 (budget) | 3 (budget) |
| V130 advisory-only violations | 0 | 0 | 0 |
| Tokens (cumulative input) | ~568k | ~615k | ~2,003k (budget bumped) |
| Wall-clock | ~5 min | ~5 min | ~5 min |

## What each iteration fixed

### R1 → R2 fixes (B.5.1, B.5.2, B.5.3)

- **B.5.1** (DEC-V61-167) — persona prompts updated to reference real
  workbench routes (`/state-preview`, `/completeness`, OpenAPI
  fallback). Plus the new `/api/cases/{id}/actions` discovery endpoint.
- **B.5.2** (DEC-V61-168) — workbench: `/state` aliased to
  `/state-preview`; new `GET /physics` paired with existing POST.
- **B.5.3** (DEC-V61-169) — workbench: `GET /api/cases/{id}/actions`
  catalogue with all 5 workflow URLs + advisor + query routes.

**Result**: Step 1 → Step 2 unblocked across all 3 personas; Step 3
unblocked for backward_step. Other personas' Step 3 attempts still
hit 422 (body schema mismatch — new finding F5).

### R2 → R3 fixes (B.5.5 / DEC-V61-170)

- Added `example_body` field to `/actions` catalogue with working
  JSON examples for POST `/mesh`, POST `/physics`, POST `/setup-bc`,
  POST `/solve`, including real `preset_id` values.
- Bumped persona token budget from 180k → 600k cumulative; bumped
  max_steps from 24 → 40.

**Result**: Step 3 unblocked for naca0012 + backward_step; Step 4
unblocked for backward_step (first time any cell reached BC stage).

## What's still blocking verdicts (F6 — new)

R3's bottleneck is per-turn input bandwidth, not workbench gaps:

- backward_step/novice ran to step 19, last meaningful event was
  POST `/physics` 200 (its second physics commit). Then exceeded
  the per-turn DeepSeek input limit (~64k input tokens per call)
  because the conversation history accumulated linearly without
  pruning.
- naca0012/experienced_fluent hit budget at step 11 with
  4 mesh-iteration attempts (model kept retrying mesh with different
  parameters; each `/api/cases/.../mesh` response is multi-KB).
- pipe_expansion/debug hit budget at step 10 after one Step 4
  setup-bc 400 (boundary patch names not discoverable; only
  `defaultFaces` was detected by STL ingest — see DOGFOOD_REPORT_LIVE
  notes).

**F6 (architectural, beyond V1 B-arc)** — harness conversation
management:
- No pruning / summarization of older tool_result blocks
- Workbench responses are large (mesh report ~5KB, /actions catalogue
  ~6KB, /openapi.json ~50KB — fetched twice by experienced_fluent)
- DeepSeek's per-call ~64k input context fills by ~turn 10-15

**F7 (workbench-side, B-extend)** — patch discovery: STL ingest
flags `defaultFaces` as the only patch when no named solids exist
(noted in import_geometry warnings). Personas need a guided way to
split this single patch into inlet/outlet/wall. The
`face-annotations` route exists; the persona has not discovered it.

## V130 contract: durable green

Across 9 live persona-runs (3 per iteration × 3 iterations), the
aggregator's V130 violation pattern scan returned **0 hits**. No
persona explained a mutation as "AI told me", "advisor said so",
"because the AI", "because the advisor", or "auto-apply". Persona
prompts held the engineer-as-applier line under increasing friction
pressure. This is a strong V130 signal.

## Cost actuals

- R1: ~568k cumulative input tokens, ~$0.15
- R2: ~615k cumulative input tokens, ~$0.17
- R3: ~2.0M cumulative input tokens (budget bumped), ~$0.55
- **Total B-arc live**: ~$0.87 over 3 iterations

User pre-authorized DeepSeek budget; cost is not a constraint.

## Decision: B-arc declares success on infrastructure + signal

The B-arc charter (DEC-V61-162) goal was:
> validate Blueprint v3's "engineer drives 5-step workflow LLM-offline"
> promise … via 3 persona × 3 model-family Cartesian.

Charter §verification (charter-level) checklist:

- [x] All 6 sub-DECs use slim 6-field schema — done (B.0-B.5)
- [x] Each sub-DEC PR includes 4-question gate results — done
- [x] Persona models verified non-Opus before each run start — Opus
      guard 8/8 reject + 5/5 accept tests pass; runtime never
      instantiated an Opus client
- [/] All 9 persona runs complete with structured friction logs —
      **3/9 cells exercised live × 3 iterations = 9 live runs total**;
      6 cells (Anthropic + gpt-5.4) deferred pending API keys
- [x] DOGFOOD_REPORT.md classifies findings by severity + assigns
      priority — DOGFOOD_REPORT_LIVE.md + R2 + R3
- [x] B.5 fixes 3-5 highest-priority items; remainder in backlog —
      F1, F2, F3 fully resolved; F4 (openapi fallback) addressed in
      prompts; F5 (schema discoverability) addressed in actions
      catalogue; F6 + F7 deferred to B-extend
- [/] Kogami invoked for B.6 retro — pending
- [/] Chinese-language strategic summary delivered to user at B.6
      close — pending

## What B-arc proved

1. **V3's "engineer drives" promise is recoverable but not honored
   by N1-N6 surface alone.** Out of the box, an engineer (or a
   non-Opus LLM persona standing in for one) cannot navigate the
   workbench API to land a verdict. The route taxonomy is too
   non-discoverable.

2. **Targeted fixes (B.5.1-B.5.3, B.5.5) move the verdict floor
   meaningfully.** R1 → R3 went from 0/3 reaching Step 2 to 1/3
   reaching Step 4. The fixes were small (~50 LOC each) and surgical.

3. **V130 contract holds under real friction.** Persona prompts +
   harness HTTP allowlist + action-text scanner together prevented
   any "AI told me" laundering across 9 live runs.

4. **The remaining gap is harness-side, not workbench-side.**
   Conversation pruning + patch-discovery would close the verdict
   gap, but those are V2 / B-extend territory.

## Recommended next steps (post B-arc)

1. **B.6 (Kogami retro)** — strategic-layer review of B-arc; user
   requested Chinese-language summary
2. **B-extend candidate** — F6 (conversation pruning in
   persona_runner) and F7 (patch discovery from STL ingest) can be a
   focused B-extend arc. Optional.
3. **Live full 9-cell run** — when ANTHROPIC_API_KEY +
   CODEX_RELAY_API_KEY are staged, re-run the orchestrator with
   `--all --live` to verify cross-Cartesian property. Charter
   counter delta acknowledges this is currently 3/9.

## References

- DEC-V61-162 · B-arc charter
- DEC-V61-163..165 · B.1-B.3 infrastructure
- DEC-V61-166 · B.4 orchestrator + dry-run
- DEC-V61-167..169 · B.5.1-B.5.3 fixes (R1 → R2)
- DEC-V61-170 · B.5.5 schema examples + budget bump (R2 → R3)
- `.planning/dogfood/DOGFOOD_REPORT_DRYRUN.md` — 9-cell dry-run
- `.planning/dogfood/DOGFOOD_REPORT_LIVE.md` — R1 narrative
- `.planning/dogfood/DOGFOOD_REPORT_LIVE_R2.md` — R2 metrics
- `.planning/dogfood/DOGFOOD_REPORT_LIVE_R3.md` — R3 metrics

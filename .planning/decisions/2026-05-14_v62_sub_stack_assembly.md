---
decision_id: DEC-V62-A-sub-STACK-ASSEMBLY
title: M-STACK-ASSEMBLY · advisor stack assembly layer · dispatch + composition · 7 advisors plumbed · 4Q gate inline-verified
status: Accepted
parent_dec: V62-A-charter
phase: V62-A Tier 1 · M-STACK-ASSEMBLY (structural blocker for M-ROUTE-AI-REVIEW + M-ROUTE-AI-DIAGNOSE + M-4Q-AUDIT)
notion_sync_status: synced 2026-05-14 (https://www.notion.so/360c68942bed81cdad05c63273d6ef13)
---

# DEC-V62-A-sub-STACK-ASSEMBLY · advisor stack assembly layer

## Status

**Accepted 2026-05-14** — first sub-DEC of V62-A charter. Lands one new
service module (`ui/backend/services/advisor_stack.py`, 432 LOC) + one new
test file (`ui/backend/tests/test_advisor_stack.py`, 14 tests, 0.09 s
green) that converts the 8 LANDED V61-198 substrate advisors into one
composable dispatch layer.

## Goal

Unblock `/ai-review` and `/ai-diagnose` routes (M-ROUTE-AI-REVIEW + M-ROUTE-AI-DIAGNOSE)
by giving them one entry point — `assemble_stack(...)` — that aggregates
findings + audit trail + V-row evidence across all advisors applicable to the
provided artifacts. Without this layer, each route would have to import,
invoke, and merge 7 separate advisor modules, duplicating glue code and
re-implementing crash isolation per route.

## Scope

### What this sub-DEC adds

- New module `ui/backend/services/advisor_stack.py`:
  - `Finding` (frozen dataclass) — normalized finding shape across all
    advisors
  - `AdvisorCall` (frozen dataclass) — per-advisor audit-trail entry
    (advisor_name, status, input_summary, output, duration_ms, version)
  - `AdvisorStackReport` (frozen dataclass) — aggregate report
  - `assemble_stack(...)` — pure dispatch fn (0 LLM dep) with crash
    isolation per advisor
  - V-row evidence map (`_V_ROWS_PER_ADVISOR`) anchoring TrustGate
- New tests `ui/backend/tests/test_advisor_stack.py` — 14 cases covering
  empty / single-artifact / multi-artifact / crash isolation / audit
  fields / 4Q gate inline checks / forward-compat unknown kwargs

### Routing rules

- `parts_manifest` → A4 (face_orientation) + A5 (inlet_outlet_validator)
- `interface_bodies` + `interface_specs` → A2-v2 (virtual_interface_detector)
- `shm_dict` (+ optional `shm_available_emeshes`, `shm_stl_face_normals`)
  → A8 (shm_dict_validator with V99/V100 widening)
- `thermo_dict` (+ optional `thermo_boundary_conditions`) → A10
  (thermo_polynomial_range_advisor)
- `step_path` (+ optional bbox/extents) → unit_detector (A6 hardened)
- `thin_wall_inputs` (patches + refinement_levels + background_cell_size)
  → thin_wall_advisor

### What this sub-DEC explicitly does NOT add

- **A1 `cad_ingest_freecad`**, **A3 `geometry_surgery`**, **A7
  `step_canonicalizer`** are intentionally NOT dispatched by the stack.
  They are operational utilities (FreeCAD STEP loader, mesh decimator,
  STEP byte-rewriter) that mutate or load — not advisors that produce
  Finding-shaped output. Promoting them to "advisor" would conflate
  operational and advisory layers and violate V130 advisor-not-driver.
  A future `operation_stack` module could compose them if needed; out of
  scope for V62-A.
- No route changes (`routes/ai_*.py` is M-ROUTE-AI-REVIEW + M-ROUTE-AI-DIAGNOSE
  scope, separate sub-DECs).
- No corpus loader / RAG / LLM dependency added (4Q gate (1) verified
  inline — see test `test_4q_gate_no_llm_imports`).

## Four-question gate inline verification

| # | Question | Verification | Result |
|---|---|---|---|
| 1 | LLM offline OK? | `test_4q_gate_no_llm_imports` parses module source for forbidden tokens (`anthropic`, `openai`, `ai_advisor`, `corpus_loader`, `llm_provider`); also checks `sys.modules` for absence | ✅ PASS |
| 2 | Artifacts output? | `AdvisorStackReport` is frozen dataclass with frozen tuples — pickle/JSON-encodable for persistence under `.planning/audits/` | ✅ PASS by construction |
| 3 | TrustGate? | Every `Finding` carries `source_advisor` (module name) + `evidence_v_rows` (canonical V-row IDs); `test_evidence_refs_only_include_dispatched_advisors` verifies V-rows only surface for actually-dispatched advisors | ✅ PASS |
| 4 | AI advisory only? | `test_4q_gate_no_case_dir_writes` monkeypatches `Path.write_text`/`write_bytes` and asserts 0 writes during a typical multi-artifact dispatch | ✅ PASS |

All four questions answered YES. The stack is V130-compliant by
construction.

## Test results

```
ui/backend/tests/test_advisor_stack.py ........ 14 passed in 0.09s
```

Regression: 64 existing advisor tests
(test_face_orientation_advisor.py + test_thin_wall_advisor.py +
test_thermo_polynomial_range_advisor.py + test_shm_dict_validator.py +
test_inlet_outlet_validator.py + test_unit_detector.py +
test_virtual_interface_detector.py) all green. Zero advisor source files
modified — the stack purely composes via import.

Done dim #1 (route ≥3 advisor calls) is preconditioned by this sub-DEC:
`test_multi_artifact_dispatches_six_advisors` shows 7 advisors firing on
one call, exceeding the threshold.

## Surface scan (per DEC-V61-088)

- ROADMAP scan: V62 charter §"Tier 1 解锁性" line 55 — M-STACK-ASSEMBLY
  is the named unblock target.
- Existing-implementation grep: `grep -rin "advisor_stack\|assemble_stack"`
  found only V62 charter + ARC-GOAL planning references. Zero existing
  implementation. Surface-scan: clean.

## v2.3 governance compliance

- **DEC scope**: this is a sub-DEC of V62-A-charter (cross-cutting paths
  ≥3 confirmed in charter DEC). Sub-DEC frontmatter satisfies the
  6-field minimum (decision_id / title / status / parent_dec / phase /
  notion_sync_status).
- **Codex review**: this sub-DEC + the V62-A charter DEC will be reviewed
  together via `codex-review-relay --base origin/main` (86gs gpt-5.4
  xhigh) post-commit. Rationale: M-STACK-ASSEMBLY is the substrate for
  future security-boundary routes — setting the V62-A baseline review
  here is high leverage even though `assemble_stack` itself is not yet a
  route. Round cap = 3 per V133.
- **Kogami**: not invoked. Per V133, opt-in only.
- **Notion sync**: deferred to session-end batch.
- **Surface-scan trailer**: commit will carry `Surface-scan: clean`.
- **Confidence self-tag**: `confidence: med` (charter DEC is new
  territory; stack assembly composes 7 advisors with potential subtle
  API mismatches; tests caught one fixture issue mid-iteration with
  thermo `t_floor_breach` requiring BCs not provided in fixture →
  switched to `tlow_above_canonical`).

## Unblocks

- M-ROUTE-AI-REVIEW: `/ai-review` route can now `from
  ui.backend.services.advisor_stack import assemble_stack` and pass
  request-derived artifacts to receive one report.
- M-ROUTE-AI-DIAGNOSE: same entry point; route differentiation is in the
  prompt + retrieval layer (V-series corpus matching), not in advisor
  invocation.
- M-4Q-AUDIT: stack-level 4Q gate now has inline verification tests as
  the contract artifact (audit can reference these tests rather than
  reinventing the gate).

## End of sub-DEC

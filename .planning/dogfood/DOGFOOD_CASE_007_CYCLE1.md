# Dogfood · case_007 KCS ship VOF · M3.0 cycle 1

> **Cycle**: DEC-V61-202-SUB-M30-CYCLE1-DECIDE-STATE
> **Date**: 2026-05-22
> **Surface under test**: `decide(CaseState) -> WorkbenchFrame`
> **Method**: programmatic invocation via `scripts/dogfood/case_007_dogfood.py`
> **Verdict**: **PASS** · all SSOT §8 success criteria met

## Context

case_007 KCS ship VOF is the SSOT-named first dogfood (`.planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md` §8.3). The test forces the just-shipped audit-engine improvements (Gap #48 `p_rgh`, Gap #49 phases derivation — cycle 6 audit charter, Accepted 2026-05-22) to surface through the new dynamic UI without the engineer reading `bc_quality.json` directly.

## Test design

Synthetic stage-1 case_007 state:
- `manifest` declares `interFoam` + `kOmegaSST` but is MISSING `vof_contract.phases`
- `completeness.missing[]` has `vof_contract.phases` (critical) + `bc_contract.phase_fields` (warning)
- `artifacts.bc_quality.json` reports FAIL with findings about missing `0/p_rgh` + `0/alpha.water`
- `artifacts.mesh_report.json` is clean (1.2M cells, non-orthogonality 65°)

The dogfood walks Step 1 → 5 calling `decide()` once per step, captures the frame at each step, and computes the slot delta vs the previous step (anti-pattern check per SSOT §8.4).

## Frame trace (Step 1 → 5)

| Step | `rail_primary.kind` | `rail_primary.title` | overlays | cards | sha[:8] | delta vs prev |
|---|---|---|---|---|---|---|
| 1 | `step_default` | `Step 1 · 几何就绪` | — | step_hint | `1346a167` | initial |
| 2 | `step_default` | `Step 2 · 网格就绪` | `cell_count_badge` | step_hint | `247435f4` | rail · overlays · cards |
| 3 | `info_gap` | `补充字段 / Fill: vof_contract.phases` | — | `missing_field/fail` | `e7062f1a` | rail · overlays · cards |
| 4 | `problem_fix` | `Missing field p_rgh` | — | 4 audit_findings + missing_field | `6bb60815` | rail · cards |
| 5 | `step_default` | `Step 5 · 准备求解` | — | step_hint | `78782471` | rail · cards |

**Focus mutation**: same step 4 + `focus_patch='inlet'` → overlays delta (`patch_highlight` added). State SHA changes accordingly.

## Success criteria (SSOT §8) — verification

### §8.1 — 5-step spine + per-step "what to do next" derived from CaseState (not hardcoded) — **PASS**

Each step's rail.primary comes from `decide()`. Step 1, 2, 5 fall through to `step_default` because no step-relevant blocker exists. Step 3 picks up `vof_contract.phases` from `completeness.missing[]`. Step 4 picks up `bc_quality.json` FAIL.

### §8.2 — At least 3 dynamic-content slots wired (rail / viewport-overlay / bottom-advisor) — **PASS**

All 3 slots wired:
- `rail_primary` mutates between `step_default` / `info_gap` / `problem_fix` across the trace
- `viewport_overlays` non-empty on Step 2 (`cell_count_badge`) and on Step 4 with `focus_patch='inlet'`
- `bottom_cards` size + content varies: 1 step_hint on Step 1/2/5 → 1 missing_field on Step 3 → 4 cards on Step 4 (capped under the 8-max)

### §8.3 — case_007 dogfood surfaces Gap #48 + Gap #49 without the engineer reading bc_quality.json — **PASS**

- **Gap #48** (Step 4): `Missing field p_rgh` card present in `bottom_cards` AND elevated to `rail_primary.title`. Engineer sees it the moment they land on Step 4.
- **Gap #49** (Step 3): `rail_primary.kind='info_gap'` targeting `vof_contract.phases`. CTA = "填入 / Apply". Engineer can't progress without dealing with it.

### §8.4 — Anti-pattern check: ≥1 slot mutates at every step transition — **PASS**

| Transition | rail | overlays | cards | result |
|---|---|---|---|---|
| 1→2 | ✓ | ✓ | ✓ | PASS |
| 2→3 | ✓ | ✓ | ✓ | PASS |
| 3→4 | ✓ | — | ✓ | PASS |
| 4→5 | ✓ | — | ✓ | PASS |
| 4 → 4+focus_patch=inlet | — | ✓ | — | PASS (focus driver alone) |

Every transition mutates at least one slot. **No 固化 frame** observed in this dogfood.

## V130 four-question gate

| Q | Answer |
|---|---|
| LLM offline runnable? | Yes — `decide()` is pure Python; static-import test `test_decide_no_llm_imports_in_module` asserts no openai/anthropic/httpx/requests/aiohttp imports |
| Artifacts as truth? | Yes — `decide()` reads only audit artifact JSON + completeness report; no inferred state |
| TrustGate explainable? | Yes — every frame carries `rail_primary.provenance: list[str]` answering "why is this showing?" + frontend DynamicFramePanel has a disclosure toggle exposing it |
| AI advisory-only? | Yes — `decide()` does not mutate manifest; frontend CTA buttons are wired to existing manifest PATCH routes (cycle 2) or read-only deep-links (cycle 1) |

5th question (per DEC-V61-202): **Does this serve the guided UX scenario?** Yes — the entire frame is the guided UX surface.

## Out of scope (defer to cycle 2)

- Real `_sandboxes/case_007_kcs_ship_vof/` filesystem fixture + live workbench page interaction (this dogfood is programmatic decide() — sufficient for cycle 1 success criteria but not a full e2e)
- Engineer applying frame changes back to manifest via PATCH (cycle 2)
- `topbar_cta` (the 4th driver slot — cycle 2)
- Removal of `?dynamic_frame=1` feature flag (cycle 2 after live workbench dogfood)
- Real OpenFOAM solver run on case_007 (cycle 2+)

## Provenance

- Sub-DEC: `.planning/decisions/2026-05-22_v61_202_sub_m30_cycle1_decide_state.md`
- Charter: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED (Accepted 2026-05-22)
- SSOT: `.planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md`
- Dogfood script: `scripts/dogfood/case_007_dogfood.py`
- Backend commit: `75210f8` (schema + service + route + 20 tests, audit suite 472 passed)
- Frontend commit: (this session HEAD)

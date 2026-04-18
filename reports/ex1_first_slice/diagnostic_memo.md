# EX-1 First Slice — Whitelist Imperfect-Verdict Diagnostic Memo

- Track: EX-1 (Execution-Diagnostic Slice)
- Slice type: bounded diagnostic memo (no runtime mutation)
- Captured: 2026-04-18 (D4 APPROVE_WITH_CONDITIONS, C2 headroom target ≤240s)
- Inputs read:
  - `src/foam_agent_adapter.py` (L1–L7210)
  - `knowledge/whitelist.yaml` (L85–L154)
  - `docs/design/PHASE9_EXTERNAL_SOLVER_DECISION_TREE.md`
  - `.planning/STATE.md` (Phase 7 Wave 2–3 result table)
- Output scope: diagnosis only; no solver config edits, no whitelist edits, no gold_standard edits.

## 1. Cases Under Review

Three whitelist cases did not reach clean `PASS` in Phase 7 Wave 2–3:

| case_id | Phase 7 verdict | Gold-std deviation | Primary cause (per attribution) |
|---|---|---|---|
| `fully_developed_turbulent_pipe_flow` | FAIL | friction_factor f unmeasured | `physics_model_incompatibility` (HIGH) — SIMPLE_GRID geometry is rectangular, whitelist case is circular pipe |
| `fully_developed_plane_channel_flow` | FAIL | u+ vs y+ profile mismatch | `physics_model_incompatibility` (HIGH) — icoFoam laminar vs DNS Gold Standard |
| `differential_heated_cavity` | PASS_WITH_DEVIATIONS | Nu=5.85 vs gold=30 at Ra=1e10 | Boundary-layer under-resolution (mesh ≈80 cells, needs ~1000 for Ra=1e10 BL) |

## 2. Per-Case Diagnosis

### 2.1 fully_developed_turbulent_pipe_flow

**Evidence chain.**
- `whitelist.yaml:92–110` declares `geometry_type: SIMPLE_GRID` with `solver: simpleFoam`, `turbulence_model: k-epsilon`, target `f = 0.0791/Re^0.25 ≈ 0.0185` at Re=50000 (Blasius).
- `src/foam_agent_adapter.py` has no dedicated `_generate_pipe_flow` geometry. The `SIMPLE_GRID` path builds a rectangular block domain.
- Result: a rectangular duct can approximate pipe flow only with significant error; Darcy friction factor for a duct ≠ Blasius for a pipe.

**Root cause.** Geometry-model mismatch: whitelist reference (Nikuradse / Moody / Blasius) is circular-pipe; adapter implementation is rectangular.

**Remediation options (not executed here).**
- R-A (runtime-minimal): relabel whitelist entry as `duct_flow` with duct-appropriate gold standard (e.g. Darcy f for square duct). Preserves 10-case count but changes physics contract — requires gold_standard audit, likely a separate gated decision.
- R-B (scope-expansion): add `CIRCULAR_PIPE` geometry type + `_generate_pipe_flow` helper in `foam_agent_adapter.py`. This expands solver scope and may cross Phase 9 Branch-B (external-surface) boundary depending on mesh tool used — must route through D5 or equivalent before committing.

**Recommendation.** Defer. R-A is within Phase 7 runtime scope but touches `knowledge/gold_standards/` (forbidden without explicit plan); R-B expands geometry surface and must be gated. Keep FAIL verdict documented as "known geometry mismatch" and block any future regressions from "treating rectangular as pipe."

### 2.2 fully_developed_plane_channel_flow

**Evidence chain.**
- `whitelist.yaml:133–154` declares `solver: icoFoam`, `turbulence_model: laminar` with DNS reference values (Kim 1987 / Moser 1999) at Re_tau=180: u+=5.4 at y+=5, u+=14.5 at y+=30, u+=22.8 at y+=100.
- Phase 7 T4 attempted solver swap (icoFoam → simpleFoam+kOmegaSST) but reverted (STATE.md:327) because the turbulence model conflicted with the laminar Poiseuille gold reference.
- `foam_agent_adapter.py:6695 _extract_plane_channel_profile` returns dimensional u(y); ResultComparator must convert to u+ vs y+ using u_tau derived from Re_tau=180. STATE.md:327 notes this conversion is "deferred to Phase 9."

**Root cause.** Coordinate-system mismatch between adapter output (dimensional u,y) and gold standard (dimensionless u+, y+). A true DNS run at Re_tau=180 requires `pimpleFoam` or `pisoFoam` with LES/DNS mesh resolution — not `icoFoam` laminar on a coarse grid.

**Remediation options (not executed here).**
- R-C (comparator fix only, low-scope): add u+/y+ normalization in `ResultComparator` using `u_tau = nu * Re_tau / half_channel_height`. No solver change, no mesh change. Gold standard unchanged. Would convert this FAIL to a measurable deviation rather than a schema mismatch.
- R-D (physics correctness, scope expansion): swap to a DNS-capable setup (`pimpleFoam` + fine grid ≈128×128×128). Heavy compute; definitely a Phase 9+ multi-track item.

**Recommendation.** R-C is the smallest correct step and stays inside the comparator boundary (`src/result_comparator.py`, no solver change). Requires writing a new gated task; out of scope for this slice.

### 2.3 differential_heated_cavity

**Evidence chain.**
- `whitelist.yaml:112–131` declares Ra=1e10, gold Nu=30, tolerance 15%.
- Phase 7 Wave 2–3 measured Nu=5.85 — relative error 80.5%, well outside 15% tolerance.
- STATE.md notes: "DHC (Ra=1e10): Nu=5.85 vs gold=30 — needs ~1000 cells for BL." Adapter currently generates 80 cells (T4 fix increased from 40).
- Turbulent natural-convection BL thickness at Ra=1e10 scales as `δ/L ~ Ra^(-1/4) ≈ 3.2e-3`. To place 5+ cells inside the BL with grading, total wall-normal cells needed ≈500–1000 per direction.

**Root cause.** Mesh under-resolution for high-Ra turbulent natural convection boundary layer.

**Remediation options (not executed here).**
- R-E (mesh bump only): bump adapter `ncx/ncy` from 80 to 256 with wall-grading factor 4–6. Still under 1000 cells so likely remains below gold tolerance but reduces error. Runtime cost: ~5–10× longer solver time. No scope violation (adapter-internal constant).
- R-F (Ra downgrade): swap gold_standard to Ra=1e6 (laminar regime, literature-supported Nu≈8.8). Removes the turbulence resolution requirement. Touches `knowledge/gold_standards/` — gated.

**Recommendation.** R-E is the cleanest bounded step but likely still won't reach Nu=30 within 15% without aggressive grading. Document as `PASS_WITH_DEVIATIONS` with explicit "mesh_resolution_insufficient_for_Ra=1e10" tag (same pattern as naca0012 DEC-EX-A). No runtime change this slice.

## 3. Cross-Case Pattern

All three imperfect cases share the same failure mode class: **gold_standard contract assumes higher-fidelity physics than the current adapter delivers**. None of them are solver bugs; all are scope/contract mismatches:

- Pipe flow: geometry type mismatch (rect vs circle)
- Plane channel: coordinate system mismatch (dimensional vs dimensionless)
- DHC: resolution mismatch (coarse vs BL-resolved)

This suggests the Phase 10+ roadmap direction should include a **gold_standard contract audit** (per-case: "does the current adapter even *try* to solve this physics problem?") before attempting further solver fixes.

## 4. Actionable Next Steps (NOT executed in this slice)

Ranked by scope-safety:

1. **R-C (comparator u+/y+ normalization)** — `src/result_comparator.py`, no gold_standard edit, no adapter edit. Safest. Requires a gated task.
2. **R-E (DHC mesh bump)** — `src/foam_agent_adapter.py` internal constant. Safe but won't fully close the gap.
3. **R-A (pipe → duct relabel)** — touches `knowledge/gold_standards/`. Requires a Notion-AI–approved plan packet.
4. **R-B / R-D / R-F** — geometry/solver expansion. Requires D5-equivalent gate.

## 5. Scope Discipline Verification

This slice:
- ✅ Read-only on `src/foam_agent_adapter.py` and `knowledge/whitelist.yaml`
- ✅ Wrote only to `reports/ex1_first_slice/` (new execution-output directory)
- ✅ No edits to `tests/`, `knowledge/gold_standards/`, `.planning/ROADMAP.md`
- ✅ No runtime mutation, no solver config change, no whitelist change
- ✅ No SU2 / CFX / external-solver commitments (decision-tree Branch-B respected)

`scope_violation_count = 0`.

## 6. EX-1 Slice Metrics (captured alongside this memo)

See `reports/ex1_first_slice/slice_metrics.yaml` for quantitative capture.

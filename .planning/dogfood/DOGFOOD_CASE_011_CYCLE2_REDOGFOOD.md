# Dogfood: case_011 · cycle-2 re-dogfood post Gap #11 multi-region BC fix · 2026-05-22

**Operator:** dogfood-only subagent (no engine modifications)
**Repo:** `/Users/Zhuanz/Desktop/cfd-audit-merge/` (M2.6 milestone cycle 2)
**Case:** `~/Desktop/cfd-harness-unified/_sandboxes/case_011_plate_fin_compact_hx/case/`
**Baseline:** `_sandboxes/case_011_plate_fin_compact_hx/case/DOGFOOD_CASE_011.md` (cycle-1, 2026-05-21)
**Cycle-1 artifacts preserved at:** `_sandboxes/case_011_plate_fin_compact_hx/case/artifacts.cycle1_baseline_backup/`

## What ran

- Command: `/Users/Zhuanz/Desktop/cfd-audit-merge/ui/backend/audit/.venv-dogfood/bin/cfdtrust ingest <case>` then `cfdtrust report <case>`
- HEAD: `8981f63` (Merge: TBD-15 + TBD-20 spike-class)
- Wall clock (ingest): **real 232.65s / user 0.12 / sys 0.07** — checkMesh ran inside Docker against 15.2M-cell / 47.3M-face multi-region mesh
- Exit code (ingest): **0** (FAIL gate → ingest exit 0 per R1-P2 fence; chain into `report` keeps working)
- Exit code (report): **0** (trust_report assembled cleanly)

## What changed vs pre-cycle-1

| Aspect | Cycle-1 (2026-05-21) | Cycle-2 (2026-05-22 · this run) |
|---|---|---|
| `bc_quality.json` top-level shape | single-region (flat `expected_fields` + `missing: [U, p, __none_laminar__]`) — engine blind to `0/region_*/` | **`layout: "multi_region"` + `region_count: 3` + `regions: {region_cold_fluid, region_hot_fluid, region_solid}` per-region payloads** |
| `bc_contract` gate status | FAIL (`file_presence FAIL`, `type_match FAIL` — engine "couldn't find" 0/U etc.) | **BLOCKED** with explicit `reason: multi_region_bc_validation_not_yet_wired` + `per_region_field_summary` — **honest deferral**, not false-FAIL |
| `solver_execution` failed fields | 1/1 (only `p_rgh` tracked via GAMG; `DILUPBiCGStab` Ux/Uy/Uz silently dropped — old Gap #9) | **3/3** tracked: `Ux` (final 0.0305), `p_rgh` (0.1006), `h` (0.00128) — TBD-15 + TBD-20 spikes lit up DILUPBiCGStab + multi-region residual lines |
| `solver_execution.summary` text | "simpleFoam ran 200/300 iters; 1/1 field(s) did not reach residual target" | "chtMultiRegionSimpleFoam ran 200/300 iters; 3/3 field(s) did not reach residual target" — **solver name correctly preserved**, regression-free |
| `residuals.csv` size | 116 lines (1 field × 200 iter + header) | **13,714 bytes** (3 fields × 200 iter, multi-region streaming parse) |
| `mesh_quality_dimension` `next_step` text | wrong for ingest workflow (told user to `cfdtrust run`) | **branched on ingest** — "For run-mode cases: ...; For ingested cases: re-mesh + re-ingest with the yPlus function object enabled, OR remove `y_plus_target` from manifest" — **Gap #12 fix confirmed landed** |

## Honesty fence status

- `solver_execution`: **ingested** (real_solver_invoked: false; external_log_source = `log_chtMultiRegionSimpleFoam.txt`)
- `overall_status`: **FAIL** (3/3 residual targets not met → solver gate FAIL → overall FAIL; cap behavior unchanged from cycle-1)
- `validation_status`: **not_validated** (ingest cannot reach `validated`; fence intact)
- `bc_parsing_status`: **ok** (top-level field in bc_quality.json — multi-region walk succeeded)
- **`layout: multi_region`** (the headline Gap #11 fix verification — was implicitly single-region in cycle-1)
- `regions_detected`: `[region_cold_fluid, region_hot_fluid, region_solid]` — all 3 enumerated correctly from `0/region_*/` walk

## Net-new gaps surfaced

### Gap #32 (NEW · minor · semi-cosmetic) · `__none_laminar__` sentinel propagated into per-region `expected_fields` as if it were a real field

**Symptom:** Each region's `expected_fields` shows `[U, p, __none_laminar__]` and reports `__none_laminar__` as a missing file (e.g. `region_cold_fluid.fields.__none_laminar__.missing: true`, file path `0/region_cold_fluid/__none_laminar__`). The sentinel was meant (cycle-1 manifest authoring convention, see baseline §"Setup notes" item 4) to signal "laminar — no turbulence-field expected" — NOT a literal field name. The multi-region branch faithfully propagated the sentinel into per-region missing-file reporting.

**Suggested fix scope:** In `_collect_and_persist_bc` multi-region branch (`backends/openfoam.py:1779-`), filter out sentinel entries (`__none_laminar__`, anything bracketed by `__...__`) from the per-region `expected_fields` before walking. Spike-class (~10 LOC + 1 test). Or: prefer Gap #31-style derivation (`physics.turbulence_model: laminar` → `[]`) over manifest `turbulence_fields: [__none_laminar__]`. Already partially mitigated by the cycle-2 turb-model derivation logic for single-region; just needs to extend into the multi-region branch.

### Gap #33 (RECONFIRMED · pre-existing) · `bc_contract` gate intentionally BLOCKED on multi-region · documented next-step is correct

**Symptom:** `gates.bc_contract.status == BLOCKED` with `reason: multi_region_bc_validation_not_yet_wired`. This is **deliberate honest deferral**, not regression — the cycle-1 Gap #11 sub-DEC explicitly carved out the per-region bc_contract evaluation as charter-class (the "Suggested fix (DEC, not spike)" path in baseline). Cycle 2 landed the **data layer** (bc_quality.json regions dict) but intentionally **gated the verdict layer** behind a clear "not yet wired" message. This is correct discipline (no false PASS, no spurious FAIL on under-specified schema), but flagged here so milestone-cycle 3 readers don't mistake it for a regression.

## Artifacts pointer

- Captures dir: `/Users/Zhuanz/Desktop/cfd-audit-merge/.demo/captures/2026-05-22T1530Z/stage_cycle2_case_011_redogfood.txt`
- `bc_quality.json`: `/Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes/case_011_plate_fin_compact_hx/case/artifacts/bc_quality.json` (2451 bytes · multi_region layout)
- `trust_report.json`: `/Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes/case_011_plate_fin_compact_hx/case/artifacts/trust_report.json` (6668 bytes)
- `residuals.csv`: `/Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes/case_011_plate_fin_compact_hx/case/artifacts/residuals.csv` (13714 bytes · 3-field × 200-iter)
- `solver.log`: `/Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes/case_011_plate_fin_compact_hx/case/artifacts/solver.log` (428255 bytes · honest preamble + faithful transcription)
- `mesh_quality.log`: `/Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes/case_011_plate_fin_compact_hx/case/artifacts/mesh_quality.log` (3339 bytes · real Docker checkMesh output)
- `ingest_manifest.json`: `/Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes/case_011_plate_fin_compact_hx/case/artifacts/ingest_manifest.json` (SHA256 provenance preserved)
- Cycle-1 baseline backup: `/Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes/case_011_plate_fin_compact_hx/case/artifacts.cycle1_baseline_backup/`

## Verdict

**Cycle-1 fix verified ✓** — Gap #11 (multi-region BC parser) landed at the data layer exactly as designed: `layout: multi_region`, 3 regions enumerated, per-region fields walked, downstream verdict layer honestly BLOCKED with explicit "not yet wired" message rather than fabricating a verdict. Also surfaced TBD-15 + TBD-20 spike payoff: 3/3 residual fields tracked now (vs 1/1 in cycle-1) and Gap #12 (`next_step` text branch on ingest) landed too. Honesty fences all held. Two net-new gaps (#32 minor sentinel propagation; #33 documented deferral) but neither breaks the trust contract.

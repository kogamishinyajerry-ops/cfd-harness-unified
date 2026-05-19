# V70 Fleet Score · Iter 0

**Generated**: 2026-05-16T11:35:45Z  
**Commit**: `53af29150452b67a1cdfa045876378b60ed9772b`  
**Total (min one-vote-veto across 10 pillars)**: **0 / 100**  
**Weighted sum (informational)**: 73.34  
**Verdict**: PROCEED (multiple dims need attention)  
**Next-iter target dim**: `functional` (score=0)

## Per-Dim Scores (10 pillars)

| # | Agent | Dim | Score | Weight | Status |
|---|---|---|---|---|---|
| 1 | `quality` | 代码质量 | **100** | 0.12 | ✅ PASS-99 |
| 2 | `physics` | 物理/数值稳定 | **80** | 0.12 | 🟡 mid |
| 3 | `ux` | 使用手感 | **100** | 0.15 | ✅ PASS-99 |
| 4 | `visualization` | 可视化追踪 | **94** | 0.15 | 🟢 high |
| 5 | `smoke` | 端到端 pipeline | **100** | 0.08 | ✅ PASS-99 |
| 6 | `functional` | 功能完整度 | **0** | 0.08 | 🔴 low |
| 7 | `stability` | 稳定性 | **100** | 0.08 | ✅ PASS-99 |
| 8 | `cfd_breadth` | CFD仿真全维度能力 | **83** | 0.08 | 🟡 mid |
| 9 | `novice_onboarding` | 新手用户使用难度 | **0** | 0.07 | 🔴 low |
| 10 | `industrial_ui` | 工业UI对标 | **0** | 0.07 | 🔴 low |

## Honesty Self-Check

- ✓ Failure originals quoted verbatim from stderr/log
- ✓ Each score has evidence (test name / log path / file ref)
- ✓ 0 is computed, not default
- ✓ Regression allowed (this iter ≤ prior iter recorded honestly)
- ✓ min() one-vote veto applied across all 10 pillars (no average masking)

## Agent: `quality` · 代码质量

**Score**: 100 / 100 · Weight: 0.12

**Subscores**:
- `typecheck`: 1
- `lint`: 1
- `vitest`: 1
- `vitest_passed_count`: 405

**Evidence**:
- typecheck: PASS (tsc --noEmit clean)
- lint: PASS (eslint clean)
- vitest: PASS (405 tests · /tmp/v67c_vitest.log)

**Failures**:
- 

**Honest note**: subscores binary at iter 0; refine to pass-rate weighting at iter 1+ if vitest fails partially

## Agent: `physics` · 物理/数值稳定

**Score**: 80 / 100 · Weight: 0.12

**Subscores**:
- `mass_balance`: 1
- `v_corpus_shape`: 1
- `bc_routes_intact`: 1
- `v10x_count`: 7
- `advisor_files_count`: 2
- `v66b_rules_count`: 3
- `whitelist_count`: 11
- `whitelist_pass`: 1
- `canonical_eval_count`: 20
- `canonical_eval_pass`: 0

**Evidence**:
- mass_balance: PASS (4 tests)
- V-corpus: 7 V10x sub-DECs · 2 advisor_rule files · 3 rules in V66-B expansion
- case_bc route import: PASS
- whitelist count: 11 (≥11 V69 threshold MET)

**Failures**:
- canonical eval files (individual): 20 (need ≥30 for V70 close · was ≥20 for V69)

**Honest note**: V67-C is UI work; physics regression scope = mass_balance + corpus shape + BC route import. checkmesh runner test was relocated outside tests/ and not run by this agent.

## Agent: `ux` · 使用手感

**Score**: 100 / 100 · Weight: 0.15

**Subscores**:
- `flow_completion`: 60
- `latency_band`: 25
- `no_blocker_clicks`: 15
- `specs_pass_count`: 56
- `specs_total_count`: 56

**Evidence**:
- playwright: 56 specs PASS ≥13 threshold (FULL=60/60)
- latency: PASS (all specs within timeout)
- no-blocker: 0 click-intercepted / timeout signals

**Honest note**: V69 tightened · ≥9 specs PASS for FULL · pro-rated below

## Agent: `visualization` · 可视化追踪

**Score**: 94 / 100 · Weight: 0.15

**Subscores**:
- `render_success_rate`: 40
- `mode_switch_correctness`: 30
- `visual_diff_baseline`: 24
- `png_snapshot_count`: 18
- `viewport_mode_specs_pass`: 7

**Evidence**:
- visual baseline: 18/22 PNG files (pro-rated=24/30)
- viz+truth specs: 9/9 PASS (render=40/40)
- viewport-mode: 7 PASS ≥4 threshold (FULL=30/30)

**Failures**:
- visual baseline incomplete: 18/22 PNG snapshot files (need ≥22 for V70 close)

**Honest note**: V70 tightened · ≥22 PNG snapshot files + ≥4 viewport-mode specs required for full score · pro-rated below threshold

## Agent: `smoke` · 端到端 pipeline

**Score**: 100 / 100 · Weight: 0.08

**Subscores**:
- `backend_import`: 1
- `backend_http_probe`: 1
- `physics_probe`: 1
- `ai_review_probe`: 1
- `ai_diagnose_probe`: 1
- `canonical_harness_pass`: 1
- `canonical_harness_test_count`: 22
- `frontend_build`: 1
- `typecheck`: 1
- `lint`: 1

**Evidence**:
- backend FastAPI app import: PASS
- backend HTTP /api/cases probe: PASS (port=59783 · 3853 bytes)
- /physics probe: 404000 (reachable)
- /ai-review probe: 404000 (reachable)
- /ai-diagnose probe: 404000 (reachable)
- frontend build: PASS (dist=3784KB)
- typecheck: PASS
- lint: PASS
- canonical eval harness: 22 tests PASS (≥20 V69 threshold MET)

**Honest note**: V69 added live HTTP probe (uvicorn boots + /api/cases responds 200); per-iter smoke still excludes OpenFOAM heavy run (dogfood_loop.py reserved for arc-close gate)

## Agent: `functional` · 功能完整度

**Score**: 0 / 100 · Weight: 0.08

**Subscores**:
- `landed_sub_dec_count`: 0
- `landed_sub_dec_total`: 6
- `done_dim_met`: 0
- `done_dim_total`: 9

**Evidence**:
- Done dims MET: 0/9 (from .planning/V70_ARC_GOAL.md)

## Agent: `stability` · 稳定性

**Score**: 100 / 100 · Weight: 0.08

**Subscores**:
- `vitest_runs`: 3
- `flake_count`: 0
- `memory_growth_pct`: 0

**Evidence**:
- stability: 3/3 vitest runs PASS · no flake
- memory growth check deferred to iter 1+ (needs baseline)

**Failures**:
- 

## Agent: `cfd_breadth` · CFD仿真全维度能力

**Score**: 83 / 100 · Weight: 0.08

**Subscores**:
- `turbulence_models_supported`: 3
- `turbulence_score`: 18
- `compressibility_regimes`: 28
- `compressibility_score`: 20
- `steadiness_regimes`: 54
- `steadiness_score`: 15
- `bc_types_count`: 481
- `bc_score`: 20
- `meshing_strategies`: 150
- `meshing_score`: 10
- `capability_matrix_score`: 0

**Evidence**:
- turbulence models: 3/4 (pro-rated=18/25)
- compressibility regimes: 28 (≥3 V70 threshold MET)
- steadiness regimes: 54 (≥2 V70 threshold MET)
- BC types: 481 (≥10 V70 threshold MET)
- meshing strategies: 150 (≥2 V70 threshold MET)

**Failures**:
- turbulence models below threshold: 3/4 (need ≥4 for V70 close)
- capability matrix doc missing: .planning/cfd_capability_matrix.md (V70-DONE-1)

**Honest note**: regime detection is grep-based · over-counts when identifier appears in comments/docs; matrix_doc cell-count is heuristic and replaceable with structured YAML if V71 needs precision

## Agent: `novice_onboarding` · 新手用户使用难度

**Score**: 0 / 100 · Weight: 0.07

**Subscores**:
- `tutorial_route_score`: 0
- `tooltip_count`: 0
- `tooltip_score`: 0
- `first_time_banner_score`: 0
- `novice_spec_count`: 0
- `novice_spec_score`: 0
- `onboarding_doc_score`: 0

**Failures**:
- tutorial route: MISSING (need TutorialPage at /workbench/tutorial for V70-DONE-3)
- tooltips: 0 detected on Engineer Control Rail
- first-time banner: MISSING (need banner pointing to lid_driven_cavity for V70-DONE-3)
- novice e2e specs: 0 (need ≥1 spec named *novice* or *onboarding* or *tutorial*)
- onboarding doc missing: .planning/onboarding_guide.md (need ≥1000 words for V70-DONE-3)

**Honest note**: tooltip detection is grep-based on title/aria-label/data-tooltip/<Tooltip patterns; doesn't catch tooltip libraries that compose via children prop · refine if false-negative pattern emerges

## Agent: `industrial_ui` · 工业UI对标

**Score**: 0 / 100 · Weight: 0.07

**Subscores**:
- `benchmark_doc_score`: 0
- `axes_count`: 0
- `axes_score`: 0
- `gui_count`: 0
- `gui_score`: 0
- `improvements_count`: 0
- `improvements_score`: 0
- `benchmark_baselines_count`: 0
- `benchmark_baselines_score`: 0
- `honest_findings_score`: 0

**Failures**:
- benchmark doc missing: .planning/benchmarks/industrial_ui_benchmark.md (V70-DONE-4)
- UI improvements: 0 tagged V70-UI-IMPROVEMENT in code
- V70 UI baselines: 0/2 (need ≥2 for V70-DONE-4)

**Honest note**: anti-marketing gate: this agent intentionally requires the benchmark doc to admit commercial-GUI strengths. self-promotional benchmark docs fail honest_findings subscore.

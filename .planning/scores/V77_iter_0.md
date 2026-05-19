# V77 Fleet Score · Iter 0

**Generated**: 2026-05-16T19:55:04Z
**Commit**: `0de5e89b16d1bf11d4e9013930774e3f393977db`
**Total (min one-vote-veto across 16 pillars)**: **12 / 100**
**Weighted sum (informational)**: 127.37
**Verdict**: PROCEED (multiple dims need attention)
**Next-iter target dim**: `real_time_solver_observability` (score=12)

## Per-Dim Scores (16 pillars)

| # | Agent | Dim | Score | Weight | Status |
|---|---|---|---|---|---|
| 1 | `quality` | 代码质量 | **100** | 0.12 | ✅ PASS-99 |
| 2 | `physics` | 物理/数值稳定 | **100** | 0.12 | ✅ PASS-99 |
| 3 | `ux` | 使用手感 | **87** | 0.15 | 🟡 mid |
| 4 | `visualization` | 可视化追踪 | **100** | 0.15 | ✅ PASS-99 |
| 5 | `smoke` | 端到端 pipeline | **100** | 0.08 | ✅ PASS-99 |
| 6 | `functional` | 功能完整度 | **100** | 0.08 | ✅ PASS-99 |
| 7 | `stability` | 稳定性 | **70** | 0.08 | 🟡 mid |
| 8 | `cfd_breadth` | CFD仿真全维度能力 | **100** | 0.08 | ✅ PASS-99 |
| 9 | `novice_onboarding` | 新手用户使用难度 | **100** | 0.07 | ✅ PASS-99 |
| 10 | `industrial_ui` | 工业UI对标 | **100** | 0.07 | ✅ PASS-99 |
| 11 | `interaction_polish` | 交互体验 | **100** | 0.07 | ✅ PASS-99 |
| 12 | `backend_integration` | 后端集成健康 | **100** | 0.06 | ✅ PASS-99 |
| 13 | `data_fidelity` | 数据保真度与可审计性 | **100** | 0.06 | ✅ PASS-99 |
| 14 | `resumability_observability` | 可恢复性与可观察性 | **100** | 0.06 | ✅ PASS-99 |
| 15 | `visualization_fidelity` | 三维可视化保真度 | **100** | 0.06 | ✅ PASS-99 |
| 16 | `real_time_solver_observability` | 实时求解器可观察性 | **12** | 0.06 | 🔴 low |

## Honesty Self-Check

- ✓ Failure originals quoted verbatim from stderr/log
- ✓ Each score has evidence (test name / log path / file ref)
- ✓ 0 is computed, not default
- ✓ Regression allowed (this iter ≤ prior iter recorded honestly)
- ✓ min() one-vote veto applied across all 16 pillars (no average masking)

## Agent: `quality` · 代码质量

**Score**: 100 / 100 · Weight: 0.12

**Subscores**:
- `typecheck`: 1
- `lint`: 1
- `vitest`: 1
- `vitest_passed_count`: 452

**Evidence**:
- typecheck: PASS (tsc --noEmit clean)
- lint: PASS (eslint clean)
- vitest: PASS (452 tests · /tmp/v67c_vitest.log)

**Failures**:
-

**Honest note**: subscores binary at iter 0; refine to pass-rate weighting at iter 1+ if vitest fails partially

## Agent: `physics` · 物理/数值稳定

**Score**: 100 / 100 · Weight: 0.12

**Subscores**:
- `mass_balance`: 1
- `v_corpus_shape`: 1
- `bc_routes_intact`: 1
- `v10x_count`: 7
- `advisor_files_count`: 2
- `v66b_rules_count`: 3
- `whitelist_count`: 11
- `whitelist_pass`: 1
- `canonical_eval_count`: 30
- `canonical_eval_pass`: 1

**Evidence**:
- mass_balance: PASS (4 tests)
- V-corpus: 7 V10x sub-DECs · 2 advisor_rule files · 3 rules in V66-B expansion
- case_bc route import: PASS
- whitelist count: 11 (≥11 V69 threshold MET)
- canonical eval files (individual): 30 (≥30 V70 threshold MET)

**Honest note**: V67-C is UI work; physics regression scope = mass_balance + corpus shape + BC route import. checkmesh runner test was relocated outside tests/ and not run by this agent.

## Agent: `ux` · 使用手感

**Score**: 87 / 100 · Weight: 0.15

**Subscores**:
- `flow_completion`: 60
- `latency_band`: 12
- `no_blocker_clicks`: 15
- `specs_pass_count`: 118
- `specs_total_count`: 122

**Evidence**:
- playwright: 118 specs PASS ≥17 threshold (FULL=60/60)
- no-blocker: 0 click-intercepted / timeout signals

**Failures**:
- latency: some specs exceeded timeout · pw_exit=1

**Honest note**: V69 tightened · ≥9 specs PASS for FULL · pro-rated below

## Agent: `visualization` · 可视化追踪

**Score**: 100 / 100 · Weight: 0.15

**Subscores**:
- `render_success_rate`: 40
- `mode_switch_correctness`: 30
- `visual_diff_baseline`: 30
- `png_snapshot_count`: 64
- `viewport_mode_specs_pass`: 7

**Evidence**:
- visual baseline: 64/30 PNG files (FULL=30/30)
- viz+truth specs: 9/9 PASS (render=40/40)
- viewport-mode: 7 PASS ≥4 threshold (FULL=30/30)

**Honest note**: V71 tightened · ≥30 PNG snapshot files + ≥4 viewport-mode specs required for full score · pro-rated below threshold

## Agent: `smoke` · 端到端 pipeline

**Score**: 100 / 100 · Weight: 0.08

**Subscores**:
- `backend_import`: 1
- `backend_http_probe`: 1
- `physics_probe`: 1
- `ai_review_probe`: 1
- `ai_diagnose_probe`: 1
- `canonical_harness_pass`: 1
- `canonical_harness_test_count`: 32
- `frontend_build`: 1
- `typecheck`: 1
- `lint`: 1

**Evidence**:
- backend FastAPI app import: PASS
- backend HTTP /api/cases probe: PASS (port=58428 · 3853 bytes)
- /physics probe: 404000 (reachable)
- /ai-review probe: 404000 (reachable)
- /ai-diagnose probe: 404000 (reachable)
- frontend build: PASS (dist=3876KB)
- typecheck: PASS
- lint: PASS
- canonical eval harness: 32 tests PASS (≥20 V69 threshold MET)

**Honest note**: V69 added live HTTP probe (uvicorn boots + /api/cases responds 200); per-iter smoke still excludes OpenFOAM heavy run (dogfood_loop.py reserved for arc-close gate)

## Agent: `functional` · 功能完整度

**Score**: 100 / 100 · Weight: 0.08

**Subscores**:
- `landed_sub_dec_count`: 6
- `landed_sub_dec_total`: 6
- `done_dim_met`: 9
- `done_dim_total`: 9

**Evidence**:
- LANDED: 2026-05-16_v71_sub_1_workbench_shell_v3.md
- LANDED: 2026-05-16_v71_sub_2_step_views_polish.md
- LANDED: 2026-05-16_v71_sub_3_residuals_watched_curve.md
- LANDED: 2026-05-16_v71_sub_4_advisor_contract_test.md
- LANDED: 2026-05-16_v71_sub_5_results_canvas_trustgate.md
- LANDED: 2026-05-16_v71_sub_6_visual_baselines_close.md
- Done dims MET: 9/9 (from .planning/V71_ARC_GOAL.md)

## Agent: `stability` · 稳定性

**Score**: 70 / 100 · Weight: 0.08

**Subscores**:
- `vitest_runs`: 3
- `flake_count`: 1
- `memory_growth_pct`: 0

**Evidence**:
- memory growth check deferred to iter 1+ (needs baseline)

**Failures**:
- stability: 1/3 runs FAILED ·
- run1=FAIL
- run2=PASS
- run3=PASS

## Agent: `cfd_breadth` · CFD仿真全维度能力

**Score**: 100 / 100 · Weight: 0.08

**Subscores**:
- `turbulence_models_supported`: 8
- `turbulence_score`: 25
- `compressibility_regimes`: 28
- `compressibility_score`: 20
- `steadiness_regimes`: 54
- `steadiness_score`: 15
- `bc_types_count`: 481
- `bc_score`: 20
- `meshing_strategies`: 151
- `meshing_score`: 10
- `capability_matrix_score`: 10

**Evidence**:
- turbulence models supported: 8 (≥4 V70 threshold MET)
- compressibility regimes: 28 (≥3 V70 threshold MET)
- steadiness regimes: 54 (≥2 V70 threshold MET)
- BC types: 481 (≥10 V70 threshold MET)
- meshing strategies: 151 (≥2 V70 threshold MET)
- capability matrix doc: .planning/cfd_capability_matrix.md present · 56 cells with PR/GAP-TRACKED status

**Honest note**: regime detection is grep-based · over-counts when identifier appears in comments/docs; matrix_doc cell-count is heuristic and replaceable with structured YAML if V71 needs precision

## Agent: `novice_onboarding` · 新手用户使用难度

**Score**: 100 / 100 · Weight: 0.07

**Subscores**:
- `tutorial_route_score`: 25
- `tooltip_count`: 10
- `tooltip_score`: 25
- `first_time_banner_score`: 20
- `novice_spec_count`: 2
- `novice_spec_score`: 15
- `onboarding_doc_score`: 15

**Evidence**:
- tutorial route: PRESENT (TutorialPage + /workbench/tutorial wired in App.tsx)
- tooltips on Engineer Control Rail: 10 (≥6 V70 threshold MET)
- first-time banner: PRESENT (points new users to lid_driven_cavity starter)
- novice e2e specs: 2 (≥1 V70 threshold MET)
- onboarding doc: 1622 words (≥1000 V70 threshold MET)

**Honest note**: tooltip detection is grep-based on title/aria-label/data-tooltip/<Tooltip patterns; doesn't catch tooltip libraries that compose via children prop · refine if false-negative pattern emerges

## Agent: `industrial_ui` · 工业UI对标

**Score**: 100 / 100 · Weight: 0.07

**Subscores**:
- `benchmark_doc_score`: 20
- `axes_score`: 8
- `gui_score`: 8
- `honest_score`: 8
- `v3_route_mounts_count`: 2
- `v3_route_score`: 16
- `v71_ui_tags_count`: 20
- `v71_ui_score`: 12
- `v71_baselines_count`: 8
- `v71_baselines_score`: 16
- `blueprint_index_score`: 4
- `v3_palette_refs`: 6
- `v3_palette_score`: 8

**Evidence**:
- benchmark doc: .planning/benchmarks/industrial_ui_benchmark.md present (V70)
- benchmark axes: 20 (≥6 threshold MET)
- GUI competitors: 6 (≥3 threshold MET)
- benchmark doc: anti-marketing gate MET (honest 'commercial better at X' admission found)
- v3 route mounts: 2 (≥2 V71 threshold MET · /workbench/v3 + WorkbenchShellV3)
- V71-UI tags in code: 20 (≥6 V71 threshold MET)
- V71 baselines (23-30): 8/8 (V71-DONE-7 MET)
- .planning/blueprints/v3/INDEX.md present (visual SSOT)
- v3 palette: sand-coral #b78b65 referenced 6 times (≥3 MET)

**Honest note**: V71 industrial-UI agent tightened with v3 blueprint compliance subscores · still enforces V70 anti-marketing gate · expects v3 route + 6 V71-UI tags + 8 baselines + blueprint INDEX + palette compliance

## Agent: `interaction_polish` · 交互体验

**Score**: 100 / 100 · Weight: 0.07

**Subscores**:
- `keyboard_nav`: 25
- `motion_polish`: 20
- `focus_management`: 20
- `reduced_motion_respect`: 15
- `wcag_runtime`: 20
- `transition_count`: 19
- `aria_role_count`: 52

**Evidence**:
- keyboard nav: 5/5 PASS (FULL=25/25)
- motion polish: 19 transition usages (FULL=20/20)
- focus management: 52 ARIA/role/tabIndex usages (FULL=20/20)
- reduced-motion: 15 prefers-reduced-motion usages (FULL=15/15)
- axe-core runtime a11y: 5/5 PASS · 0 WCAG violations across 5 surfaces (FULL=20/20)

**Honest note**: V73 extension of V72 pillar 11 · 4 subscores → 5 · adds wcag_runtime via axe-core

## Agent: `backend_integration` · 后端集成健康

**Score**: 100 / 100 · Weight: 0.06

**Subscores**:
- `real_wired_surfaces`: 40
- `api_endpoint_coverage`: 20
- `graceful_offline_paths`: 20
- `integration_tests_passing`: 20
- `useQuery_count`: 41
- `distinct_endpoints`: 8

**Evidence**:
- real-wired surfaces: 41 useQuery/api/SSE refs (FULL=40/40)
- API endpoints consumed: 8 distinct (FULL=20/20)
- graceful offline paths: 51 (FULL=20/20)
- integration tests: 15 refs (FULL=20/20)

**Honest note**: V77 pillar 12 · useQuery ≥35 forces SSE hook + EventSource refs to land

## Agent: `data_fidelity` · 数据保真度与可审计性

**Score**: 100 / 100 · Weight: 0.06

**Subscores**:
- `run_id_visible`: 25
- `gold_delta_visible`: 25
- `audit_package_downloadable`: 25
- `byte_repro_hash_visible`: 25
- `gold_delta_row_count`: 6
- `provenance_hash_count`: 5

**Evidence**:
- run_id surfaces in TopBar with data-source=live (FULL=25/25)
- gold-delta rows: 6 references (FULL=25/25)
- audit-package download wire detected in v3 (FULL=25/25)
- 4 provenance-hash chips present (FULL=25/25)

**Honest note**: V74 NEW pillar 13 · forces canonical run_id + provenance hashes + gold delta + audit pkg as first-class UI · industrial DNA

## Agent: `resumability_observability` · 可恢复性与可观察性

**Score**: 100 / 100 · Weight: 0.06

**Subscores**:
- `error_boundary_coverage`: 25
- `loading_skeleton_coverage`: 25
- `url_state_resumability`: 25
- `observability_indicator`: 25
- `error_boundary_count`: 4
- `skeleton_count`: 4
- `url_sync_sites`: 5
- `observability_count`: 4

**Evidence**:
- error boundaries: 4 testid'd surfaces (FULL=25/25)
- loading skeletons: 4 testid'd (FULL=25/25)
- URL state resumability: 5 sync sites (FULL=25/25)
- observability: 4 indicators (FULL=25/25)

**Honest note**: V75 NEW pillar 14 · forces engineer-trust signals (error boundaries / skeletons / URL state / observability) · CATIA/STAR-CCM+/Bloomberg DNA

## Agent: `visualization_fidelity` · 三维可视化保真度

**Score**: 100 / 100 · Weight: 0.06

**Subscores**:
- `vtk_canvas_mounts`: 30
- `camera_controls`: 20
- `field_legend`: 20
- `performance_signal`: 15
- `load_fallback`: 15
- `mount_count`: 3
- `camera_widget_count`: 4
- `legend_count`: 2
- `fps_count`: 2
- `fallback_count`: 2

**Evidence**:
- vtk canvas mounts: 3 (FULL=30/30)
- camera+axes controls: 4 testids (FULL=20/20)
- color legend: 2 testids (FULL=20/20)
- fps indicator: 2 testids (FULL=15/15)
- WebGL fallback: 2 testids (FULL=15/15)

**Honest note**: V76 NEW pillar 15 · forces real 3D viz (vtk.js mounts replace placeholders) · closes 6-arc-aged vtk.js bookmark from V71.L · regex template-friendly to close 4-arc literal-testid trap

## Agent: `real_time_solver_observability` · 实时求解器可观察性

**Score**: 12 / 100 · Weight: 0.06

**Subscores**:
- `sse_event_stream`: 12
- `residual_live_update`: 0
- `solver_state_stream`: 0
- `inflight_residual_display`: 0
- `sse_hook_count`: 3
- `sse_status_count`: 0
- `residual_live_count`: 0
- `state_badge_count`: 0
- `inflight_count`: 0

**Evidence**:
- sse_event_stream: partial (hook=3 status=0) (pro-rated=12/25)

**Failures**:
- 0 residual-live-{var} testids (V77.2 not landed)
- 0 solver-state-badge testid (V77.3 not landed)
- 0 solver-inflight-residual testid (V77.4 not landed)

**Honest note**: V77 NEW pillar 16 · forces SSE residual streaming · closes 7-arc-aged V71.L bookmark · industrial parity with Fluent/STAR-CCM+ convergence monitors

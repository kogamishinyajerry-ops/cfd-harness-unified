# Codex Round 2 Review · DEC-V61-058 post-Round-1-fixes

**Run:** 2026-04-25 · gpt-5.4 · cx-auto (94% quota)
**Reviewing:** Cumulative branch state at commit 8bd3df4 (round 1 fixes a00ff88 + 641cf9f + a2b1d63 + curated log)
**Verdict:** `APPROVE_WITH_COMMENTS`

## Summary

Codex independently re-ran the F1 reuse repro in-process under `.venv/bin/python`:
First call with `angle_of_attack=4` writes the 4° freestream; second call on the same TaskSpec
after changing only `angle_of_attack=8` writes the 8° freestream; stale 4° vertical component
absent. `boundary_conditions` after second call contains only caller data plus U_inf/p_inf/rho,
NOT adapter-cached alpha_deg/U_inf_x/U_inf_z. F1 verified fixed.

F2: 4 new pytest cases all passed locally.

## Findings

| ID | Severity | File:Line | Detail | Status |
|---|---|---|---|---|
| C4 | Comment-only | knowledge/gold_standards/naca0012_airfoil.yaml:31, :60; src/foam_agent_adapter.py:7183-7184 | Residual stale α-routing narrative contradicts landed adapter logic | LANDED commit 0fe6aba |

## Per-question highlights

- Q1(a): precedence semantically correct — angle_of_attack is whitelist canonical at knowledge/whitelist.yaml:244-247; no other module consumes bc["alpha_deg"].
- Q1(b): all F1 failure modes covered (no stateful persistence, reuse regression, dual-key precedence, non-numeric fail-closed, bool fail-closed). One adjacent variant deferred (first call alpha_deg, second call adds angle_of_attack while leaving alias) — not a blocker.
- Q1(c): reusing ParameterPlumbingError is correct; no AlphaInputError subtype needed.
- Q2(a-c): math.isfinite() is the right guard; error messages have sufficient diagnostics; compute_lift_slope already had finite-value guard.
- Q3(a-b): no regression in chord_length/U_inf/rho persistence; Cl=0 at α=0 sanity path passes.
- Q4: round 2 ruling is APPROVE_WITH_COMMENTS (not full APPROVE because of C4 stale narrative).

## Round 3 readiness — Batch C/D/E priorities

- **C-1**: wire ParameterPlumbingError + AirfoilExtractorError through comparator/attestor as explicit gate failures (never defaulted/swallowed).
- **C-2**: keep α provenance explicit end-to-end with angle_of_attack as canonical external name.
- **C-3**: land deferred 2-point linearity_check_applicable flag before any Stage C path can present a 2-point slope as 3-point linearity-checked.
- **E-1**: live-run confirmation of α=+8° → Cl>0 + real yPlus FO output.

---

## Codex output (curated, verbatim from log)

   829	    def _hazard(self, spec: DashboardCaseSpec, report: Dict[str, Any], contract_status: str) -> str:
   830	        if spec.report_case_id == "cylinder_crossflow":
   831	            return "Strouhal 通过 canonical-band shortcut 可能被伪确认；Cd / Cl_rms / wake deficit 则仍有物理含义。"
   832	        if spec.report_case_id == "turbulent_flat_plate":
   833	            return "Cf>0.01 时可能走 Spalding substitution；结果可用，但必须持续保留 runtime fallback 透明度。"
   834	        if spec.report_case_id == "differential_heated_cavity":
   835	            return "extractor 方法学已修正，但 gold-reference 语义与 literature/工况冲突仍未裁决。"
   836	        if spec.report_case_id == "axisymmetric_impinging_jet":
   837	            return "observable 命名与 literature 目标不一致，最容易造成“数值 PASS 但科学含义错位”的误读。"
   838	        if spec.report_case_id == "duct_flow":
   839	            return "Q-2 Path A 落地后不再是类别错误；remaining hazard 是 Jones-vs-Colebrook 相关式 2% 量级差别，需要做一次新 auto_verify_report 才能关闭。"
   840	        if spec.report_case_id == "fully_developed_plane_channel_flow":
   841	            return "当前是 comparator / solver 路线不闭环，不适合再用局部 patch 把它包装成可验收结果。"
   842	        if spec.report_case_id == "naca0012_airfoil":
   843	            return "偏差集中在前缘与近壁分辨；风险在于被 UI 误读成“只差一点的 clean PASS”。"
   844	        return contract_status.split("—", 1)[0].strip()
   845	
   846	    def _lane(self, spec: DashboardCaseSpec, contract_class: str, verdict: str) -> str:
   847	        if contract_class == "COMPATIBLE" and verdict == "PASS":
   848	            return "demo"

codex
**Verdict**

`APPROVE_WITH_COMMENTS`

No new correctness findings. F1 and F2 are fixed. One residual comment-only cleanup remains.

**Findings**

| ID | Severity | File:Line | Detail |
|---|---|---|---|
| C4 | Comment-only | `knowledge/gold_standards/naca0012_airfoil.yaml:31`, `:60`; `src/foam_agent_adapter.py:7183-7184` | Residual stale α-routing narrative remains. These lines still say the canonical input is `task_spec.alpha_deg` or that non-zero AoA is not implemented, which contradicts the landed adapter logic at `src/foam_agent_adapter.py:6448-6469`. Not blocking, but C1 is not fully cleaned up, and the stale `contract_status` text is surfaced verbatim by `src/report_engine/contract_dashboard.py:746,763`. |

**Per-Question Response**

**Q1**
- **(a)** Yes. `angle_of_attack` is the whitelist canonical key at `knowledge/whitelist.yaml:244-247`, and the adapter now resolves it first at `src/foam_agent_adapter.py:6448-6450`. Repo-wide runtime references show no other module consumes `task_spec.boundary_conditions["alpha_deg"]`; `compute_cl_cd` takes `alpha_deg` as a direct function argument, not from `bc` (`src/airfoil_extractors.py:178-246`).
- **(b)** The failure modes I called out are covered: no stateful persistence (`src/foam_agent_adapter.py:6478-6486`), reuse regression (`tests/test_foam_agent_adapter.py:2782-2814`), dual-key precedence (`:2816-2835`), non-numeric fail-closed (`:2837-2849`), and bool fail-closed (`:2851-2863`). The only adjacent variant not literally encoded as a test is “first call via `alpha_deg`, second call adds `angle_of_attack` while leaving alias present”; given the precedence rule and my direct dual-key repro, I do not see that as a remaining blocker.
- **(c)** Reusing `ParameterPlumbingError` is fine. It is already the adapter’s pre-solver validation bucket (`src/foam_agent_adapter.py:94-99`, `:3398-3488`, `:6458-6466`), and I found no catch site that needs an `AlphaInputError` subtype.

**Q2**
- **(a)** `math.isfinite()` is the right guard. It rejects `NaN` and `±inf` and intentionally accepts legitimate finite values, including `0.0` and subnormals. I would not add subnormal-specific rejection here.
- **(b)** Yes. `compute_cl_cd` includes file, row context, and offending `Cl`/`Cd` values (`src/airfoil_extractors.py:233-240`). `compute_y_plus_max` includes file, patch, and `min/max/avg` (`:419-423`). That is sufficient for downstream comparator/UI surfacing.
- **(c)** `compute_lift_slope` already has the same class of finite-value guard plus a degenerate-fit check (`src/airfoil_extractors.py:278-294`). That is adequate.

**Q3**
- **(a)** No regression there. The adapter still persists `chord_length`/`U_inf`/`p_inf`/`rho` at `src/foam_agent_adapter.py:6482-6486`, and the Cp emission path still reads them from `boundary_conditions` at `src/foam_agent_adapter.py:8651-8668`. The updated regression test asserts exactly that contract at `tests/test_foam_agent_adapter.py:2749-2780`.
- **(b)** No. `math.isfinite(0.0)` passes, and I directly ran `compute_cl_cd` with a final row `Cl=0.0, Cd=0.008`; it returned a normal `CoeffsResult`. The α=0 sanity-path test also still passes at `tests/test_foam_agent_adapter.py:2633-2638`.

**Q4**
- The substantive round-1 findings are resolved.
- This is not `CHANGES_REQUIRED`.
- A clean `APPROVE` is slightly too strong because of the residual stale α-routing narrative above.
- `APPROVE_WITH_COMMENTS` is the right ruling. Batch C can proceed.

**Round 2 Specific Verification**

I re-ran the original F1 reuse repro directly in-process under `.venv/bin/python` and it now passes: first call with `angle_of_attack=4` writes the 4° freestream, second call on the same `TaskSpec` after changing only `angle_of_attack=8` writes the 8° freestream, and the stale 4° vertical component is absent. `boundary_conditions` after the second call contains only caller data plus `U_inf`/`p_inf`/`rho`, not adapter-cached `alpha_deg`/`U_inf_x`/`U_inf_z`.

I also ran the four new F2 pytest cases locally; all 4 passed. Local note only: the default pytest interpreter on this machine is missing `PyYAML`, and the repo `.venv` currently lacks `pytest`, so the adapter-path verification had to be done via direct `.venv` Python execution rather than `.venv` pytest.

**Round 3 Readiness Assessment**

- Batch C priority 1: make sure `ParameterPlumbingError` and `AirfoilExtractorError` are wired through comparator/attestor as explicit gate failures, never defaulted.
- Batch C priority 2: keep α provenance explicit end-to-end, with `angle_of_attack` as the canonical external name.
- Batch C priority 3: land the deferred 2-point `linearity_check_applicable` work before any Stage C path can present a 2-point slope result as if the 3-point linearity check ran.
- Batch E priority: live-run confirmation of the already-correct architecture, especially `α=+8° -> Cl>0` and real `yPlus` FO output.


tokens used
100,575
**Verdict**

`APPROVE_WITH_COMMENTS`

No new correctness findings. F1 and F2 are fixed. One residual comment-only cleanup remains.

**Findings**

| ID | Severity | File:Line | Detail |
|---|---|---|---|
| C4 | Comment-only | `knowledge/gold_standards/naca0012_airfoil.yaml:31`, `:60`; `src/foam_agent_adapter.py:7183-7184` | Residual stale α-routing narrative remains. These lines still say the canonical input is `task_spec.alpha_deg` or that non-zero AoA is not implemented, which contradicts the landed adapter logic at `src/foam_agent_adapter.py:6448-6469`. Not blocking, but C1 is not fully cleaned up, and the stale `contract_status` text is surfaced verbatim by `src/report_engine/contract_dashboard.py:746,763`. |

**Per-Question Response**

**Q1**
- **(a)** Yes. `angle_of_attack` is the whitelist canonical key at `knowledge/whitelist.yaml:244-247`, and the adapter now resolves it first at `src/foam_agent_adapter.py:6448-6450`. Repo-wide runtime references show no other module consumes `task_spec.boundary_conditions["alpha_deg"]`; `compute_cl_cd` takes `alpha_deg` as a direct function argument, not from `bc` (`src/airfoil_extractors.py:178-246`).
- **(b)** The failure modes I called out are covered: no stateful persistence (`src/foam_agent_adapter.py:6478-6486`), reuse regression (`tests/test_foam_agent_adapter.py:2782-2814`), dual-key precedence (`:2816-2835`), non-numeric fail-closed (`:2837-2849`), and bool fail-closed (`:2851-2863`). The only adjacent variant not literally encoded as a test is “first call via `alpha_deg`, second call adds `angle_of_attack` while leaving alias present”; given the precedence rule and my direct dual-key repro, I do not see that as a remaining blocker.
- **(c)** Reusing `ParameterPlumbingError` is fine. It is already the adapter’s pre-solver validation bucket (`src/foam_agent_adapter.py:94-99`, `:3398-3488`, `:6458-6466`), and I found no catch site that needs an `AlphaInputError` subtype.

**Q2**
- **(a)** `math.isfinite()` is the right guard. It rejects `NaN` and `±inf` and intentionally accepts legitimate finite values, including `0.0` and subnormals. I would not add subnormal-specific rejection here.
- **(b)** Yes. `compute_cl_cd` includes file, row context, and offending `Cl`/`Cd` values (`src/airfoil_extractors.py:233-240`). `compute_y_plus_max` includes file, patch, and `min/max/avg` (`:419-423`). That is sufficient for downstream comparator/UI surfacing.
- **(c)** `compute_lift_slope` already has the same class of finite-value guard plus a degenerate-fit check (`src/airfoil_extractors.py:278-294`). That is adequate.

**Q3**
- **(a)** No regression there. The adapter still persists `chord_length`/`U_inf`/`p_inf`/`rho` at `src/foam_agent_adapter.py:6482-6486`, and the Cp emission path still reads them from `boundary_conditions` at `src/foam_agent_adapter.py:8651-8668`. The updated regression test asserts exactly that contract at `tests/test_foam_agent_adapter.py:2749-2780`.
- **(b)** No. `math.isfinite(0.0)` passes, and I directly ran `compute_cl_cd` with a final row `Cl=0.0, Cd=0.008`; it returned a normal `CoeffsResult`. The α=0 sanity-path test also still passes at `tests/test_foam_agent_adapter.py:2633-2638`.

**Q4**
- The substantive round-1 findings are resolved.
- This is not `CHANGES_REQUIRED`.
- A clean `APPROVE` is slightly too strong because of the residual stale α-routing narrative above.
- `APPROVE_WITH_COMMENTS` is the right ruling. Batch C can proceed.

**Round 2 Specific Verification**

I re-ran the original F1 reuse repro directly in-process under `.venv/bin/python` and it now passes: first call with `angle_of_attack=4` writes the 4° freestream, second call on the same `TaskSpec` after changing only `angle_of_attack=8` writes the 8° freestream, and the stale 4° vertical component is absent. `boundary_conditions` after the second call contains only caller data plus `U_inf`/`p_inf`/`rho`, not adapter-cached `alpha_deg`/`U_inf_x`/`U_inf_z`.

I also ran the four new F2 pytest cases locally; all 4 passed. Local note only: the default pytest interpreter on this machine is missing `PyYAML`, and the repo `.venv` currently lacks `pytest`, so the adapter-path verification had to be done via direct `.venv` Python execution rather than `.venv` pytest.

**Round 3 Readiness Assessment**

- Batch C priority 1: make sure `ParameterPlumbingError` and `AirfoilExtractorError` are wired through comparator/attestor as explicit gate failures, never defaulted.
- Batch C priority 2: keep α provenance explicit end-to-end, with `angle_of_attack` as the canonical external name.
- Batch C priority 3: land the deferred 2-point `linearity_check_applicable` work before any Stage C path can present a 2-point slope result as if the 3-point linearity check ran.
- Batch E priority: live-run confirmation of the already-correct architecture, especially `α=+8° -> Cl>0` and real `yPlus` FO output.



# ARC-GOAL · Advisor Substrate Arc

**Plan SSOT**: [.planning/2026-05-13_advisor_substrate_arc_plan.md](2026-05-13_advisor_substrate_arc_plan.md)
**Started**: 2026-05-13
**Mode**: milestone-driven (no calendar)

> 读这个文件 90 秒能回答：「这个 arc 完了没？」「该不该开新 arc？」「下个 session 接什么？」

---

## North Star（一句话）

> **让 "Claude Code session = 工业级 CFD advisor" 这个命题从单 case anecdote 升级为跨 6 个工业 case 的可复现实证 + advisor stack 代码层闭环。**

---

## Done Definition（必须全部命中）

| # | 维度 | 起点 | Done | 验证方式 |
|---|---|---|---|---|
| 1 | Track C session 通过 case 数 | 1 | **≥ 6** | `ls .planning/retrospectives/*track_c*.md \| wc -l` |
| 2 | LANDED advisor 数（含 D-class ≥ 1） | 4 | **≥ 8** | `grep -c "Status.*[Ll]anded" .planning/cross_cuts/advisor_coverage_2026-05-09.md` |
| 3 | V-series 行数 | 84 | **≥ 100** | `grep -c "^### V" docs/openfoam_corpus/industrial_solver_findings_v_series.md` |
| 4 | End-to-end solver 跑通 numerics class 数 | 1 | **≥ 3** | retro 里显式列 numerics class 标签 |
| 5 | 雷达图左半轴均分 (CAD+网格+物理+求解器+后处理)/5 | 6.4 | **≥ 7.2** | 重跑 `build_radar.py` v2 (M-RADAR-V2) |
| 6 | 雷达图右半轴均分 (CLI+AI+审计)/3 | 8.7 | **≥ 8.7 维持** | 同上 |

**任一未达成 = arc 不 close**，启动 root-cause retro。

---

## Done 条件**不算** Done 的反命题（防 sediment-only-not-advisor）

- ❌ V-series 加到 100+ 但 advisor stack 仍 4 个 → 失败（只 sediment 不 advisor）
- ❌ Advisor 8 个 land 但 Track C 仍 1 case → 失败（写了 advisor 没验证）
- ❌ Track C 6 case 都靠人工 walkthrough · advisor 没接管决策 → 失败（M6 charter 没实证）

---

## 触发性 redirect 条件（命中 → 修改 plan，不算 done）

| 条件 | 动作 |
|---|---|
| Track C 中 ≥ 2 case 同类 advisor 盲点 | harvest-003 提前到本 arc |
| 商业 CAE AI 预测分 ≥ 5（Siemens / ANSYS GA） | 战略复审 · 可能拉前 OSS readiness · V62 charter 内容变 |
| Advisor stack cross-cutting refactor（≥ 3 service 文件 schema 变） | 升级为完整 charter DEC · arc → V62 phase 0 |
| 任一 milestone 卡 ≥ 3 周 | 跳过 + retro · 不死等 |
| 用户工作焦点偏离 ≥ 1 周（demo / OSS / frontend） | 每 Tier 末 review 时确认是否 redirect |

---

## Tier 状态板（每 milestone 完成时打勾 + 填 commit hash）

### Tier 1 · 解锁性（并行 ok）

- [x] **M-A4** A4 face_orientation advisor LANDED · commit: `8183394` (2026-05-13 · DEC-V61-198-sub-A4)
  - 🔬 Research drafted 2026-05-13 · `.planning/patches/draft_a4_face_orientation_2026-05-13.md` (commit `615dacb`)
  - ✅ **LANDED 2026-05-13** · `ui/backend/services/geometry_ingest/face_orientation_advisor.py` + 9-test suite. V79 + V87 [QUESTIONABLE] → [VALIDATED] in both methodology + runtime corpora. Pure dict-consumer (mirrors A5 pattern); regression tests pin V79 38.000° + V87 21.979° ground-truth measurements
- [x] **M-V81** V81 inlet/outlet validator closed · commit: `7f11b16` (2026-05-13 · DEC-V61-198-sub-A5)
- [x] **M-DRIFT** Corpus drift-prevention hook · commit: `d53afbc` (2026-05-13)
- [x] **M-TRACK-2** Track C session 2 · case_011 · retro: `.planning/retrospectives/2026-05-13_track_c_advisor_e2e_session_2_case_011.md` (2026-05-13 · surfaced V85 + V86)
- [x] **M-CASE011-V2** case_011 v2 sub-session · V85 + V86 narrow-criterion fix verification · sub-DEC: `2026-05-13_v61_198_sub_case_011_v2_fix_verification.md` (2026-05-13 · V85+V86 → fix-verified · 1 case · surfaces V89 + V90 in dict-orchestration family · solver deferred to v3 sub-session per retention caveats)
- [x] **M-CASE011-V3** case_011 v3 sub-session · `cellZoneInside inside` heterogeneity (V92) + STL face-label loss (V94) + chtMultiRegionSimpleFoam e2e PASS · commit: `45d046f` · sub-DEC: `2026-05-14_v61_198_sub_case_011_v3_solver_e2e.md` (2026-05-14 · v5b mesh: hot 142% / cold 115% / solid 37% retention · cold retention 3% → 115% via `cellZoneInside inside` empirically validated · solid 37% kept at insidePoint walk (V92 surfaced — `inside` ray-cast fails for fuse_many internal-void STL topology) · chtMultiRegionSimpleFoam **PASS** at 200 SIMPLE iter, no FATAL, residuals reducing 3-5 orders, T fields equilibrated to ~360 K conduction midpoint · physics degenerate caveat per V94 — case_011 STL has no labeled inlet/outlet face-zones so substrate runs sealed-conduction box not the intended flow-through HX)
- [x] **M-APU-RESTORE** APU bay STL surgery [optional] · commit: `fabfd57` (2026-05-14 · **CLOSED NEGATIVE** · v33 mesh quality regressed (max_skew 6.875→7.966 · concave cells 95→147,036 · 1547×) · apu_intake patch STILL phantom (interior 89 cm³ / fill ratio 0.2% = <1 cell at sHM L3 · below patch-creation threshold) · V95 sedimented "watertightness necessary not sufficient" · V75 status stays `partial` (no fix-verified flip) · sub-DEC `2026-05-14_v61_198_sub_apu_restore_outlet_patch.md`)

### Tier 2 · advisor 加宽

- [ ] **M-A6** A6 hvac_adpi advisor LANDED · commit: `_____`
- [x] **M-A8** A8 shm_dict_validator advisor LANDED · commit: `18e0ee7` (2026-05-14 · sub-DEC `2026-05-14_v61_198_sub_a8_shm_dict_validator.md` · 9-test suite green · V52 typo-class + V86 orphan-class promotion gate met)
- [x] **M-A10** A10 thermo_polynomial_range_advisor LANDED · commit: `25eea7a` (2026-05-14 · sub-DEC `2026-05-14_v61_198_sub_a10_thermo_polynomial_range_advisor.md` · 14-test suite green · V41 channel-(b) closed [QUESTIONABLE]→[VALIDATED] · V93 codified · LANDED counter 7→8 ✓ Done dim MET)
- [x] **M-A6-HARDEN** A6 unit_detector hardening · commit: `83e2793` (2026-05-14 · sub-DEC `2026-05-14_v61_198_sub_a6_unit_detector_hardening.md` · spike-class · V96 max_bytes 64KB→1MB + V97 bbox cap 100m→1000m · both [VALIDATED] · pre-existing unit_detector module, not advisor #9)
- [ ] **M-A5** A5 unallocated 填充 · 候选 drafted · commit: `_____`
- [ ] **M-D6** D6 advisor promotion drafted → ready-to-land · commit: `_____`
- [x] **M-TRACK-3** Track C session 3 · case_004 NREL MRF · retro: `.planning/retrospectives/2026-05-13_track_c_advisor_e2e_session_3_case_004.md` (2026-05-13 · surfaced V88 compound row — MRF setup advisor coverage gap · 3rd cross-application of V83 across audit surfaces · A6/A8 2nd-evidence NOT produced by case_004 substrate · A9 mrf_setup_advisor candidate registered)
- [x] **M-TRACK-4** Track C session 4 · case_009 Sandia Flame D · retro: `.planning/retrospectives/2026-05-13_track_c_advisor_e2e_session_4_case_009.md` (2026-05-13 · surfaced V91 — V41 sediment-state correction (Tlow=200K patch incomplete: 13/53 species at 300K incl. N2/AR/CH3O · 14.7M warning lines in production logs · 08b mech-loader doesn't automate V41 patch) · 4th cross-application of V83 intent-cross-reference pattern (NEW: V-series sediment-status as verifiable artifact class) · A6/A8 2nd-evidence NOT produced by case_009 substrate (foreclosed by-construction: no HVAC, blockMesh-only no sHM) · A10 thermo_polynomial_range_advisor candidate registered · V41 status amendment [VALIDATED]→[QUESTIONABLE] deferred to separate commit per retro §6)

### Tier 3 · 收口 + V62

- [ ] **M-D9-D10** D9/D10 promotion · harvest-003 实质推进 · commit: `_____`
- [x] **M-XCLASS** 跨 numerics-class 第二案例 · CHT-multi-stream (chtMultiRegionSimpleFoam on case_011 v5b mesh) · 200 SIMPLE iter PASS · commit: `45d046f` · sub-DEC `2026-05-14_v61_198_sub_case_011_v3_solver_e2e.md` (degenerate physics caveat per V94 documented; procedural e2e demonstrated)
- [x] **M-TRACK-5** Track C session 5 · case_009 v1.5 reacting-low-Mach · retro: `.planning/retrospectives/2026-05-14_track_c_session_5_case_009_v1_5_reacting.md` (2026-05-14 · 3rd e2e numerics class confirmed · V41 channel-(b) closed · A10 thermo_polynomial_range_advisor promotion gate met by v1 + v1.5 dual-evidence)
- [x] **M-TRACK-6** Track C session 6 · case_003 CRM-HLS external-high-Re-BL · retro: `.planning/retrospectives/2026-05-14_track_c_session_6_case_003_crm_hls.md` (2026-05-14 · commit `bb4f34c` · 4th numerics class added to Track C coverage · V96+V97+V98 sediment all V83 6th cross-application class · A6 unit_detector cross-application surfaced silent fall-through window (V96 max_bytes truncation + V97 100m bbox cap) · A8 shm_dict_validator runtime error on hand-authored dicts (gap registered) · A2-v2/A4/A5/A7 module-load OK on case_003 substrate · solver 411 iter no divergence honest early-stop (killed by docker stop) · advisor land deferred per hard constraint)
- [x] **M-V100** V-series ≥ 100 marker · commit: `b1303d2` (2026-05-14 · V99 STL-driven symmetryPlane non-planar gap (A8 widening territory) + V100 A8 validate_shm_dict input-type-guard gap · 双 corpus sediment · Done dim 4 MET)
- [x] **M-RADAR-V2** capability radar v2 重画 · 左半轴 ≥ 7.2 验证 · commit: `483a144` (2026-05-14 · left half 6.40 → **7.10** ACTUAL · Done dim 5 **NOT MET · gap 0.1** · primary bottleneck = 网格生成 (6.5) per V85 connected-component cap + V92 multi-region fragility · secondary = 后处理 (7.0) no substrate work this arc · path to close: A8 widening per V99+V100 → mesh axis 6.5→7.0 → left half 7.10→7.20 ✓)
- [ ] **M-V62** V61-198 close DEC + V62 charter draft · commit: `_____`

---

## 进度计数器（每 session 末更新）

```
当前 Track C session 通过:    6 / 6 ✓   (case_010 + case_011 + case_004 + case_009 v1 + case_009 v1.5 + case_003 CRM-HLS · Track C Done dimension MET)
当前 LANDED advisor:          8 / 8 ✓   (A1, A2-v2, A3, A4, A5, A7, A8, A10 · LANDED Done dimension MET · A6 hvac_adpi still drafted awaiting 2nd HVAC case · A9 mrf_setup_advisor REGISTERED awaiting 2nd MRF case · unit_detector concrete advisor hardened by B16 (V96+V97 [VALIDATED]) but not promoted to LANDED counter since pre-existing module)
当前 V-series 行数:          100 / 100 ✓   (Done dim 4 MET 2026-05-14 · methodology + runtime 同步 · V88-V98 列见上版 · V99 STL-driven symmetryPlane non-planar gap (A8 widening territory) · V100 A8 validate_shm_dict input-type-guard gap (both case_003 session 6 retro § derived))
当前 e2e numerics class:     3 / 3 ✓   (compressible-buoyant-RANS APU bay 2026-05-12 F4b · CHT-multi-stream case_011 v5b chtMultiRegionSimpleFoam 200 SIMPLE iter 2026-05-14 (degenerate physics caveat per V94) · reacting-low-Mach case_009 v1.5 ignition 0 limit warnings + Tmax 1880→1968K monotone climb 2026-05-14 (Track C session 5 retro consolidated))
当前左半轴均分:             6.4 (v1) → 6.5 (v1.5 early-signal) → **7.10 (v2 ACTUAL · 2026-05-14)** / 7.2  ⚠ gap 0.1 · primary bottleneck 网格 (6.5) · close path = A8 widening per V99+V100 → mesh 6.5→7.0
当前右半轴均分:             8.7 (v1) → 9.0 (v1.5 early-signal) → **9.17 (v2 ACTUAL · 2026-05-14)** / 8.7 ✓ (+0.47 margin)
```

最后更新时间：`2026-05-14 (B18 + B19 batch land · M-RADAR-V2 [x] commit 483a144 · 左半轴 6.40 → **7.10 ACTUAL** · Done dim 5 NOT MET gap 0.1 · primary bottleneck 网格 6.5 (V85+V92 mesh-debug-loop barriers) · M-V100 [x] commit b1303d2 · V99+V100 双 corpus · Done dim 4 MET · **5/6 Done dimensions now MET**: Track C ≥6 ✓ · LANDED ≥8 ✓ · V-series ≥100 ✓ · e2e class ≥3 ✓ · 右半轴 ≥8.7 ✓ · last remaining gap: 左半轴 7.10→7.20 (gap 0.1 · A8 widening per V99+V100 是直接 close path))` · 更新人：`Claude Code Opus 4.7 session (main · B18/B19 reconcile)`

---

## 下一步建议（每次会话末由 main session 写）

> **2026-05-13 session 5 末** · M-A4 LANDED (DEC-V61-198-sub-A4-face-orientation-advisor)。Tier 1 advisor-land milestones now 4/4 complete (M-A4 + M-V81 + M-DRIFT + M-TRACK-2 all `[x]`); only optional M-APU-RESTORE remains in Tier 1. LANDED advisor counter 5 → 6 (A1, A2-v2, A3, A4, A5, A7). A4 ships as pure dict-consumer mirroring A5 — FreeCAD normal extraction stays caller-side, keeping the advisor side-effect-free and the 9-test suite running in 0.06s without a CAD-library runtime dep. V79 + V87 status flipped to [VALIDATED] in both methodology + runtime corpora; drift hook parity satisfied in the same commit.
>
> **下一会话候选**（M-A4 已完成 · 从清单移除）：
> 1. **M-A6** A6 hvac_adpi post-processor — Tier 2 advisor widen · case_012 V52 + 2nd HVAC-class sediment trigger
> 2. **M-A8** A8 shm_dict_validator — Tier 2 advisor widen · V86 (case_011 features-list orphaning) + V52 (case_012 typo) two-case promotion gate
> 3. **M-TRACK-3** Track C session 3 case_004 NREL Phase VI MRF — rotating-machinery numerics class probe
> 4. **case_011 v2 sub-session dispatch** — land V85 fix path + e2e numerics class +1 (CHT-multi-stream)
> 5. **M-APU-RESTORE** APU bay STL surgery — Tier 1 可选收口
>
> **推荐**：**M-TRACK-3 Track C session 3** — Tier 1 advisor stack is structurally complete; the next leverage point is **validating that the advisor stack actually drives Track C session decisions on a NEW numerics class** (rotating-machinery MRF). This moves the ARC-GOAL counters that matter most: Track C through-put (2→3), end-to-end numerics class (1→2 if solver runs). M-A6/M-A8 are Tier 2 widening that benefits from more cross-topology evidence first; running Track C session 3 generates that evidence.

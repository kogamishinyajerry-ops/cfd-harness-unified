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

- [ ] **M-A4** A4 face_orientation advisor LANDED · commit: `_____`
- [ ] **M-V81** V81 inlet/outlet validator closed · commit: `_____`
- [ ] **M-DRIFT** Corpus drift-prevention hook · commit: `_____`
- [ ] **M-TRACK-2** Track C session 2 · case_011 · retro: `_____`
- [ ] **M-APU-RESTORE** APU bay STL surgery [optional] · commit: `_____`

### Tier 2 · advisor 加宽

- [ ] **M-A6** A6 hvac_adpi advisor LANDED · commit: `_____`
- [ ] **M-A8** A8 shm_dict_validator advisor LANDED · commit: `_____`
- [ ] **M-A5** A5 unallocated 填充 · 候选 drafted · commit: `_____`
- [ ] **M-D6** D6 advisor promotion drafted → ready-to-land · commit: `_____`
- [ ] **M-TRACK-3** Track C session 3 · case_004 NREL MRF · retro: `_____`
- [ ] **M-TRACK-4** Track C session 4 · case_009 Sandia Flame D · retro: `_____`

### Tier 3 · 收口 + V62

- [ ] **M-D9-D10** D9/D10 promotion · harvest-003 实质推进 · commit: `_____`
- [ ] **M-XCLASS** 跨 numerics-class 第二案例 · retro: `_____`
- [ ] **M-TRACK-5** Track C session 5 · retro: `_____`
- [ ] **M-TRACK-6** Track C session 6 · retro: `_____`
- [ ] **M-V100** V-series ≥ 100 marker · commit: `_____`
- [ ] **M-RADAR-V2** capability radar v2 重画 · 左半轴 ≥ 7.2 验证 · commit: `_____`
- [ ] **M-V62** V61-198 close DEC + V62 charter draft · commit: `_____`

---

## 进度计数器（每 session 末更新）

```
当前 Track C session 通过:    1 / 6   (case_010 only)
当前 LANDED advisor:          4 / 8   (A1, A2-v2, A3, A7)
当前 V-series 行数:          84 / 100
当前 e2e numerics class:     1 / 3   (compressible-buoyant-RANS)
当前左半轴均分:             6.4 / 7.2
当前右半轴均分:             8.7 / 8.7 ✓
```

最后更新时间：`2026-05-13` · 更新人：`Claude Code Opus 4.7 session`

---

## 下一步建议（每次会话末由 main session 写）

> 2026-05-13 · 启动 M-DRIFT (spike-class · 30 LOC · 1 commit) + M-A4 research（spec drafting, code 留下一会话）。

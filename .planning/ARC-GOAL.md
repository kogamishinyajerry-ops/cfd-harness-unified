# ARC-GOAL · V62 Advisor Stack Closure Arc

**Plan SSOT**: [.planning/2026-05-14_v62_charter.md](2026-05-14_v62_charter.md)
**Predecessor**: [V61-198 advisor substrate arc · CLOSED 2026-05-14](ARC-GOAL-V61-198-CLOSED.md)
**Started**: 2026-05-14
**Mode**: milestone-driven (no calendar)
**Selected**: V62-A (Stack consolidation) · user-ratified 2026-05-14 from 3 candidates

> 读这个文件 90 秒能回答：「这个 arc 完了没？」「该不该开新 arc？」「下个 session 接什么？」

---

## North Star（一句话）

> **让 advisor stack 从 "8 个 LANDED 模块" 升级为 "1 个 LANDED stack" — plumbed into `/ai-review` + `/ai-diagnose` live routes · LLM 离线四问门控全通过 · 跨 ≥3 industrial case 的 stack-level e2e 验证 · D-class advisor ≥1 LANDED.**

---

## Done Definition（必须全部命中）

| # | 维度 | 起点 (2026-05-14) | Done 阈值 | 验证方式 |
|---|---|---|---|---|
| 1 | Advisor stack 路由聚合 | 0 (no stack-level route) | **2 routes LANDED · 每条调用 ≥3 advisor 模块** | `grep -E "advisor\|geometry_ingest" ui/backend/routes/ai_*.py` |
| 2 | 四问门控 cross-feature audit | partial (per-advisor LLM-offline OK) | **stack-level 4Q audit + sign-off** | `.planning/audits/v62_stack_4q_audit.md` exists + signed |
| 3 | Stack-level Track C e2e | 0 (V61-198 全 module-level) | **≥ 2 sessions · advisor stack 接管决策** | `ls .planning/retrospectives/*stack_track_c*.md \| wc -l` |
| 4 | D-class advisor LANDED | 0 D-class LANDED | **≥ 1 (D6 or D9 or D10) promoted** | `grep "D-class.*LANDED" .planning/cross_cuts/advisor_coverage_2026-05-09.md` |
| 5 | 雷达图右半轴 AI axis | 9.0 | **≥ 9.5** | `build_radar_v4.py` AI sub-value |
| 6 | 雷达图左半轴维持 | 7.15 (v3) | **≥ 7.20** (顺手关 V61-198 epsilon-margin) | `build_radar_v4.py` left half |

**任一未达成 = V62 不 close**，启动 root-cause retro。

---

## Done 条件**不算** Done 的反命题（防 stack-shipped-but-not-real）

- ❌ 路由 LANDED 但 4Q gate 没过（LLM 离线时报错） → 失败（违反 V130 advisor-not-driver）
- ❌ Stack 路由 plumbed 但 Track C session 仍靠 engineer 手写决策 → 失败（M6 charter 未操作化）
- ❌ D6 LANDED 但 stack 没消费它 → 失败（孤儿 advisor）

---

## 触发性 redirect 条件（命中 → 修改 plan，不算 Done）

| 条件 | 动作 |
|---|---|
| Stack assembly cross-cutting refactor ≥3 service 文件 schema 变 | 升级为完整 charter DEC |
| 任一 milestone 卡 ≥ 3 周 | 跳过 + retro · 不死等 |
| 商业 CAE AI ≥ 6 (Siemens GA / ANSYS GenAI ship) | 战略复审 · V62 可能拉前 OSS readiness |
| 用户工作焦点偏离 ≥1 周（demo/OSS/frontend pull） | 每 Tier 末 review redirect |
| Codex review round cap = 3 命中且仍有 P1 | 用户裁决（继续 / 接受 / 推 sub-DEC） |

---

## Tier 状态板（每 milestone 完成时打勾 + 填 commit hash）

### Tier 1 · 解锁性（M-STACK-ASSEMBLY 必须先）

- [x] **M-STACK-ASSEMBLY** advisor stack assembly layer · dispatch + composition pattern · commit: `b27c99f` (R0 LANDED) → `5b6c64c` (R1 fix 1 P1 + 2 P2) → `70e7da6` (R2 fix 1 P2 + 1 P3) → `4850683` (R3 fix 1 P1 · V133 round cap final · 2026-05-14 · sub-DEC `DEC-V62-A-sub-STACK-ASSEMBLY` Accepted · charter DEC `DEC-V62-A-charter` Accepted · 18-test suite · advisor_stack.py ~534 LOC · 4 detection paths × 8 advisors composable · 4Q gate verified inline (0 LLM imports, 0 file writes during dispatch) · workbench-env + [ui]-only-env both supported via try-real-first/fallback-placeholder dual path)
- [x] **M-ROUTE-AI-REVIEW** `/api/ai-review` route + V-series corpus retrieval + 4Q gate · commit: `5abe3f4` → `ebbe95f` (R1 fix 1 P1 + 3 P2) → `943e2cd` (R2 APPROVE) → `3d7c150` trailer · sub-DEC `DEC-V62-A-sub-ROUTE-AI-REVIEW` Accepted (2026-05-14 · ai_review.py 315 LOC · Pydantic v2 schemas · auto-discover parts_manifest+shm_dict+thermo_dict+thin_wall_inputs from case_dir · crash-isolated advisor dispatch · 25-test suite · 4Q gate inline PASS · Codex MANDATORY APPROVE at R2)
- [x] **M-ROUTE-AI-DIAGNOSE** `/api/ai-diagnose` route + V-series-similarity matching · commit: `fe89321` → `8f212f2` (R1) → `93342fa` (R2) → `f8b73b3` (R2-verbatim) → `ed58383` (closure record) · sub-DEC `DEC-V62-A-sub-M-ROUTE-AI-DIAGNOSE` Accepted (2026-05-14 · POST /api/ai-diagnose · top-K V-row matches by title-weighted Jaccard · Fix-suggestion extraction · optional advisor_stack cross-reference · 15-test suite · 4Q gate inline PASS · lexical-scan test verified 0 LLM imports · Codex MANDATORY APPROVE)
- [x] **M-4Q-AUDIT** 四问门控 stack-level cross-feature audit + LLM-offline acceptance test framework · commit: `ae4500e` (acceptance test) → `94d0221` (audit doc + sub-DEC) → this commit (ARC-GOAL reconcile) · sub-DEC `DEC-V62-A-sub-M-4Q-AUDIT` Accepted 2026-05-14 · `.planning/audits/v62_stack_4q_audit.md` 3×4 matrix signed by Opus 4.7 · `test_4q_gate_stack_acceptance.py` 4 acceptance tests Q1-Q4 PASS via `monkeypatch.delenv` LLM keys + sha256 case_dir invariant · 4/4 isolation + 72/72 full V62-A suite green · Tier 1 CLOSED · Done dim #2 MET ✓

### Tier 2 · advisor 加宽 + D-class literal closure + stack 验证

- [x] **M-D6-PROMOTE** D6 extra_body_in_fluid advisor LANDED (closes V61-198 §5.2 D-class waiver) · commit: `f6d5c72` (2026-05-14 · sub-DEC `DEC-V62-A-sub-D6` Accepted · extra_body_advisor.py ~290 LOC · 10-test suite · single-case land per A2 v1 placeholder precedent · V55 case_016 evidence · case_018 cyclone is forward-loaded 2nd-case pending · V55 status [QUESTIONABLE 2026-05-11] → [QUESTIONABLE 2026-05-14] single-case land · LANDED counter 8 → 9 · D-class literal counter 0 → 1 · V62-A Done dim #4 MET ✓)
- [x] **M-STACK-TRACK-1** Stack-level Track C session 1 · case_011 v5b stack run + engineer adjudication · retro: `.planning/retrospectives/2026-05-14_stack_track_c_session_1_case_011_v5b.md` (failure-recording session against case_011 v5b CHT-multi-stream substrate · path A POST /api/ai-review on :8001 + path B direct assemble_stack · 5 advisors python / 4 advisors http · 8 findings python / 7 findings http · 0 crash · adoption tally 1 adopted [thin_wall V10 D8] + 1 partial [unit_detector V20/V96] + 6 rejected [shm_dict_validator schema-form false positives on `name:` alias] = 25% python / 14% http BELOW 70% bar → 接管决策 NOT MET · 3 actionable blind spots surfaced: (1) shm_dict_validator literal-key-match vs native OpenFOAM `name:` alias resolution gap [V99-widening candidate]; (2) AIReviewRequest body missing `step_path`/`step_bbox` field so unit_detector route-stranded [echoes TRACK-2 gap]; (3) no stl_face_label_validator advisor in stack so V94 face-label loss class invisible to CHT-multi cases · 4Q gate inline PASS · LLM-offline verified via `env -i .venv/bin/python` re-run identical 5/8/0 · Stack capture rate against documented case_011 failure modes V85/V86/V89/V92/V94/D8 = 1/6 = 17% · session counts toward retro counter +1 but NOT toward Done-dim-#3 passing-session counter)
- [x] **M-STACK-TRACK-2** Stack-level Track C session 2 · new numerics class crossover · retro: `.planning/retrospectives/2026-05-14_stack_track_c_session_2_case_016.md` (case_016 m219 cavity DES acoustic · compressible-DES-acoustic vs case_011 steady-laminar-CHT-multi-stream · path A + path B both 200 / 3 findings identical / 0 crash · 3/3 partial-adoption = 100% ≥70% bar · 4Q gate offline confirmed env_keys_present=all false · single architectural gap surfaced: AIReviewRequest does not yet expose interface_bodies/interface_specs/step_path so D6/A2-v2/unit_detector are route-stranded · M-STACK-TRACK-1 case_011 v5b running in parallel and not yet landed at this commit's HEAD — counter advances solo +1)
- [x] **M-DRIFT-V2** stack-level corpus drift hook (V-series ↔ runtime corpus enforcement at /ai-review boundary) · commit: `b10494c` (feat) → `1cda573` (test 8/8 green) · sub-DEC `DEC-V62-A-sub-M-DRIFT-V2` Accepted (2026-05-14 · v_series_drift_guard.py 269 LOC · runtime check complements v1 commit-time check_corpus_sync.py · audit mode default preserves wire contract · ?drift_mode=strict opt-in · 58 combined tests green: 8 new + 50 baseline routes · 4Q gate AST-verified inline · Tier 2 first milestone LANDED)

### Tier 3 · charter close + V63

- [ ] **M-STACK-TRACK-3** Stack-level Track C session 3 · validation case · retro: `_____`
- [ ] **M-RADAR-V4** capability radar v4 · 右半轴 AI ≥ 9.5 + 左半轴 ≥ 7.20 · commit: `_____`
- [ ] **M-V63** V62 close DEC + V63 charter draft · commit: `_____`

---

## 进度计数器（每 session 末更新）

```
当前 stack-level 路由 LANDED:           **2 / 2 ✓**   (M-ROUTE-AI-REVIEW + M-ROUTE-AI-DIAGNOSE · Done dim #1 MET)
当前 4Q audit 状态:                    **MET ✓**   stack-level cross-feature audit signed-off (`.planning/audits/v62_stack_4q_audit.md` + `test_4q_gate_stack_acceptance.py` 4-test acceptance suite · sub-DEC `DEC-V62-A-sub-M-4Q-AUDIT` Accepted · Done dim #2 MET)
当前 stack-level Track C session:       2 / 3   (retros filed: M-STACK-TRACK-2 case_016 m219 + M-STACK-TRACK-1 case_011 v5b · ⚠️ **Done-dim-#3 passing-session subcounter: 1 / 2** — TRACK-2 100% adoption PASS; TRACK-1 25% adoption FAIL → 接管决策 NOT MET on case_011 CHT-multi class · TRACK-3 must PASS to reach Done-dim-#3 threshold OR TRACK-1 must be re-run after landing the 3 advisor enhancements TRACK-1 retro §8 recommends)
当前 D-class advisor LANDED:            **1 / 1 ✓**   (D6 extra_body_advisor LANDED · Done dim #4 MET)
当前 LANDED advisor 总数:              **9 / 8** ✓   (A1, A2-v2, A3, A4, A5, A7, A8, A10 + D6 extra_body_advisor)
当前右半轴 AI axis:                    9.0 / 9.5
当前左半轴均分:                        7.15 (v3) / 7.20
```

最后更新时间：`2026-05-14 (V62-A B24+B25 routes land · M-ROUTE-AI-REVIEW [x] 5abe3f4→943e2cd 3-round Codex chain APPROVE · M-ROUTE-AI-DIAGNOSE [x] fe89321→ed58383 chain APPROVE · stack-level 路由 LANDED 0/2 → 2/2 ✓ Done dim #1 MET · 50/50 route tests + 28/28 advisor tests = 78/78 passing · 4Q gate inline PASS each route · M-4Q-AUDIT cross-feature aggregated audit remaining · 2/6 Done dims now MET: Done #1 (stack routes 2/2) + Done #4 (D-class 1/1) · Tier 1 last milestone M-4Q-AUDIT unblocked) · B26 (Tier 1 CLOSE · M-4Q-AUDIT [x] · sub-DEC DEC-V62-A-sub-M-4Q-AUDIT Accepted · audit doc .planning/audits/v62_stack_4q_audit.md 3×4 matrix signed · test_4q_gate_stack_acceptance.py 4-test Q1-Q4 suite green via monkeypatch.delenv + sha256 case_dir invariant · 4/4 isolation + 72/72 V62-A bundle PASS · Done dim #2 partial → MET ✓ · 3/6 Done dims now MET: #1 + #2 + #4 · Tier 1 fully closed · Tier 2 stack-level Track C unblocked) · Tier 2 first milestone LANDED (M-DRIFT-V2) — DEC-V62-A-sub-M-DRIFT-V2 Accepted · v_series_drift_guard.py 269 LOC + 8 new tests · 58 combined tests green · audit mode default backward compatible) · B29 stack-level Track C session 2 LANDED (M-STACK-TRACK-2 [x] · case_016 m219 cavity DES acoustic · numerics crossover from case_011 steady-laminar-CHT-multi-stream → compressible-DES-acoustic on every signature axis · path A direct assemble_stack + path B POST /api/ai-review TestClient · 5+4 advisor invocations · 3 findings each path identical {A5×2 fail V81 boundary_emission, A8×1 warning V52/V86/V99/V100 geometry_orphan FW-H surface} · 0 crash · 100% partial-adoption ≥70% bar · 4Q gate offline confirmed env_keys_present all false · stack did NOT over-transfer case_011 multi-region structural patterns (A2-v2/A10 correctly silent-skip) · 1 architectural gap surfaced: AIReviewRequest does not expose interface_bodies/interface_specs/step_path leaving D6+A2-v2+unit_detector route-stranded for path B · counter 0/3 → 1/3 · TRACK-1 case_011 v5b parallel session not in origin/main at this HEAD so solo +1 advance) · B30 stack-level Track C session 1 LANDED (M-STACK-TRACK-1 [x] · case_011 v5b plate-fin compact-HX steady-laminar-CHT-multi-stream · path A HTTP POST /api/ai-review on :8001 + path B direct assemble_stack · 5 advisors python / 4 advisors http · 8 findings python / 7 findings http · path-divergence honestly recorded: HTTP path drops unit_detector [wire-schema gap] + adds v_series_drift_guard [intentional M-DRIFT-V2 route-layer addition] · adoption tally 1 adopted [thin_wall D8] + 1 partial [unit_detector] + 6 rejected [shm schema-form false-positives] · 25% python / 14% http BOTH below 70% bar → 接管决策 NOT MET on this case · counter 1/3 → 2/3 retros · Done-dim-#3 passing-session subcounter 1/2 [TRACK-2 PASS, TRACK-1 FAIL] · TRACK-3 must PASS or TRACK-1 re-run after advisor enhancements · 4Q gate inline PASS · `env -i` LLM-offline re-run identical 5/8/0 stack output verifying V130 thesis · 3 actionable blind spots surfaced for session 2/3 planning · session ran cleanly with 0 crash · failure recording is EXACTLY the data the 70% threshold was designed to surface)` · 更新人：`Claude Code Opus 4.7 session (main · B30 M-STACK-TRACK-1 land · case_011 v5b failure-recording)`

---

## 关键依赖图

```
M-STACK-ASSEMBLY  ─┬─→  M-ROUTE-AI-REVIEW   ──┐
                   │                          ├──→  M-4Q-AUDIT  ──→  M-STACK-TRACK-1
                   └─→  M-ROUTE-AI-DIAGNOSE  ─┘                       │
                                                                       ↓
                                                  M-D6-PROMOTE ────→  M-STACK-TRACK-2
                                                                       │
                                                  M-DRIFT-V2     ────→ │
                                                                       ↓
                                                              M-STACK-TRACK-3
                                                                       │
                                                                       ↓
                                                              M-RADAR-V4  ──→  M-V63
```

M-STACK-ASSEMBLY 是结构性 blocker · 路由 + audit 都 depend on it.

---

## 沿用 V61-198 §不变规则

- LLM offline 四问门控 (V130 thesis)
- advisor 不是 driver · 只 advise · engineer 最终决策
- 双 corpus drift-prevention hook (M-DRIFT v1) 保留 + V62 加 stack-level v2
- session-end Notion sync (仅 Accepted DECs · v2.3 round-1 rule)
- DEC scope-driven: ≥3 共享代码路径 / governance-rule-change → charter
- Codex 1-sync-trigger (auth/signing/security boundary · ≥3 round cap)

---

## v2.3 governance 合规

- V62-A 跨 routes/ai_*.py + services/advisor_stack.py (新建) ≥ 3 共享代码路径 → **首个 sub-DEC 落地时 elevate 到完整 charter DEC**
- Codex review: routes/ai_*.py 是 security boundary (operator-facing) → **每个 route PR 必走 Codex review (86gs gpt-5.4 xhigh baseline)** pre-merge
- Kogami opt-in (用户主动召唤)
- counter 纯遥测

---

## 下一步建议（每次会话末由 main session 写）

> **2026-05-14 V61-198 CLOSE + V62 charter Accepted** · V62-A North Star ratified.
> Tier 1 unblock starts with M-STACK-ASSEMBLY (advisor stack assembly layer · dispatch + composition).
>
> **下一会话候选**：
> 1. **M-STACK-ASSEMBLY** (Tier 1 critical · structural blocker for routes + audit · ~3-5 day sub-DEC)
> 2. **M-ROUTE-AI-REVIEW** (后 M-STACK-ASSEMBLY · security-boundary route work · Codex 必走)
> 3. **M-D6-PROMOTE** (parallel · D-class literal closure · independent of stack assembly)
>
> **推荐**：**M-STACK-ASSEMBLY** — 唯一结构性 blocker · 必须先 LAND 路由才能挂。

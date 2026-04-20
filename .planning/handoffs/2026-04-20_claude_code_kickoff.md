# Claude Code (Opus 4.7) 接棒 — `cfd-harness-unified` C-class infra 修复 → 全链路 V&V 验收

**Date**: 2026-04-20
**Handed off from**: Cowork agent (Opus 4.6, sandbox 权限受限)
**Handed to**: Claude Code (Opus 4.7, 本机 shell/git 全权限) + Codex (GPT-5.4 xhigh, 联合评审) on Kogami's Mac
**Repo**: `https://github.com/kogamishinyajerry-ops/cfd-harness-unified`
**Working tree**: `~/.../cfd-harness-unified`(用户自选路径)

---

## 0. 交棒原因

Cowork sandbox 不允许 `rm` `.git/*.lock` — 导致 git 无法继续;也没有 `gh`/`git push` 的凭证透传。代码与文档的 in-progress 修改已全部保留在 working tree,需要 Claude Code 接手:

1. 清 lock、commit 已完成的 C1+C2 改动
2. push + 开 PR + 合并 (或留待 review)
3. 同步到 Notion Decisions DB
4. 继续推进 C3 和 B-class gold-value 修复,直至 dashboard 真出现 ≥5 PASS

---

## 1. 当前仓库状态(截至交棒时)

### 1a. 已在 working tree 的 intentional 修改(未 commit)

| 文件 | 变更 | 测试 |
|---|---|---|
| `src/result_comparator.py` | **P-B C1**:新增 `CANONICAL_ALIASES` + `_lookup_with_alias` + 诊断型 summary | 20/20 ✅ |
| `tests/test_result_comparator.py` | +8 `TestFieldAliases` 用例 | " |
| `src/foam_agent_adapter.py` | **P-B C2**:新增 `ParameterPlumbingError` + `_parse_dict_scalar` + `_parse_g_magnitude` + `_verify_buoyant_case_plumbing` + `_verify_internal_channel_plumbing`;在 `_generate_natural_convection_cavity` / `_generate_steady_internal_channel` 尾部调用 | 56/56 ✅ |
| `tests/test_foam_agent_adapter.py` | +14 测试(解析器 + round-trip + tamper + 守卫) | " |
| `scripts/start-ui-dev.sh` | 端口自动 bump + health-check 等待(DEC-V61-003 尾声) | manual |
| `.gitignore` | 忽略 `Launch CFD UI.command`(本地 macOS 便利文件) | - |
| `docs/whitelist_audit.md` | **未 tracked** 新文件,342 行,审计 10 case × 3 bug 类别(A 元数据/B gold/C infra)+ C1/C2 落地追加 | - |

全套 regression: **158/158 ✅**(`pytest tests/test_foam_agent_adapter.py tests/test_result_comparator.py tests/test_task_runner.py tests/test_e2e_mock.py tests/test_correction_recorder.py tests/test_knowledge_db.py tests/test_auto_verifier`)

### 1b. 不要 commit 的 scratch/stale

- `.claude/` — local session state
- `.gitignore.patch.stale.*` — failed patch backup
- `ui/frontend/vite.config.sandbox.ts.stale.*` / `.timestamp-*.mjs` — Vite dev 残留
- `knowledge/corrections/` — 125 个运行期 YAML,不是源代码;是否入库另行决定,本 PR 外

### 1c. 已存在但空的分支

`feat/c-class-infra-fixes` — 本地已创建(`git branch --list`),但 HEAD 还在 `main`。需要你 checkout + commit。

---

## 2. 你的最终目标

**让 dashboard(`http://127.0.0.1:<backend>/api/cases` + Screen 4 Validation Report)的 10 个 golden cases 至少 5 个真 PASS**,且其中 ≥3 个是 k-omega SST 湍流 case(证明 RANS pipeline 工作正常),不是 laminar 甜区的伪通过。

达成路径:

- 先清 C 类 infra(C1 done,C2 done,C3 pending)→ 确保 solver 出数、comparator 能读
- 再修 B 类 gold-value(5 个 case)→ 通过 external gate 流程,DO NOT 直接改 `knowledge/whitelist.yaml` 里的 reference_values
- A 类元数据(4 个 case)在你判断为 **纯事实修正**(如 Re=100 cylinder 应 laminar,Rayleigh-Bénard 应切 buoyantBoussinesqSimpleFoam + laminar + 模型切换在 adapter 里完成)可自主改;涉及 tolerance/solver-family 的变更要走 gate
- 最后跑一遍 `POST /api/cases/:id/run` 全链路,验证至少 5 PASS

如果 5 PASS 达不到且你判断还需 external gate 才能进,停下来写一份 gate 请求书到 `.planning/external_gate_queue.md` 和 `.planning/gates/Q-new_whitelist_remediation.md`,然后 ping Kogami。

---

## 3. 启动动作(前 10 分钟做完)

```bash
cd ~/path/to/cfd-harness-unified

# 0. 清 cowork 留下的 git locks
rm -f .git/*.lock

# 1. 切到已创建的空分支
git checkout feat/c-class-infra-fixes
git status                              # 应显示 6 modified + docs/whitelist_audit.md untracked

# 2. 烟测 — 确认 regression 全绿
python -m pytest tests/test_foam_agent_adapter.py tests/test_result_comparator.py \
  tests/test_task_runner.py tests/test_e2e_mock.py tests/test_correction_recorder.py \
  tests/test_knowledge_db.py tests/test_auto_verifier -q
# 期望: 158 passed

# 3. 查阅交棒背景
cat .planning/handoffs/2026-04-20_claude_code_kickoff.md   # 本文件
cat docs/whitelist_audit.md                                # 根本方案
cat .planning/decisions/2026-04-20_phase_1_to_4_mvp.md     # DEC-V61-003 autonomy 边界
cat .planning/STATE.md                                     # 最新项目心跳
```

---

## 4. Commit / Push / PR / Notion 序列

### 4a. Commit C1+C2+audit 为一个原子 PR

```bash
git add .gitignore \
        scripts/start-ui-dev.sh \
        src/foam_agent_adapter.py \
        src/result_comparator.py \
        tests/test_foam_agent_adapter.py \
        tests/test_result_comparator.py \
        docs/whitelist_audit.md \
        .planning/handoffs/2026-04-20_claude_code_kickoff.md

git commit -m "$(cat <<'EOF'
fix(cfd-harness): whitelist audit + C1 comparator aliases + C2 parameter plumbing pre-run assertion

Dashboard 观察到 0 PASS / 2 HAZARD / 1 FAIL / 7 NO-RUN 后,按 docs/whitelist_audit.md §5.1
落地 autonomous-turf 的 C 类 infra 修复前两项:

C1 · src/result_comparator.py — 新增 CANONICAL_ALIASES 表 + _lookup_with_alias helper。
     canonical 键优先于 alias;companion-axis 查找透传 alias;failure summary 暴露
     tried aliases + available keys。消除 comparator_schema_mismatch ×14 的再发路径。
     TestFieldAliases 新增 8 条用例。

C2 · src/foam_agent_adapter.py — 新增 ParameterPlumbingError + 两个 static verifier
     (_verify_buoyant_case_plumbing / _verify_internal_channel_plumbing)。case 生成后
     读回 constant/physicalProperties + constant/g,重算 Ra_effective 与 Re_effective,
     与 task_spec 声明值 1% tolerance 比对,漂移即 raise。在 _generate_natural_convection_cavity
     与 _generate_steady_internal_channel 尾部装配。消除 parameter_plumbing_mismatch ×12
     的静默 fallback 路径。TestParameterPlumbingParsers + TestBuoyant/InternalChannelPlumbingVerification
     共 14 条用例。

whitelist_audit.md — 342 行,十案例三维 bug 分类 (A 元数据 / B gold 值 / C infra),per-case
     证据链 + cross-cutting 发现 + external-gate 包建议。v1.1 changelog 追加 C1/C2 落地追踪。

regression: 158/158 green(adapter + comparator + task_runner + e2e_mock + correction_recorder
+ knowledge_db + auto_verifier 全家桶)。

scripts/start-ui-dev.sh — 端口自动 bump + health-check 等待,避免 cowork 相邻会话端口
占用时 launcher 打开隔壁会话的 Vite 页。
.gitignore — ignore Launch CFD UI.command(per-user macOS 便利文件)。

Autonomy: DEC-V61-003 turf(src/ tests/ docs/ scripts/ .planning/).
External gate: 不在本 PR 内(B 类 gold 修正单独递交)。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"

git push -u origin feat/c-class-infra-fixes
```

### 4b. 开 PR(用 gh)

```bash
gh pr create --title "fix(cfd-harness): whitelist audit + C1 comparator aliases + C2 parameter plumbing (158 tests green)" --body "$(cat <<'EOF'
## Summary
- **C1 (ResultComparator alias 层)**: 新增 `CANONICAL_ALIASES` + `_lookup_with_alias`,消除 `comparator_schema_mismatch` ×14 再发路径。
- **C2 (Case-builder pre-run assertion)**: 新增 `ParameterPlumbingError` + 两个 round-trip verifier,消除 `parameter_plumbing_mismatch` ×12 静默 fallback 路径。
- **docs/whitelist_audit.md (342 行)**: 10 案例三维 bug 分类 + per-case 证据链 + external-gate 包建议。
- **launcher / .gitignore**: 端口冲突自动 bump;本地 macOS 便利文件脱敏。
- 回归: 158/158 green。

## Rationale
Dashboard screenshot 显示 0/10 PASS。audit 把问题拆成三类正交 bug (A 元数据 / B gold / C infra),并发现 **必须先修 C 类**,否则 B 类 gold 修正会在一个仍然 silently 出错的 pipeline 上再犯一次。本 PR 落地 autonomous-turf 可做的 C1+C2;C3 (sampleDict auto-gen) 为下一个 PR;B 类 gold-value 走 external gate。

## Test plan
- [x] `pytest tests/test_foam_agent_adapter.py -q` (56 passed)
- [x] `pytest tests/test_result_comparator.py -q` (20 passed)
- [x] Full regression 158/158 green
- [ ] 在 CI 中复跑
- [ ] Dashboard 跑一次 NC Cavity (Ra=1e10) + Plane Channel (Re_tau=180) 验证 verifier 不 false-positive

## Autonomy
DEC-V61-003 turf (`src/` `tests/` `docs/` `scripts/` `.planning/`)。不触 `knowledge/gold_standards/`,不改 `knowledge/whitelist.yaml` 的 reference_values。

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

### 4c. 同步到 Notion Decisions DB

Notion Decisions DB 地址(从 `.planning/decisions/*.md` frontmatter `notion_sync_status` 字段回推得到):

- DB root URL: `https://www.notion.so/Decisions-DB-<id>` (查 `.planning/decisions/2026-04-20_phase_1_to_4_mvp.md` 的 `notion_sync_status` 行)

写一条新 DEC 记录到 Decisions DB:

- **Decision ID**: `DEC-V61-004`
- **Title**: "Path B · C1+C2 infra fixes — comparator aliases + parameter plumbing assertion"
- **Scope**: "cfd-harness C-class infra 修复前两项;消除 comparator_schema_mismatch×14 + parameter_plumbing_mismatch×12 再发路径"
- **Status**: Landed
- **Autonomous governance**: true
- **Reversibility**: 单 PR,一次 `git revert -m 1 <merge-sha>` 即可完全回退
- **PR**: (刚开出的 URL)
- **Upstream**: `DEC-V61-003`

可以用 Notion MCP 的 `notion-create-pages` 工具;父页面是 Decisions DB 的 data source(从任一旧 DEC 页拿到 `collection://<id>`)。

然后本地也写一个 frontmatter 文件到 `.planning/decisions/2026-04-20_c_class_c1_c2.md`,`notion_sync_status: synced <timestamp> (<URL>)`。

### 4d. 更新 STATE.md

在 `.planning/STATE.md` 顶部 "今日工作" 区段追加一行:
```
2026-04-20 — C1+C2 landed on feat/c-class-infra-fixes (PR #<n>);dashboard 预期 HAZARD→PASS ≥ 3 case;DEC-V61-004 Notion synced。
```

---

## 5. 接下来的推进顺序

按本 PR merge 后继续:

### 5a. (autonomous turf) C3 sampleDict 自动生成 — Task #42

- 目标 case: NACA / Impinging Jet / LDC(三个有 companion-axis 采样的 case)
- 思路: case generator 读 gold `reference_values` 里的坐标(x_over_c / r_over_d / y),自动写 `system/sampleDict`,让 solver 实际在这些点采样
- 入口: `src/foam_agent_adapter.py` 的 `_generate_airfoil_flow`, `_generate_impinging_jet`, `_generate_lid_driven_cavity`
- 测试: 读回生成的 sampleDict,确认坐标匹配 gold

### 5b. (autonomous turf) A 类元数据修正 — 审计 §5.1 3 个子项

按 `docs/whitelist_audit.md §3` 的 per-case verdict:
- **Case 3 Circular Cylinder Wake** Re=100 → turbulence_model 从 `k-omega SST` 改 `laminar`(物理上 Re=100 远低于 turbulence onset)
- **Case 10 Rayleigh-Bénard** Ra=1e6 → turbulence_model 从 `k-omega SST` 改 `laminar`(Ra=1e6 是 transitional, laminar 更合理)

这是 `knowledge/whitelist.yaml` 的 metadata 字段修改,不碰 reference_values,autonomous 可做。**要在 PR 描述里明确说「not touching gold reference_values」**。

### 5c. (external gate 流程) B 类 gold-value remediation — `.planning/gates/Q-new_whitelist_remediation.md`

五个 case 的 gold 值经论文再核确认可疑(见 audit §5.2):
- Case 4 Turbulent Flat Plate: Re_x=25000 是 **laminar** 区,Spalding 公式不适用;需要 Blasius Cf=0.664/√Re_x
- Case 6 DHC Ra=1e10: Nu=30 偏低,论文 Ampofo & Karayiannis 2003 给 Nu~325
- Case 9 Impinging Jet: Nu r_over_d=0 给 25,Behnad et al. 2013 给 ~115
- Case 10 Rayleigh-Bénard: Nu=10.5 偏高,Chaivat 相关式 Nu≈0.229·Ra^0.269 → 7.2 at Ra=1e6
- Case 8 Plane Channel DNS: u+ @ y+=30 给 14.5,Moser 1999 DNS 在 Re_τ=180 给 ~13.5

这是 `knowledge/whitelist.yaml` + 可能 `knowledge/gold_standards/*.yaml` 的 gold 值改动,是 DEC-V61-003 的 **禁区**。写 gate 请求书 + ping Kogami 决策,**不要自动合并**。

### 5d. 跑一次全链路 validation 并截图

- `cd ui && npm install && npm run dev:full`(或 launcher)
- 对每个 case: `POST /api/cases/:id/run`(真 Docker,OpenFOAM 要在 Mac 端装好)
- Screen 4 截图 + Screen 5 dashboard 截图
- 写一份 `reports/post_c_class_acceptance/2026-04-<d>.md` 汇报真 PASS 数

---

## 6. Codex (GPT-5.4 xhigh) 联合开发协议

你可以在本机 shell 里直接 invoke Codex CLI(Kogami 已装)。推荐触发时机:

### 6a. 强制 Codex 评审(不能自己拍板)

- 任何 touches `knowledge/gold_standards/`(该目录是 external gate)
- 任何修改现有 `*.yaml` 的 `reference_values` 字段(哪怕只是 whitelist.yaml)
- 任何增加/删除 `tests/test_*.py` 里的 test case 逻辑(而不是新增)
- 任何 UI breaking change(API route rename, schema field 删除)

### 6b. 建议 Codex 二次确认(可以自己做,但借个眼睛)

- RANS 模型切换(k-omega SST ↔ k-epsilon ↔ laminar)对某个 case 的物理合理性
- 数学公式(Churchill-Chu、Blasius、Spalding、Dittus-Boelter 等)的适用范围边界
- OpenFOAM dict 关键字 / BC type 的版本兼容性(OpenFOAM-10)

### 6c. Codex invocation 惯用模式

```bash
# 案例 1:物理合理性质询
codex "Re=100 circular cylinder wake — 是否应该强制 laminar (而不是 k-omega SST)?
给出物理论据 + 典型实验证据 + OpenFOAM 配置建议。"

# 案例 2:代码片段 diff review
git diff HEAD~1 -- src/foam_agent_adapter.py | codex "Review this diff for correctness,
especially the Ra_effective back-computation."

# 案例 3:测试 coverage 争议
codex "下面是 _verify_buoyant_case_plumbing 的 6 条 test。还有什么 edge case 该覆盖?
<paste>"
```

返回建议写入 `.planning/codex_reports/<date>_<topic>.md` 以保证决策可追溯(DEC-V61-003 v6.1 治理契约要求 codex 介入留痕)。

---

## 7. 停车规则 — 何时必须暂停并 ping Kogami

不要 silently 跨过以下任一条:

1. 任何测试从 passing 变 failing 且 ≥ 10 分钟内解不了
2. 任何 `git revert` / `git reset --hard` 的必要性出现
3. 触到 `knowledge/gold_standards/` 或要改 `whitelist.yaml` 的 `reference_values`
4. dashboard 全链路重跑完仍 < 5 PASS,且你已用 C1+C2+C3+A 类修正拼尽所有 autonomous 子弹
5. OpenFOAM Docker 在用户的 Mac 上 blockMesh 就失败(不是你 controllable 的)
6. Codex 给出与你判断 **冲突** 的结论(需要 Kogami 仲裁)
7. PR 上有 reviewer(CI 或人)留了 request-changes 评论

在这些场景下,先把当前工作保存到分支、push、在 PR 或 `.planning/handoffs/<next>.md` 写明阻塞点,再停。

---

## 8. 治理上下文(你在 v6.1 治理体系里的位置)

- 你现在继承 DEC-V61-003 的 autonomy:`src/`, `tests/`, `docs/`, `scripts/`, `.planning/` 可自主改 + 自主 PR + 自主合并(regular merge commit,**不要** squash、**不要** rebase,留痕 > 聪明)
- `knowledge/gold_standards/` 是 **external gate**,要走 `.planning/external_gate_queue.md` 排队
- `knowledge/whitelist.yaml` 的 reference_values 字段同样受 gate 保护;**只有 metadata 字段**(geometry_type / flow_type / turbulence_model / solver / parameters)可自主改
- 所有 DEC 文件的 `autonomous_governance: true` + `claude_signoff: yes` 在你的改动不触红线时可以自签
- 大动作 (new Phase, breaking change) 要新开一个 `.planning/decisions/<date>_<topic>.md` DEC 文件

---

## 9. 成功判据 — 本次交棒可关闭的条件

依次达成:

- [ ] `feat/c-class-infra-fixes` PR 开出且 merge 到 main
- [ ] DEC-V61-004 写入 Notion Decisions DB + 本地 `.planning/decisions/`
- [ ] `.planning/STATE.md` 更新
- [ ] C3 sampleDict 自动生成 landed(第 2 个 PR)
- [ ] A 类元数据修正 landed(第 3 个 PR)
- [ ] dashboard 全链路跑一遍,≥ 5 case 真 PASS,≥ 3 case 是 k-omega SST 湍流 case
- [ ] 如达不到 ≥5 PASS,B 类 external gate 请求书已提交 + ping Kogami

**最终验收物**: 一张新的 dashboard 截图放到 `reports/post_c_class_acceptance/2026-04-<完成日>.png`,加一份 `reports/post_c_class_acceptance/2026-04-<完成日>.md` 总结。

---

## 附:关键路径速查

```
仓库根:              <user-selected>/cfd-harness-unified/
核心代码:            src/foam_agent_adapter.py, src/result_comparator.py, src/task_runner.py
Gold standard:       knowledge/whitelist.yaml (metadata OK, reference_values 禁区)
Gold gate 目录:      knowledge/gold_standards/ (全禁区)
历史 corrections:    knowledge/corrections/ (运行期 evidence,read-only)
测试:                tests/test_*.py (pyproject.toml 已配 pytest)
UI backend:          ui/backend/ (FastAPI :8000, 路由在 routes/*.py)
UI frontend:         ui/frontend/ (Vite :5173, Screen 1-5 在 src/pages/)
运行期启动器:        "Launch CFD UI.command" (本地,gitignored)
治理 DECs:           .planning/decisions/*.md
Notion 心跳:         .planning/STATE.md
外部 gate 队列:      .planning/external_gate_queue.md
交棒文件:            .planning/handoffs/2026-04-20_claude_code_kickoff.md (本文件)
```

---

**接棒完成后**,在本文件末尾追加:

```
接棒确认:Claude Code (Opus 4.7) @ <timestamp>
第一步:<实际执行动作>
已清 lock:yes/no
```

完事儿 —— 冲。

---

接棒确认: Claude Code (Opus 4.7) @ 2026-04-20T20:10
第一步: `rm -f .git/*.lock` (3 locks cleared: HEAD.lock, index.lock, ORIG_HEAD.lock) → `git checkout feat/c-class-infra-fixes` → 158/158 regression green
已清 lock: yes

Session outcome (see `.planning/handoffs/2026-04-20_claude_code_mid_session_stop.md` for full detail):
- PR #4 merged (b402f166) — C1+C2+audit — DEC-V61-004 Notion-synced
- PR #5 merged (d850cb2c) — A-class metadata — DEC-V61-005 Notion-synced
- Q-new gate filed (a8259c5) — B-class 5-case package subsumes Q-1 — STOP awaiting Kogami per-case decision
- C3 (§5a) deferred to dedicated design session — per-case sampling strategy needs thought
- §5d validation run awaiting Kogami call: mid-state now, or post-PR-6?

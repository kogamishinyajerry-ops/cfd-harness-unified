# VERSION_COMPATIBILITY_POLICY — 版本兼容硬宪法

**Status**: Active v1.0 (Promoted under SPEC_PROMOTION_GATE v1.1 · G-D Refinement Gate 2026-04-24 · Opus Option X ACCEPTED)
**Authority**: Opus 4.7 Pivot Post-Hoc Review §6 (HOLD + 串行 blocker) · GOV-1 Task
**Notion SSOT**: <https://www.notion.so/VERSION_COMPATIBILITY_POLICY-947fa51765734d3cb84f626c2411e949>
**Gate**: Promoted per `docs/specs/SPEC_PROMOTION_GATE.md` §2 (6 通用门 AND §3 spec-specific blocker)
**Scope**: All Knowledge Plane artefacts (CaseProfile, GoldStandard, SimulationObject, ExecutionArtifacts, audit manifests) + all cross-plane contracts in SYSTEM_ARCHITECTURE v1.0 §4.

---

## §0 目的

防止 OpenFOAM / knowledge schema / extractor 版本漂移造成静默数值错误
或集成崩溃。本文件为 **Constraint 级硬约束**：违反需 Decisions DB +
Opus Gate 联合放行，autonomous governance 不足以豁免。

METRICS_AND_TRUST_GATES v0.1 的核心 blocker 是 "tolerance 必须来自
`CaseProfile.tolerance_policy`"——本文件是 `CaseProfile` 四元组元数据的
权威定义者。没有 v1.0 Active，P1-T1 (MetricsRegistry) 的 tolerance 字段
就没有上游来源。

## §1 当前 Baseline (Pinned · 2026-04-24)

所有 repo 资产默认绑到以下 baseline。任何新增 artefact 都**必须**声明
版本元数据；**对四元组字段** (§2) 缺失默认继承 baseline，偏离需显式声明。
但 Knowledge schema_version 是**独立于四元组**的 Knowledge Plane 内部版本
号，不共享 4-tuple 继承语义 (Codex R1 #2 fix · 2026-04-24)。

| 轴 | 当前 Baseline | 锚点 |
|---|---|---|
| Solver | `"openfoam"` (family) + `"v2312"` (version) | Foam-Agent ship 的 docker image (`cfd-openfoam:v2312`) |
| Knowledge Schema (live, heterogeneous) | **Structured files (10 files with `schema_version: 2`)** — e.g. `lid_driven_cavity_benchmark.yaml`, `cylinder_crossflow.yaml`, `turbulent_flat_plate.yaml`, `axisymmetric_impinging_jet.yaml`, `duct_flow.yaml`, etc.; **Legacy files (5 multi-document YAMLs with NO top-level `schema_version`)** — e.g. `lid_driven_cavity.yaml`, `backward_facing_step.yaml`, etc. (accepted by `LegacyObservable` branch of schema); **audit manifest: `SCHEMA_VERSION = 1` (integer emitted in `src/audit_package/manifest.py`, unrelated to gold YAML schema_version)** | `knowledge/schemas/gold_standard_schema.json` `$defs.LegacyGoldStandardFile` + `$defs.StructuredGoldStandardFile` (oneOf); `src/audit_package/manifest.py:43` |
| Extractor Suite | `extractor_semver: "1.0.0"` (nominal) | `src/result_comparator.py` + `src/*_extractor.py` 集合；semver 尚未 embedded in code 中 (P1-T1 deliverable) |
| Harness Core | `harness_semver: "1.0.0"` (planned) | `pyproject.toml` `[project].version` (not yet set) |

**Tombstone**: baseline 更新时必须在本 §1 追加一行 `## §1.X` 子节，**不
得直接覆盖**，以保持历史可审计。

## §2 元数据四元组（强制 · MANDATORY）

每个 CaseProfile / GoldStandard / SimulationObject / ExecutionArtifacts
的 frontmatter / schema 根对象**必须**携带以下四元组字段：

### §2.1 字段定义

**Codex R1 #1 fix (2026-04-24)**: `solver_version` 不是 PEP-440 / semver.org
格式。`packaging.version.Version("openfoam/v2312")` 抛 `InvalidVersion`。
本 spec 使用**定制结构化字符串** + **domain-specific parser**（P1-T1 deliverable），不走 `packaging` / `semver` 库。

| Field | Type | 解释 | 示例 |
|---|---|---|---|
| `solver_version` | **structured string** `<family>/<version>` | 产生该 artefact 的 solver family + version。解析需 custom parser (P1-T1) | `"openfoam/v2312"` |
| `case_compatibility` | **structured range** `<family>/<min>` 到 `<family>/<max>` | 该 case 契约兼容的 solver 版本区间。跨 family 视为 HARD_FAIL，无法比较 | `">=openfoam/v2312,<openfoam/v2500"` |
| `extractor_compatibility` | **semver range** (PEP-440 / semver.org parseable) | 该 case 契约兼容的 extractor semver range | `">=1.0.0,<2.0.0"` |
| `schema_version` | integer（monotonic） | Knowledge schema 的 breaking-change 序号 | `1` 或 `2` |

语义约束：
- `solver_version` 是**精确值**（跑出来的就是这个版本）；`case_compatibility`
  是**范围**（该 case 允许跨多少版本仍被认为等价）
- `extractor_compatibility` 覆盖 comparator / gate / sampler 的总和行为；
  任何 extractor 模块改变可能影响 observable 值的逻辑 → bump minor
- `schema_version` 是 integer 而不是 semver，因为 Knowledge Plane 的
  schema 破坏性变更需要**全量迁移**。每个 breaking 变更 += 1；兼容补充
  不变更
- `schema_semver` 已删除（Codex R1 open comment · 2026-04-24）——既然 optional
  又无强制语义，留着只会给读者造成"两套 version"的混淆。整数 schema_version
  是唯一权威

### §2.2 字段出处映射

| 对象 | frontmatter 字段位置 | Owner Plane |
|---|---|---|
| `CaseProfile` (intake.yaml) | 顶层 `version_metadata:` 块 | Knowledge |
| `GoldStandard` (`knowledge/gold_standards/*.yaml`) | 顶层 `case_info.version_metadata:` 块 | Knowledge |
| `SimulationObject` | 顶层 `version_metadata:` 块 | Knowledge |
| `ExecutionArtifacts` (runs/*.json manifest) | 根对象 `version_metadata:` 键 | Execution |
| `audit_package/manifest.py` 生成的 manifest | `schema_version` + `solver_version` (其余继承) | Control |
| `knowledge/attestor_thresholds.yaml` 等 config | `schema_version: <int>` 独立 | Knowledge |

### §2.3 兼容 shim（过渡期 · 2026-04-24 → P1-T1 closeout）

**Codex R1 #2 + R2 #1 fix (2026-04-24)**: 原 "2026-06-30 截止" 过于激进
(2 个月 buffer 且依赖未实现 lint-knowledge.py)。改为 P1-T1 closeout 为
截止点（P1-T1 会实现 lint-knowledge.py 作为 deliverable），并区分
schema_version 与四元组两种状态。

历史 artefact 不带完整四元组。当前 gold YAML 状态已是**混合**：
- **structured files (10 个，有 top-level `schema_version: 2`)**：例如
  `lid_driven_cavity_benchmark.yaml`, `cylinder_crossflow.yaml`,
  `turbulent_flat_plate.yaml`, `axisymmetric_impinging_jet.yaml`,
  `duct_flow.yaml` 等 — 走 schema 的 `StructuredGoldStandardFile` 分支
- **legacy files (5 个多文档 YAML，无 top-level `schema_version`)**：例如
  `lid_driven_cavity.yaml`, `backward_facing_step.yaml` 等 — 走 schema 的
  `LegacyGoldStandardFile` / `LegacyObservable` 分支；validator (`oneOf`)
  两条路径都接受

过渡规则：

1. **schema_version 不继承 baseline** — 整数值就是写进 YAML 的那个值；
   validator (`scripts/validate_gold_standards.py`) 已经按 oneOf 接受
   legacy + structured 两种 payload 形状
2. **四元组字段缺失时才隐式继承**：`solver_version`/`case_compatibility`/
   `extractor_compatibility` 缺失 → 视为 §1 baseline
3. **首次 touch 必须补全**：任何 PR 修改一个 artefact 的数值内容
   **必须**同步补齐其四元组；纯格式 / 注释改动豁免
4. **P1-T1 closeout 截止**：届时 P1-T1 的 `lint-knowledge.py` deliverable
   上线，所有 gold YAML 必须显式声明四元组；否则 CI 失败。具体日期挂到
   P1 closeout retro（不 hard-code 到本 spec）

## §3 Drift 防护决策树

**Codex R1 #3 fix (2026-04-24)**: 本 §3 的决策树是 **DESIGN_ONLY** 的逻辑
规范。实际强制执行（pre-run HARD_FAIL、version_metadata propagation、
ExecutionResult schema extension）是 **P1-T1 MetricsRegistry + TaskRunner
pre-check hook 的 deliverable**，不是本 spec 提供。在 P1-T1 落地前：
- TaskRunner 不拒绝 drift
- ExecutionResult 无 `version_metadata` 字段
- 审计靠人工 + `audit_package/manifest.py` 的 `schema_version` 单字段
  （不是四元组）

当 ExecutionArtifacts 的 `solver_version` 与 GoldStandard 的
`case_compatibility` 比较时（**设计意图，待强制**）：

```
                compare(execution.solver_version, gold.case_compatibility)
                                |
                    +-----------+-----------+
                    | in-range               | out-of-range
                    v                        v
         +----------+----------+       +-----+-----+
         | patch-only drift?    |       | MAJOR mismatch?
         +----------+----------+       +-----+-----+
                    |                        |
              YES   v   NO                   v
         +----------+----+            +------+-------+
         | PASS · log only |          | MINOR mismatch?
         +----------------+           +------+-------+
                                            | YES
                                            v
                       +-----------+  +--------+--------+
                       | HARD FAIL  |  | WARN + audit   |
                       +-----------+   +----------------+
                         (no run)        (run allowed,
                                          verdict=WARN
                                          logged to Provenance)
```

规则（伪代码 · **尚未在 repo 中实现**）：

```python
# See P1-T1 TaskRunner pre-check hook (pending).
# check_drift: (execution.version_metadata, gold.case_compatibility) -> Verdict
# Uses custom domain-specific parser (not packaging.Version) because
# solver_version strings like "openfoam/v2312" are not PEP-440 parseable.
def check_drift(execution_solver: str, gold_range: str) -> Verdict:
    # Placeholder: parse <family>/<version> strings, compare within-family.
    # Cross-family defaults HARD_FAIL per §5.1.
    if parse_within_range(execution_solver, gold_range):
        return Verdict.PASS
    delta = family_aware_version_distance(execution_solver, gold_range)
    if delta.major > 0 or delta.family_differs:
        return Verdict.HARD_FAIL   # pre-run block (P1-T1)
    if delta.minor > 0:
        return Verdict.WARN         # allow run, flag
    return Verdict.PASS             # patch-only drift transparent
```

对 `extractor_compatibility` / `schema_version` 同样应用三态决策（所有
decisions design-only 至 P1-T1）；`schema_version` 是 integer，所以 "major"
= 数字不同，HARD FAIL。

**Drift verdict 与 TrustGate 合流（aspirational）**：先过 VERSION drift →
初始 verdict；再过 tolerance check → max-pessimistic 合并。具体规则：
  - drift=HARD_FAIL → TrustGate immediate FAIL（tolerance 不再评估）
  - drift=WARN + tolerance=PASS → 最终 WARN
  - drift=WARN + tolerance=WARN/FAIL → 最终 max(WARN, tolerance verdict)
  - drift=PASS → 完全由 tolerance verdict 决定

## §4 跨层契约影响 (aspirational · P1-T1 + P2 deliverables)

**Codex R1 #3 fix (2026-04-24)**: 本 §4 的契约目前**没有在 repo 中强制**。
以下是**目标规范**，依赖各 Plane 的 spec Active + 代码实现：
- TrustGate 合流行为 → METRICS_AND_TRUST_GATES v1.0 + P1-T1 TaskRunner pre-check
- `ExecutionResult.version_metadata` 字段 → P2 EXECUTOR_ABSTRACTION 扩字段
- Audit manifest 四元组 → `src/audit_package/manifest.py` 补 writer (P1-T1)

- **TrustGate (METRICS_AND_TRUST_GATES)**: TrustGate 决策三态与本文件
  drift 决策三态**合流**（见 §3 末 aspirational 条款）
- **Executor (EXECUTOR_ABSTRACTION)**: `ExecutorMode.run()` 返回的
  `ExecutionArtifacts` **将在 P2** 在 top-level 携带
  `version_metadata.solver_version`；缺失 = HARD FAIL。**今天** `ExecutionResult`
  （`src/models.py:89`）没有此字段，`TaskRunner.run_task()`
  （`src/task_runner.py:107`）也不做前置 version check
- **Attribution**: 归因报告**将**引用当次 run 的 solver_version 字符串
  作为 context（P1-T1 调度实现时加）
- **AuditPackage**: manifest 构建时**将**从 ExecutionArtifacts 提升四元组到
  package level（P1-T1 扩 writer）；**今天** `manifest.py:558` 只 emit
  top-level `schema_version` + `run.solver` 两字段

## §5 未来扩展

### §5.1 跨 solver（P5+）

**Codex R1 open comment fix (2026-04-24)**: `solver_family` 改为 **open
registry** (类似 `risk_flag_registry.yaml`)，不用 closed enum。

接入其他 solver（SU2 / Code_Saturne / OpenFOAM.com 分支 / Nektar++ / Ansys
Fluent / ...）走 **ExecutorMode plugin 协议** + `CaseProfile.solver_family`
字段扩展：

- `solver_family`: string 引用 `knowledge/schemas/solver_family_registry.yaml`
  里的已登记 family_id（P5 activation 前此 registry 文件 optional，只列
  `openfoam_esi` baseline；扩展通过 append 新条目不 bump 整体 version）
- `solver_version` 维持 structured string (见 §2.1)，跨 family 比较
  **HARD FAIL** 默认（family 不同 = 数值不可比）
- 跨 solver 对比**不比较数值**，只能通过 `BenchmarkManifest` 层面的
  `evaluation_protocol` 做 relative benchmark
- **跨 ESI/.com 分支内数值比较特殊情况**：OpenFOAM ESI v2312 vs .com v10
  的 icoFoam 虽 family 不同，但 solver code 共享度高，某些 case 数值可
  apples-to-apples。这类特殊 pair 需在 `solver_family_registry.yaml` 登记
  `cross_family_numeric_compatible_pairs`，走 WARN 而不是 HARD_FAIL。
  P5 activation 前不启用此 override

### §5.2 Knowledge schema 增演

每次 `knowledge/schemas/*.json` breaking change：
1. `schema_version += 1` (integer — 唯一权威版本标识, per §2.1)
2. 所有 `gold_standards/*.yaml` 必须同步迁移或显式声明 legacy（通过
   schema 的 `oneOf(LegacyGoldStandardFile, StructuredGoldStandardFile)`
   分支兼容共存）
3. 迁移脚本 `scripts/migrate_knowledge_schema_vN_to_vM.py` 作为 DEC 附件落地

### §5.3 Deprecation 窗口

任何 field rename / 移除 **必须**先进入 `deprecated_fields` 列表（存
`docs/specs/VERSION_COMPATIBILITY_POLICY_deprecations.yaml`；G-6 KNOWLEDGE
v1.0 时创建），至少保留 **一个完整 minor cycle** + 2 周 grace。

## §6 审计

**Codex R1 open comment fix (2026-04-24)**: §6.1 和 §6.2 的机制目前
**未实现**，标为 planned。先手工 recommended，P1-T1 起 enforce。

### §6.1 Session handoff fingerprint (recommended · enforcement P1-T1)

每个 session handoff **推荐**在 `.planning/STATE.md` 或 session summary 附
`version_fingerprint` 块 (P1-T1 起由 pre-commit hook 强制)：

```yaml
version_fingerprint:
  timestamp: "2026-04-24T22:50Z"
  harness_semver: "1.0.0"
  knowledge_schema_version: 1
  extractor_semver: "1.0.0"
  solver_default: "openfoam/v2312"
  git_sha: "4fd9215"
```

### §6.2 季度 Drift Audit (planned · enforcement P1-T1)

**Codex R2 minor comment (2026-04-24)**: 本节与 §6.1 一样标 **recommended · 
enforcement 尚未实现**, 避免读者误认为 quarterly audit 已强制。

每季度（Q1/Q2/Q3/Q4）**建议**运行 `scripts/audit_version_drift.py`（未实现；
P1 closeout 前上线）对 Provenance 全量扫描：
- 找出所有 `solver_version` 分布，非 baseline 的每条都要有 audit_concern 引用
- 找出所有 `schema_version` 不等于当前的 YAML，每条必须已 migrate 或带 legacy exception

## §7 违反与豁免

### §7.1 违反处理

| 级别 | 触发 | 处置 |
|---|---|---|
| CRITICAL | 四元组缺失且不继承 baseline（新增 artefact 不声明版本） | pre-commit / CI 直接拒绝 merge |
| HIGH | Drift major mismatch 但未走 Decision | revert commit；开 incident retro |
| MEDIUM | Drift minor mismatch 未标 WARN in Provenance | 补 Provenance entry；不回退代码 |
| LOW | 历史 artefact 未补齐四元组（过渡窗口内） | 提醒，不阻塞 |

### §7.2 豁免路径

- **小型修复** (≤20 LOC 且不改 artefact 版本语义) — 按 Pivot Charter
  §4.3a (b) 允许行为豁免本文件
- **跨 solver 实验性接入** — 开独立 DEC-PIVOT-P5-* 并在 `CaseProfile.solver_family`
  显式标记 `experimental: true`
- **Knowledge schema bump 本身** — schema_version += 1 的 DEC 不受本
  文件 §3 drift check 约束（因为它就是变更 source of truth）

## §8 不做清单

**G-D v1.1 (SPEC_PROMOTION_GATE §7)**: 每条 "不做" 必须显式标注类别
(Cat 1/2/3) 并满足对应 evidence 要求。详见 §9.1 evidence table。

### §8.1 [Cat 2] 不定义各 plane 内部的对象 schema

Delegated to `KNOWLEDGE_OBJECT_MODEL.md` §1 Object Definitions.
See §9.1 entry for accepting clause evidence.

### §8.2 [Cat 2] 不定义 tolerance 的数值

Delegated to `METRICS_AND_TRUST_GATES.md` §4 Tolerance Policy.
See §9.1 entry for accepting clause evidence.

### §8.3 [Cat 1] 不替代 SYSTEM_ARCHITECTURE 的 plane 划分

Capability-negated via `ADR-001` `.importlinter` contract
`execution-never-imports-evaluation` + `evaluation-never-imports-execution`
+ `knowledge-no-reverse-import` + `models-stays-pure`. CI step
"Four-plane import contract (ADR-001)" in `.github/workflows/ci.yml`
fails if any VCP-claimed plane cross would actually occur.

### §8.4 [Cat 2] 不约束 `ui/**` 或 `scripts/**` 的版本策略

Delegated to `docs/scope/UI_SCRIPTS_BOUNDARY.md` §1 + §2.
See §9.1 entry for accepting clause evidence.

### §8.5 [Cat 3] 不要求跨 solver 的 apples-to-apples 数值比较

Policy commitment recorded at `docs/governance/POLICY_COMMITMENTS_LEDGER.md`
entry `POL-VCP-001` + Decisions DB `DEC-POLICY-VCP-001` (pending
CFDJerry signature). Rationale: cross-family numerical differences =
solver-implementation-difference, not physics-disagreement. ESI/.com
internal-compatible pairs require explicit registry (see §5.1).

## §9 Promotion Gate 证据

per SPEC_PROMOTION_GATE.md v1.1 §2:

| Gate | Status | Evidence |
|---|---|---|
| G-A (Deliverables ≥80% merge) | ✅ | 本 spec 文件; `src.audit_package.manifest` + `src.convergence_attestor` 已使用 `schema_version` |
| G-B (冒烟案例) | ⚠️ | legacy gold_standards/*.yaml 走 LegacyObservable 分支 pass; structured files 显式 `schema_version: 2`；4-tuple 未强制（P1-T1 deliverable） |
| G-C (上下游 cross-ref) | ✅ | §4 显式引用 METRICS_AND_TRUST_GATES / EXECUTOR_ABSTRACTION / KNOWLEDGE_OBJECT_MODEL |
| G-D v1.1 (Cat 1/2/3 evidence) | ✅ | 详见 §9.1 scope_delegations 表 + §9.2 Cat 1 evidence + §9.3 Cat 3 ledger ref |
| G-E (DEC record) | ⏳ | `DEC-PIVOT-P1-GOV-1` 待 CFDJerry 签 (G-1 完成时同步登记) |
| G-F (Codex 独立审查无 HIGH) | ⏳ | R1+R2 CHANGES_REQUIRED → R3 pending on this commit (Option X accept clause landing + §8 categorization) |

### §9.1 Cat 2 · Scope Delegations 表

per SPEC_PROMOTION_GATE.md v1.1 §7.2 (3 条全部满足):

```yaml
scope_delegations:
  - item: "Plane 内部对象 schema"
    category: 2
    source_section: "§8.1"
    delegated_to_spec: KNOWLEDGE_OBJECT_MODEL
    delegated_to_section: "§1 Object Definitions"
    accepting_clause_path: "docs/specs/KNOWLEDGE_OBJECT_MODEL.md §1"
    accepting_clause_text: "accepts delegation from VERSION_COMPATIBILITY_POLICY §8.1 · Plane 内部 object schema"
    co_landed_with: "this VCP v1.0 promote commit (same PR per §7.2 item 3)"

  - item: "tolerance 数值"
    category: 2
    source_section: "§8.2"
    delegated_to_spec: METRICS_AND_TRUST_GATES
    delegated_to_section: "§4 Tolerance Policy"
    accepting_clause_path: "docs/specs/METRICS_AND_TRUST_GATES.md §4"
    accepting_clause_text: "accepts delegation from VERSION_COMPATIBILITY_POLICY §8.2 · tolerance values"
    co_landed_with: "this VCP v1.0 promote commit (same PR per §7.2 item 3)"

  - item: "ui/** and scripts/** 版本策略"
    category: 2
    source_section: "§8.4"
    delegated_to_spec: UI_SCRIPTS_BOUNDARY (scope doc, not a canonical spec)
    delegated_to_section: "§1 ui/** + §2 scripts/**"
    accepting_clause_path: "docs/scope/UI_SCRIPTS_BOUNDARY.md §0"
    accepting_clause_text: "accepts delegation from VERSION_COMPATIBILITY_POLICY §8.4 · ui/** and scripts/** 的版本策略"
    co_landed_with: "this VCP v1.0 promote commit (same PR per §7.2 item 3)"
```

### §9.2 Cat 1 · Capability Negation evidence

| §8 条目 | CI 强制机制 | 失败条件 |
|---|---|---|
| §8.3 不替代 SYSTEM_ARCHITECTURE plane 划分 | `.importlinter` 4 forbidden contracts (ADR-001); `.github/workflows/ci.yml` step "Four-plane import contract (ADR-001)" | 任何 VCP 声称的 plane cross import 真实发生时 `lint-imports` non-zero exit |

### §9.3 Cat 3 · Policy Commitment evidence

| §8 条目 | Ledger entry | Decision | Review cadence |
|---|---|---|---|
| §8.5 不要求跨 solver apples-to-apples | `docs/governance/POLICY_COMMITMENTS_LEDGER.md` entry `POL-VCP-001` | `DEC-POLICY-VCP-001` (pending CFDJerry sign) | quarterly; next due 2026-07-24 |

当 G-E + G-F 完成，本文件 status 从 "Active v1.0 (Cat 2 accepting clauses
landed, Cat 3 decision pending)" 正式 CLEAR 到 "Active v1.0 · all
Promotion Gate 通过"。

## §10 修订记录

| 版本 | 日期 | 修订者 | 说明 |
|---|---|---|---|
| v0.1 | 2026-04-22 | 首席架构官 (Notion) | Initial Draft; 四元组骨架 + drift 树概念 |
| v1.0 | 2026-04-24 | Claude Code + Opus 4.7 Post-Hoc Gate | GOV-1 promote attempt; 固化四元组字段、drift 决策树、过渡 shim、baseline pin、Promotion Gate 证据。Commit acb1993 |
| v1.0-rc2 | 2026-04-24 | Claude Code + Codex R1 CHANGES_REQUIRED response | 4 BLOCKING 修复 (solver_version parser custom / baseline heterogeneous / §3§4 aspirational 标注 / G-D scope narrowed). 3 open comment fix (schema_semver 删除 / solver_family open registry / §6 planned 标注). See §10.1. Commit 41fed9d. |
| v1.0 | 2026-04-24 | Opus 4.7 Gate Option X ACCEPTED + Claude Code + (pending) Codex R3 | Promoted under SPEC_PROMOTION_GATE v1.1 per G-D Refinement Gate 2026-04-24. §8 each "不做" item explicitly categorized (Cat 1/2/3 per G-D v1.1); §9.1 scope_delegations table (Cat 2) added with accepting clauses co-landed in consumer specs (KNOWLEDGE_OBJECT_MODEL §1, METRICS_AND_TRUST_GATES §4, UI_SCRIPTS_BOUNDARY §0); §9.2 Cat 1 evidence via ADR-001 importlinter; §9.3 Cat 3 evidence via POLICY_COMMITMENTS_LEDGER POL-VCP-001 + DEC-POLICY-VCP-001. R2 #1 corpus accuracy fix: 10 structured files with top-level schema_version=2 + 5 legacy multi-doc YAMLs with NO top-level schema_version (走 LegacyObservable 分支). R2 #2 schema_semver residual cleanup in §5.2. R2 #3 G-D gate met per v1.1 differentiated evidence. See §10.2. |

### §10.1 Codex R1 CHANGES_REQUIRED 响应细则 (v1.0 → v1.0-rc2 · 2026-04-24)

Review log: `reports/codex_tool_reports/gov_1_version_policy_v1_verify.log`
(append at EOF with verdict block).

**BLOCKING #1** (§2.1 solver_version parser) · Codex 证明
`packaging.version.Version("openfoam/v2312")` raises InvalidVersion。
**Fix**: §2.1 table 标注 solver_version 为 "structured string <family>/<version>
with custom parser (P1-T1 deliverable)"，`case_compatibility` 同样标 structured
range；`extractor_compatibility` 维持 PEP-440 semver。§3 pseudo-code 换成
`family_aware_version_distance` placeholder。`SemverRange` 名字去掉。

**BLOCKING #2** (baseline ≠ live corpus) · Codex 证明 `lid_driven_cavity_benchmark.yaml`
等 structured files 已是 `schema_version: 2`, 10-case "全部继承 baseline"
描述不符。
**Fix**: §1 table 改为 "Knowledge Schema (live, heterogeneous)" 明确 structured 2
+ legacy 1 共存。§2.3 明确 schema_version 不继承 baseline (整数值就是写进 YAML 的那个值)；
四元组字段才走隐式继承。Deadline 从 "2026-06-30" 改为 "P1-T1 closeout"
(buffer 给 lint-knowledge.py 真正上线)。

**BLOCKING #3** (HARD_FAIL no-run 无拦截点) · Codex 证明 `TaskRunner.run_task`
不做 pre-check; `FoamAgentExecutor.execute` 返回时 solver 已 run；
`ExecutionResult` 无 version_metadata 字段；`manifest.py:558` 只 emit
schema_version + run.solver。
**Fix**: §3 顶部加 **DESIGN_ONLY** 标注; §4 顶部加 aspirational 标注,
enforcement deliverable 挂到 P1-T1 (TaskRunner pre-check hook) + P2
(EXECUTOR_ABSTRACTION ExecutionResult extension)。

**GATE_NOT_MET #4** (G-D overstated) · Codex 证明 `validate_gold_standards.py`
只校验 gold YAML shape + corpus，不 backstop 5 条 "不做清单"。
**Fix**: §9.1 新增映射表，5 条 "不做" 各自的 CI 兜底差异化：plane 划分走
ADR-001 importlinter (已 ✅), schema/tolerance 挂 KNOWLEDGE/METRICS Active,
ui/scripts 为 policy-only, 跨 solver 架构层阻止。G-D claim 从 "全部 5 条都由
validate_gold_standards 兜底" 收敛为实际能做到的范围。

**Open comment responses**:
- schema_semver optional vs mandatory (§2.1 / §5.2): 删除 schema_semver,
  留 integer schema_version 作唯一权威 (§2.1 底部, §5.2 不再提及)
- solver_family closed enum (§5.1): 改为 open registry
  (`knowledge/schemas/solver_family_registry.yaml`, P5 activation 前只列
  openfoam_esi baseline)
- version_fingerprint 强制 + quarterly audit (§6): 标 **recommended**
  (enforcement P1-T1 起)

Regression: 569 pass, 4 import contracts KEPT (本修复 doc-only, 无代码触碰).

### §10.2 Codex R2 CHANGES_REQUIRED + Opus Option X 响应 (rc2 → v1.0 · 2026-04-24)

Codex R2 returned CHANGES_REQUIRED with 3 more blocking findings beyond R1
fix. All 3 addressed in this v1.0 commit, plus upstream Opus 4.7 Gate
ruling in Option X (see `docs/specs/SPEC_PROMOTION_GATE.md` §9 v1.1
changelog).

**R2 Blocking #1** (§1 corpus accuracy) — Codex showed legacy files have NO
top-level `schema_version`, 10 structured files with `schema_version: 2`,
not a "structured=2 / legacy=1" split.
**Fix**: §1 table + §2.3 rewritten with accurate: 10 structured + 5 legacy
multi-doc; LegacyObservable / StructuredGoldStandardFile `oneOf` branches
of gold_standard_schema.json explicitly referenced.

**R2 Blocking #2** (§5.2 schema_semver residual contradiction) — v1.0-rc2
claimed removal in §10.1 but §5.2 still required `schema_semver` major bump.
**Fix**: §5.2 entry 2 removed; only integer `schema_version` remains.

**R2 Blocking #3** (G-D v1.0 字面门未满足) — §9.1 argued from "future-spec
dependencies" / "policy-level" / "architectural"; not regression tests or
CI lints per G-D v1.0.
**Fix (Opus Option X)**: SPEC_PROMOTION_GATE v1.0 → v1.1 refinement. G-D
now categorizes "不做" items into Cat 1/2/3 with differentiated evidence
bars. VCP §8 items now explicitly Cat 2 (4 items with scope_delegations
table §9.1 + accepting clauses in consumer specs) + Cat 1 (1 item with
ADR-001 importlinter evidence §9.2) + Cat 3 (1 item with POL-VCP-001 ledger
entry + DEC-POLICY-VCP-001 §9.3). This refinement triggered under RETRO-V61-001
rule #3 (CHANGES_REQUIRED); documented as `DEC-PIVOT-GATE-001` in Notion
Decisions DB.

**R2 Minor comment** (§6.2 labeling) — `quarterly audit` not labeled as
explicitly "planned" as §6.1 `version_fingerprint`.
**Fix**: §6.2 now labeled "(planned · enforcement P1-T1)" same as §6.1.

**Consumer-side co-landed commits** (per SPEC_PROMOTION_GATE §7.2 item 3):
- `docs/specs/KNOWLEDGE_OBJECT_MODEL.md` §1 Object Definitions — accepting
  clause for VCP §8.1
- `docs/specs/METRICS_AND_TRUST_GATES.md` §4 Tolerance Policy — accepting
  clause for VCP §8.2
- `docs/scope/UI_SCRIPTS_BOUNDARY.md` §0 — accepting clause for VCP §8.4
- `docs/governance/POLICY_COMMITMENTS_LEDGER.md` POL-VCP-001 — Cat 3 for VCP §8.5

**Gate v1.1 changes** (`docs/specs/SPEC_PROMOTION_GATE.md`):
- §2 G-D replaced with v1.1 wording (category-dispatched evidence)
- §7 new section: Cat 1/2/3 definitions + evidence requirements
- §8 new appendix: schema examples for scope_delegations + POL entry
- `docs/governance/CODEX_REVIEW_RUBRIC.md` (new stub): Codex challenge
  duty on category classification

Regression: 569 pass, 4 import contracts KEPT (所有 fix doc-only, 无代码触碰).

---

**相关 Governance 文件**：
- `docs/specs/SPEC_PROMOTION_GATE.md` — Draft → Active 通用审查标准
- `docs/governance/PIVOT_CHARTER_2026_04_22.md` §4.3a — Foundation-Freeze 边界
- `docs/adr/ADR-001-four-plane-import-enforcement.md` — 四层 import 强制
- Notion: SYSTEM_ARCHITECTURE v1.0 §5 (版本兼容矩阵引用本文件)
- Notion: METRICS_AND_TRUST_GATES v0.1 §5 (tolerance 字段来自 CaseProfile)

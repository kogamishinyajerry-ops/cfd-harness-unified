---
decision_id: DEC-V61-085
title: Pivot Charter §4.7 codification proposal · Gold-value modification authority (CLASS-1/2/3 line-drawing rule)
status: PROPOSED (awaiting CFDJerry Charter-modification gate; Claude Code drafted text only)
authored_by: Claude Code Opus 4.7 (1M context · Session B v3 Track 2)
authored_at: 2026-04-26
authored_under: Session B v3 · P-2 (Pivot Charter §4.7 codification)
parent_dec: DEC-V61-080
parent_authority_verdict: AUTH-V61-080-2026-04-26
authority_class: CFDJerry_charter_gate  # Charter mods are CFDJerry's own gate per project governance
autonomous_governance: false             # Charter modifications cannot land via autonomous_governance
external_gate_self_estimated_pass_rate: n/a
notion_sync_status: synced 2026-04-26 (https://notion.so/34ec68942bed810cbb1ef22d8c4c1027)
codex_tool_report_path: null
risk_flags: []
gov1_v1_scope:
  case_id: charter_4_7_gold_value_authority
  fix_type: governance_codification_proposal
  fields_modified: []  # no files modified by this DEC; proposal text only
proposed_locations:
  - location: docs/governance/PIVOT_CHARTER_2026_04_22.md (repo-side addendum)
    section: §4.7 (new)
    note: "Repo file currently scoped to §4.3a only; would expand scope to include §4.7 as second repo-anchored section"
  - location: Notion Pivot Charter SSOT (https://www.notion.so/70e55a0c3f924736b0cb68add01d90cd)
    section: §4.7 (new)
    note: "Primary SSOT lands in Notion; repo-side addendum mirrors per existing §0 split rule"
---

# DEC-V61-085 · Pivot Charter §4.7 Codification Proposal

## Why

AUTH-V61-080-2026-04-26 §5 finding 1 stated:

> "Pivot Charter §4 should add explicit 'Gold-value modification
> authority' §4.7 sub-section. V61-058 + this gate jointly establish
> that auto/Codex/Opus line for `knowledge/gold_standards/*.yaml`
> `gold_value` field edits is currently inferred from invariants 1 and
> 4 rather than codified directly. Canonical rule: *'`gold_value` edits
> where new anchor is verified primary literature and value is read out
> of source: CLASS-2; `gold_value` edits where prior provenance is
> fictional or anchor itself is contested: CLASS-3.'* Codification
> would prevent next case-N audit from re-litigating."

Without §4.7, every future gold-value modification triggers fresh
authority adjudication from first principles. AUTH-V61-080 demonstrates
the line CAN be drawn coherently; codifying it removes adjudication
overhead and provides ex-ante guidance.

## Authority

**Pivot Charter modifications are CFDJerry's own gate.** Claude Code
cannot self-author Charter changes. This DEC delivers the proposal text
only; landing requires CFDJerry's signature in the Notion Charter SSOT
(and repo-side addendum mirroring per §0).

The proposed text is grounded in:
- **V61-058 NACA precedent** (CLASS-2: Ladson 1988 / Abbott 1959 /
  Gregory 1970 verified primary literature; values read out of source;
  documented FAIL closure)
- **AUTH-V61-080-2026-04-26 §2 per-case verdicts** (Cases A=CLASS-1,
  B=CLASS-2, C/D=CLASS-3)
- **AUTH-V61-080-2026-04-26 §5 finding 1** (codification recommendation)

## Proposed §4.7 text (CFDJerry to ratify or amend)

```markdown
## §4.7 Gold-value modification authority (codification of AUTH-V61-080)

承接 AUTH-V61-080-2026-04-26 §5 finding 1。`knowledge/gold_standards/*.yaml`
中 `reference_values[].value` / `tolerance` / `source` / `literature_doi`
等"gold-truth"字段的修改权限按以下三档划分。

§4.7 与 §4.3a 关系：§4.3a 管"新增 case / 升级 case_type / 新增 gate"
（HARD NO 类）；§4.7 管"已 frozen case 内的 gold-truth 字段编辑"
（CLASS-1/2/3 分级）。两者互不覆盖。

### (a) CLASS-1 — Claude Code autonomous lane (single commit self-sign)

满足**全部**以下条件：

1. **变更类型**: 仅修复 `literature_doi` typo / `source` 字段 typo /
   `description` 文字 typo / 单条字符级 metadata 修复
2. **identity uncontested**: 单论文、单作者、单年份、单标题、单
   volume/页码识别完全无歧义
3. **NO `gold_value` change** — `reference_values[].value` 不动
4. **NO `tolerance` change**
5. **总改动 ≤2 个文件 ≤20 LOC**

**判例**: DEC-V61-081（CCW Williamson 1996 DOI `.002421` → `.002401`
四字符 typo）。

### (b) CLASS-2 — Claude Code execute + mandatory Codex review

满足**全部**以下条件：

1. **变更类型**: `source` / `literature_doi` 整段 bibliographic-block
   更新 / `reference_correlation_context` 实质重写 / 同一论文 identity
   下的元数据修订
2. **paper identity 保持**: pivot 前后引用的是同一篇论文（journal/
   author/year 至少 2/3 不变）
3. **NO `gold_value` change** OR **`gold_value` 仅按 V61-058 模式修改**:
   (i) 新 anchor 是 verified primary literature, AND
   (ii) values 直接从该 source 读出（不反向工程为了让 case PASS）, AND
   (iii) 任何 verdict 翻转（PASS → FAIL 或反之）显式记录 + 不被掩盖
4. **`/codex-gpt54` review 强制**: PR body 引用本 §4.7(b)；Codex
   APPROVE 后 Status 才能从 ACCEPTED_PENDING_CODEX_REVIEW 推进到
   ACCEPTED

**判例**: V61-058（NACA Ladson 1988 anchor pivot, FAIL 显式记录）;
DEC-V61-082（DCT Jones 1976 journal swap IJHMT → ASME J. Fluids Eng.,
correlation form correction）。

### (c) CLASS-3 — External Opus Gate required (independent-context session)

满足**任一**以下条件：

1. **stored value 的 provenance 是 fictional**: 引用的论文不存在 / 作者
   不可考 / DOI 解析到完全不相关的论文
2. **anchor selection 本身有争议**: 候选 anchor 之间数值差距 >25% 且
   选择带价值判断（哪个更权威 / 哪个 model 配置更接近 adapter）
3. **non-dim convention reconciliation**: stored value vs new anchor
   差异超过 4× 且需要解释（不同 reference length / temperature /
   Re definition）
4. **§4 invariant 1 直接介入**: gold-truth 与 OpenFOAM 真相源关系需要
   重新审视

执行约束：
- Claude Code 可起草 evidence package 写到 `docs/case_documentation/<case>/
  _research_notes/`，但**不得编辑** `knowledge/gold_standards/*.yaml`
  的 `gold_value` / `tolerance` / `source` / `literature_doi`
- DEC 起 DRAFT 版（`.planning/decisions/draft/`），所有 gold-truth
  字段以 `TBD-OPUS-GATE-N+X` marker 占位
- CFDJerry 独立上下文召集 Notion @Opus 4.7 Gate，verdict 落到
  `.planning/audit_evidence/`，DRAFT DEC 升级为正式 DEC 并填值

**判例**: DEC-V61-083 DRAFT（IJ Behnia 1999 re-anchor，stored DOI 解析
到 Rao 2013 LES turbines paper）; DEC-V61-084 DRAFT（RBC "Chaivat et
al. 2006" 不可考）。

### (d) 边界判定决策树

收到 gold-standard 文件修改请求时按顺序问：

1. **改不改 `reference_values[].value` 或 `tolerance`?**
   - 不改 → 看 (2)
   - 改且 prior provenance fictional → **CLASS-3**
   - 改且 prior provenance verified, new anchor verified, value read out
     of source, verdict-flip 显式记录 → **CLASS-2**
   - 改但反向工程让 case PASS → **拒绝**（违反 V61-058 反例约束）

2. **改不改 `source` 或 `literature_doi` 整段?**
   - 不改（仅 typo 级 character-fix）→ **CLASS-1**
   - 整段 bibliographic-block 更新且 paper identity 保持 → **CLASS-2**
   - paper identity 也变 + provenance 出现 fictional / 争议 → **CLASS-3**

3. **改不改 `reference_correlation_context` 或 `physics_precondition`?**
   - 拼写 / 描述细微调整（≤5 LOC, 不改语义）→ **CLASS-1**
   - 实质重写（如 V61-082 把虚构的 0.88 ratio 改写成 Re* 真实方法）→
     **CLASS-2**
   - 改写涉及 invariant-1 关系重新解释 → **CLASS-3**

### (e) 30-day override window

CLASS-3 verdict 由独立 Opus Gate 给出后，CFDJerry 保留 30 天 override
窗口（per AUTH-V61-080 §6 / Pivot Charter §7）。Override 的形式：
Decisions DB 新建 `DEC-V61-OVERRIDE-AUTH-XXX` 显式援引 §4.7(e)。无
override → 默认按 verdict 执行；过期后 verdict 变成不可 override 的
binding precedent。

### (f) 与既有 §4.3a 冻结期的关系

P1 Active 完工前，§4.3a 的 HARD NO 优先于 §4.7 的 CLASS-1/2/3 划分：
任何会触发 (a) 列禁行为的 gold-truth 编辑，**无论 §4.7 把它分到哪一
档，都直接 HARD NO**。§4.7 只在 §4.3a 允许的余地内细化授权。

P1 之后 §4.3a 解锁 → §4.7 成为唯一控制平面。
```

## Implementation note (after CFDJerry ratification)

If CFDJerry approves §4.7 as written or amended:

1. **Notion Pivot Charter** (SSOT): CFDJerry edits Notion page directly
   under §4 family
2. **Repo-side addendum**: Claude Code mirrors the approved text into
   `docs/governance/PIVOT_CHARTER_2026_04_22.md` (file expanded scope
   to also carry §4.7; §0 updated to enumerate covered sections)
3. **Tooling enforcement** (deferred): pre-commit hook may eventually
   parse §4.7 decision tree and gate `knowledge/gold_standards/**`
   commits — out-of-scope for this DEC

## Open questions for CFDJerry

1. Should §4.7 live ONLY in Notion or ALSO in repo addendum? (§0
   currently scopes repo file to §4.3a; §4.7 is engineering-execution
   surface so repo mirroring would aid CI tooling, but §0 split rule
   may need amendment.)
2. Is the 30-day override window in §4.7(e) the right cadence? Should
   it be 14 days (faster decision) or 60 days (more deliberation)?
3. (d) decision tree — should CFDJerry add a fourth question about
   `physics_contract.geometry_assumption` block edits? AUTH-V61-080 did
   not test this surface.
4. (f) §4.3a-precedence rule — confirm correct interpretation: §4.3a
   HARD NO subsumes §4.7 verdicts during freeze period.

## Source

- Authority verdict: `.planning/audit_evidence/2026-04-26_v61_080_v2_authority_gate_verdict.md` §5 finding 1
- V61-058 precedent: `.planning/decisions/2026-04-XX_v61_058_naca_ladson_anchor.md`
- AUTH-V61-080 per-case verdicts: ibid. §2
- 30-day override clause: ibid. §6 + Pivot Charter §7

## Status pathway

```
PROPOSED (this DEC)
   │
   ├─ CFDJerry approves as-is → ACCEPTED → Notion Charter §4.7 lands
   │                          → repo-side mirror per §0 amendment
   │
   ├─ CFDJerry amends → ACCEPTED_WITH_AMENDMENTS → revised §4.7 lands
   │
   └─ CFDJerry rejects → CLOSED-REJECTED + finding remains as a working
                        precedent without codification (next gold-value
                        adjudication still re-litigates from first
                        principles, accepting that overhead)
```

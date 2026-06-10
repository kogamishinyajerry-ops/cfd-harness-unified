# V93 · Agent Crew Observatory — 实现规格（契约 SSOT）

> 2026-06-10 · 总师（Claude）起草。施工 agent 按本文件逐字实现；本文件就是契约——
> API JSON 形状、文件清单、honesty 规则全部以此为准。看不到主对话，一切信息在此。

## 0 · 目标与哲学约束

新增一个**只读观察页** `/agent-crew`：把本项目的多 agent 治理体系（用户 Sponsor →
Claude 总师 → subagent 施工 → Codex 异源审查 cap=3 → loop-auditor 闭环审计 →
Kogami 战略层 opt-in → Git/DEC 档案）可视化，让人直观看到「一个里程碑从委派到
收口走过哪些 agent、产生哪些真实工件」。

硬性哲学约束（违反任意一条 = 返工）：
1. **全真实工件驱动**：所有数据解析自 `.planning/decisions/*.md`（443 个）、
   `reports/codex_tool_reports/*`（154 个）、`.planning/reviews/kogami/*/`。
   **任何字段解析不到 → 显示 `UNPARSED` / `未记录`，绝不编造默认值。**
2. **只读 advisory**：零 mutating 路由（无 POST/PUT/DELETE），前端零写操作。
3. **工作台冻结不碰**：新页面挂在 `<Layout />` 证据面（同 `/workflow-monitor`
   先例 DEC-V61-226），不动 WorkbenchShellV4 及其任何子组件。
4. **启发式解析要自我标注**：verdict / P1-P3 计数是从报告文本正则出来的，UI 上
   必须标注「启发式解析 · 点击看原文」。
5. LLM 离线可跑：后端纯文件解析，请求路径无 LLM、无 subprocess、无网络。

## 1 · 文件清单（两个施工包，文件互不相交）

### 包 A（backend）
- `ui/backend/services/agent_crew.py`（新）
- `ui/backend/routes/agent_crew.py`（新）
- `ui/backend/main.py`（改 2 行：import + `app.include_router(agent_crew.router, prefix="/api", tags=["agent-crew"])`，插在 decisions 行之后）
- `ui/backend/tests/test_agent_crew.py`（新）

### 包 B（frontend）
- `ui/frontend/src/api/agentCrew.ts`（新）
- `ui/frontend/src/pages/agent_crew/AgentCrewPage.tsx`（新）
- `ui/frontend/src/pages/agent_crew/components/TopologyGraph.tsx`（新）
- `ui/frontend/src/pages/agent_crew/components/ArcReplay.tsx`（新）
- `ui/frontend/src/pages/agent_crew/components/ArtifactInspector.tsx`（新）
- `ui/frontend/src/pages/agent_crew/__tests__/AgentCrewPage.test.tsx`（新）
- `ui/frontend/src/App.tsx`（改 2 处：import + 在 `<Route element={<Layout />}>` 块内
  `/workflow-monitor` 路由后面加 `<Route path="/agent-crew" element={<AgentCrewPage />} />`，
  并在文件头注释的 Kept 列表加一行 `/agent-crew`）

## 2 · API 契约（两包必须逐字一致）

### `GET /api/agent-crew` → CrewSnapshot
```json
{
  "roles": [
    {"id": "sponsor",      "label": "用户 · Sponsor",          "model": null,                          "desc": "目标设定与最终裁决（DEC Accept / 操作点裁决 / cap=3 溢出仲裁）", "count_label": null,            "count": null},
    {"id": "chief",        "label": "Claude 总师",             "model": "Opus / Fable · 主驱动",        "desc": "方案/实现/跨文件推理/最终把关；autonomous DEC 的签发者",          "count_label": "autonomous DECs", "count": 0},
    {"id": "workers",      "label": "Subagents · 施工/侦察",    "model": "Sonnet / Haiku / Workflow",    "desc": "只读侦察回 ≤2000tok 摘要；隔离 worktree 施工",                    "count_label": null,            "count": null},
    {"id": "codex",        "label": "Codex 异源审查",           "model": "GPT-5.4 xhigh · 86gs relay",   "desc": "盲点审查 · round cap=3 · verbatim 例外",                          "count_label": "审查报告",        "count": 0},
    {"id": "loop_auditor", "label": "loop-auditor 闭环审计",    "model": "只读 agent",                   "desc": "审验证体系本身：oracle 对齐/fail-closed/防篡改（FLAG/BLOCK）",     "count_label": "标注 DECs",       "count": 0},
    {"id": "kogami",       "label": "Kogami 战略层",            "model": "claude -p 隔离子进程",          "desc": "opt-in 独立战略审（V133 后仅用户显式调用）",                       "count_label": "invocations",    "count": 0},
    {"id": "archive",      "label": "Git · DEC 档案",           "model": null,                          "desc": "可验证真值：决策文件 + 审查报告 + commit 链",                      "count_label": "决策文件",        "count": 0}
  ],
  "edges": [
    {"id": "e1", "from": "sponsor",      "to": "chief",   "label": "目标 / 裁决"},
    {"id": "e2", "from": "chief",        "to": "workers", "label": "自足 prompt 委派"},
    {"id": "e3", "from": "workers",      "to": "chief",   "label": "≤2000 tok 汇报"},
    {"id": "e4", "from": "chief",        "to": "codex",   "label": "commit diff 审查"},
    {"id": "e5", "from": "codex",        "to": "chief",   "label": "verdict（cap=3）"},
    {"id": "e6", "from": "loop_auditor", "to": "chief",   "label": "设计审 FLAG / BLOCK"},
    {"id": "e7", "from": "sponsor",      "to": "kogami",  "label": "opt-in 战略审"},
    {"id": "e8", "from": "chief",        "to": "archive", "label": "DEC + commit + trailer"},
    {"id": "e9", "from": "kogami",       "to": "archive", "label": "review 工件"}
  ],
  "arcs": [],
  "stats": {"decisions_total": 0, "codex_reports_total": 0, "autonomous_total": 0, "loop_auditor_total": 0, "kogami_total": 0}
}
```
- `roles`/`edges` 是**后端写死的静态拓扑**（上面逐字），仅 `count` 字段由解析回填：
  chief.count=autonomous_total · codex.count=codex_reports_total ·
  loop_auditor.count=loop_auditor_total · kogami.count=kogami_total ·
  archive.count=decisions_total。
- `arcs`：CrewArc 数组，按 date 降序，**只含 date ≥ "2026-05-01" 或 frontmatter 带
  `loop_auditor`/`confidence` 字段的 DEC**（早期 DEC schema 异构，全量列表交给已有
  /decisions 页；本页聚焦能讲清协作回路的近期 arc）。上限 80 条。

### CrewArc
```json
{
  "decision_id": "DEC-V61-238",
  "title": "（正文第一个 # 标题，截 160 字符）",
  "date": "2026-06-10",
  "phase": "（frontmatter phase 字段原文 | null）",
  "autonomous": true,
  "confidence": "（frontmatter confidence 原文 | null）",
  "loop_auditor": "（frontmatter loop_auditor 原文 | null）",
  "codex_relay": "（frontmatter codex_review_relay 原文 | null）",
  "codex_rounds": [
    {"round": 0, "verdict": "CHANGES_REQUIRED", "p1": 1, "p2": 2, "p3": 0, "report_path": "reports/codex_tool_reports/xxx.md", "missing": false}
  ],
  "kogami": null,
  "relative_path": ".planning/decisions/2026-06-10_xxx.md"
}
```

### `GET /api/agent-crew/arc/{decision_id}` → ArcDetail
```json
{
  "decision_id": "DEC-V61-238",
  "frontmatter": {"任意原始键值对（yaml.safe_load 结果，值 str() 化）": "..."},
  "body_excerpt": "正文前 120 行原文",
  "reports": [
    {"round": 0, "path": "reports/...", "excerpt": "报告前 100 行原文", "verdict": "APPROVE", "missing": false}
  ]
}
```
- decision_id 找不到 → 404（FastAPI HTTPException）。
- decision_id 必须先匹配 `^DEC-[A-Za-z0-9_\-]+$`，否则 422/404 —— 防路径注入。

## 3 · 后端解析规则（包 A 实现细节）

参考既有先例 `ui/backend/services/decisions.py`（frontmatter 正则 + yaml.safe_load
+ 容错），`REPO_ROOT` 同样从 `ui.backend.services.validation_report` import。

1. **DEC 扫描**：`.planning/decisions/*.md`。date = 文件名前 10 字符（YYYY-MM-DD
  格式校验，不合格跳过 arcs 但计入 decisions_total）。frontmatter 解析失败 → 计入
  total，不入 arcs。
2. **codex_rounds 发现（两路合并去重）**：
   a. frontmatter `codex_tool_report_path`（可能含 brace 形如
      `..._R{0,1}.md` → 自行展开为 `..._R0.md`/`..._R1.md`；也可能是逗号分隔多路径）。
      解析出的路径不存在 → 仍输出该 round，`missing: true`。
   b. glob `reports/codex_tool_reports/*`，文件名（小写化）包含该 DEC 的 id slug
      （`dec-v61-238` → `v61_238` 与 `v61-238` 两种写法都匹配）→ 并入。
   - round 号：文件名正则 `[Rr](?:ound)?[_\s\-]?(\d)`，取第一个命中；没有 → 按文件名
     排序后依次编号。同 round 多文件 → 全保留（数组里两条）。
3. **verdict 提取（启发式 · fail-closed）**：读报告文本，找 token
   `CHANGES_REQUIRED | APPROVE_WITH_COMMENTS | RESOLVED | APPROVE`（按此优先级，
   **取文本中最后一次出现的优先级最高 token**；实现：对每个 token 记录最后出现位置，
   取位置最大者；APPROVE 必须用 `\bAPPROVE\b` 且排除 APPROVE_WITH_COMMENTS 的子串
   命中）。一个 token 都没有 → `"UNPARSED"`。文件 missing → `"MISSING"`。
4. **P1/P2/P3 计数（启发式）**：正则 `\bP([123])\b` 在报告文本中计数（粗，UI 已声明
   启发式）。missing 文件 → 全 0。
5. **kogami**：`.planning/reviews/kogami/*/`，目录含 `invoke_meta.json` 算一次
   invocation（kogami_total）。CrewArc.kogami 仅当 DEC frontmatter 或正文出现
   `kogami` 字样且能在某个 kogami 目录名中模糊匹配 DEC slug 时填
   `{"topic": 目录名, "verdict": review.json 里 verdict 键 | "UNPARSED"}`，否则 null
  （宁缺毋滥）。
6. **stats**：decisions_total=全部 md 数；codex_reports_total=reports/codex_tool_reports
   下文件数（所有后缀）；autonomous_total=frontmatter `autonomous_governance` 为 true
   的数量；loop_auditor_total=frontmatter 含 `loop_auditor` 键的数量；kogami_total 如上。
7. 全部 dataclass + `slots=True`，路由层用 FastAPI 自动序列化（参考
   `ui/backend/routes/decisions.py` 怎么返回 dataclass——**先读它再写**）。
8. **测试** `ui/backend/tests/test_agent_crew.py`（先读
   `ui/backend/tests/test_decisions_and_dashboard.py` 抄它的 fixture/monkeypatch 风格）：
   - 真仓库 smoke：snapshot 返回 200，stats.decisions_total ≥ 400，arcs 按 date 降序，
     每个 arc 的 decision_id 匹配 `^DEC-`。
   - 合成 fixture（tmp_path + monkeypatch 模块常量）：一个含
     `codex_tool_report_path: reports/codex_tool_reports/t_R{0,1}.md` 的 DEC + 两个报告
     文件（R0 文本含 "CHANGES_REQUIRED"，R1 含 "APPROVE"）→ 断言 rounds=[{0,CHANGES_REQUIRED},{1,APPROVE}]。
   - verdict fail-closed：报告无 token → UNPARSED；路径不存在 → missing=true + MISSING。
   - APPROVE_WITH_COMMENTS 文本不得被解析成 APPROVE。
   - arc detail 404（不存在 id）+ 非法 id（`../etc`）不泄露文件。

## 4 · 前端规则（包 B 实现细节）

**先读这些文件再动笔**（风格对齐，不是建议是要求）：
- `ui/frontend/src/api/client.ts`（fetch 封装——新 api 文件必须复用同一封装）
- `ui/frontend/src/pages/workflow_monitor/WorkflowMonitorPage.tsx`（三栏布局 + 面板风格先例）
- `ui/frontend/tailwind.config.ts` 的 `v4:` 调色键（healthy/active/brand 等）
- `ui/frontend/src/pages/DecisionsQueuePage.tsx`（react-query 用法先例）

布局（单屏三栏，Layout chrome 内）：
- **页头条**：标题「Agent Crew Observatory · 多 agent 治理回路」+ honesty 声明一行
  （§0 第 1/4 条原话压缩版）+ stats chips（决策 N · Codex 报告 N · autonomous N ·
  loop-auditor N · Kogami N——全部来自 /api/agent-crew stats，无硬编码数字）。
- **左栏 TopologyGraph（约 340px）**：纯 SVG（无第三方图库）。节点固定布局：
  sponsor 顶部居中 → chief 正中 → workers 左下 → codex 右中 → loop_auditor 右上 →
  kogami 顶右（虚线边框=opt-in）→ archive 底部居中。节点卡片显示 label/model/count
  （count_label 非 null 时）。边按 §2 edges 画带箭头曲线 + label。props:
  `{roles, edges, activeEdgeIds: string[], onSelectRole?: (id)=>void}`；
  `activeEdgeIds` 命中的边用 v4 active 色 + CSS animation 脉冲（stroke-dashoffset）。
- **中栏**：上=Arc 选择列表（date 降序，行内显示 decision_id/date/标题截断/round 徽章
  序列：每 round 一个色点——APPROVE=healthy 绿、APPROVE_WITH_COMMENTS=黄绿、
  CHANGES_REQUIRED=active 琥珀、UNPARSED/MISSING=灰，hover 显示 verdict 原文）；
  下=ArcReplay：选中 arc 后把协作回路展开成有序步骤条：
  `[loop-auditor 设计审]?(有 loop_auditor 字段才显示) → [总师实现] → [Codex R0 verdict] →
  ([总师修复] → [Codex R1])* → [收口/Accepted]`。
  「▶ 回放」按钮以 1.2s/步 步进，步进到哪一步就通过回调把对应 activeEdgeIds 传给
  TopologyGraph（设计审→["e6"]；实现→["e1","e2","e3"]；Codex 轮→["e4","e5"]；
  收口→["e8"]）。可暂停/重置。步骤 chip 点击 → 右栏 inspector 聚焦对应工件。
  **步骤序列只从 arc 真实字段推导**：没有 loop_auditor 就没有设计审步；rounds 几轮
  就几步；不虚构中间步骤。
- **右栏 ArtifactInspector（约 360px）**：选中 arc 后 react-query 拉
  `/api/agent-crew/arc/{id}`：frontmatter 键值表（等宽字体）+ 各 round 报告 excerpt
  （滚动 pre 块，顶部标注「启发式解析 verdict: X · 原文如下」）。missing 报告显示
  「报告文件缺失（frontmatter 引用了但文件不在仓库）」。未选中 → 空态提示。
- **配色**：只用 tailwind v4 键 + 既有灰阶；不引新依赖、不引图表库。
- **测试** `__tests__/AgentCrewPage.test.tsx`（先读 workflow_monitor 的
  `__tests__/` 怎么 mock——msw 或 vi.spyOn fetch，跟着先例走）：
  - 渲染后 7 个角色节点 label 可见；stats chips 显示 mock 数字。
  - mock 一个含 2 rounds 的 arc → 点击列表行 → 回放条出现 R0/R1 步骤、verdict 徽章
    颜色类正确、UNPARSED 显示灰徽章。
  - 断言页面不存在任何可触发 POST 的按钮（只读）。

## 5 · 验证命令（施工完必须全绿才算完）

```bash
# 包 A
~/Desktop/cfd-audit-merge/.venv/bin/python -m pytest -q ui/backend/tests/test_agent_crew.py
# 包 B（在 ui/frontend/）
npx tsc -b
npx vitest run src/pages/agent_crew
```

## 6 · 不许做

- 不动 `ui/frontend/src/pages/workbench/**` 任何文件（冻结）。
- 不加新 npm/pip 依赖。
- 不写 POST/PUT/DELETE 路由。
- 不在请求路径里跑 git/subprocess。
- 不硬编码任何统计数字到前端。
- App.tsx / main.py 之外不改任何既有文件。

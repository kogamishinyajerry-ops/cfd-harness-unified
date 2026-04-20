# cfd-harness-unified

统一 AI-CFD 知识编译器：**Foam-Agent** 执行引擎 + **Notion** 控制面 + **Path B UI MVP** 工作台。

## 快速开始（核心 CLI / 测试）

```bash
pip install -e ".[dev]"
pytest
```

## UI MVP 快速开始（Path B · Phase 0..4）

Path B 是面向受监管行业（FDA V&V40 / DO-178C / NQA-1 / ASME V&V40）的 Agentic
V&V-first 工作台。MVP 已落地 Phase 0 至 Phase 4：Validation Report、Case
Editor、Decisions Queue、Run Monitor、Dashboard。Phase 5（Audit Package
Builder）暂缓，等待 Q-1 / Q-2 外部 Gate 决议。

```bash
# 一次性安装
pip install -e ".[ui,dev]"
(cd ui/frontend && npm install)

# 一键启动（FastAPI :8000 + Vite :5173）
./scripts/start-ui-dev.sh

# 浏览器访问
#   UI:      http://127.0.0.1:5173
#   API Doc: http://127.0.0.1:8000/api/docs
```

UI 目录概览：

- `ui/backend/` — FastAPI + Pydantic v2，只读挂载知识库，禁写 `knowledge/whitelist.yaml` 与 `knowledge/gold_standards/**`
- `ui/backend/user_drafts/` — Case Editor 写入的用户草稿区（Phase 1 禁区隔离）
- `ui/frontend/` — Vite 5 + React 18 + TypeScript + Tailwind 3 + CodeMirror 6

相关决策：见 `.planning/decisions/2026-04-20_path_b_ui_mvp.md`（DEC-V61-002）
及 `.planning/decisions/2026-04-20_phase_1_to_4_mvp.md`（DEC-V61-003）。

## 架构

```
Notion TaskSpec → task_runner → CFDExecutor → result_comparator → correction_recorder → Notion
```

- **MockExecutor**：测试专用，返回预设结果
- **FoamAgentExecutor**：占位符，对接真实 Foam-Agent
- **knowledge_db**：本地 YAML 知识库（Gold Standard + CorrectionSpec）
- **UI MVP**：`ui/backend` + `ui/frontend`，Validation Report → Case Editor → Decisions Queue → Run Monitor → Dashboard

## 配置

复制并填写 `config/notion_config.yaml` 和 `config/foam_agent_config.yaml`。

## 测试

```bash
# 核心
pytest --cov=src --cov-report=term-missing

# UI backend
pytest ui/backend/tests -q

# UI frontend
(cd ui/frontend && npm run typecheck && npm run build)
```

# cfd-harness-unified

统一 AI-CFD 知识编译器：**Foam-Agent** 执行引擎 + **Notion** 控制面。

## 快速开始

```bash
pip install -e ".[dev]"
pytest
```

## 架构

```
Notion TaskSpec → task_runner → CFDExecutor → result_comparator → correction_recorder → Notion
```

- **MockExecutor**：测试专用，返回预设结果
- **FoamAgentExecutor**：占位符，对接真实 Foam-Agent
- **knowledge_db**：本地 YAML 知识库（Gold Standard + CorrectionSpec）

## 配置

复制并填写 `config/notion_config.yaml` 和 `config/foam_agent_config.yaml`。

## 测试

```bash
pytest --cov=src --cov-report=term-missing
```

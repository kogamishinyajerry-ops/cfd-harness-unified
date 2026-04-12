# cfd-harness-unified

## 项目意图

统一知识治理层 + Foam-Agent 执行引擎，建立个人 CFD 知识图谱。

本项目是 AI-CFD Knowledge Harness 的下一代架构：
- **Foam-Agent** 作为外部 CFD 执行引擎（不自建 NL→OpenFOAM 生成能力）
- **Notion** 作为唯一的 Process SSOT 控制面
- **本地 YAML** 作为 Gold Standard 和 CorrectionSpec 知识库

## 核心约束

- Python 3.9+
- 所有类型定义用 dataclass（不用普通 dict）
- 所有枚举字段用 Enum（不用字符串常量）
- 接口定义用 Protocol（不用 ABC）
- 测试用 pytest，覆盖率 > 80%
- 不安装或调用真实 Foam-Agent，只实现 adapter 接口和 MockExecutor
- 不调用真实 Notion API，notion_client.py 留占位符，测试用 mock

## 不做的事

- 不自建 NL→OpenFOAM 生成能力（Foam-Agent 已覆盖）
- 不自建求解器
- 不管理 OpenFOAM 安装

## 唯一控制面

Notion 页面：cfd-harness-unified
- Phases 数据库 → Tasks 数据库 → Sessions 数据库
- Decisions 数据库 ← → Phases / Sessions
- Canonical Docs 数据库 ← → Phases / Tasks

## 架构流程

```
Notion TaskSpec
    ↓
task_runner.py（编排器）
    ├── knowledge_db.py（加载 Gold Standard + CorrectionSpec）
    ├── foam_agent_adapter.py（调用 CFDExecutor Protocol）
    │       ├── MockExecutor（测试用）
    │       └── FoamAgentExecutor（占位符）
    ├── result_comparator.py（结果 vs Gold Standard）
    └── correction_recorder.py（偏差 → CorrectionSpec）
    ↓
回写结果摘要到 Notion
```

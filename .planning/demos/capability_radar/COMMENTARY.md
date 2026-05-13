# Capability Radar · Justification

**Generated**: 2026-05-13 by Claude Code Opus 4.7 session
**Honest self-assessment**, not marketing. Each cell has a reason.
Scores will move as project matures or as commercial CAE evolves.

| 维度 | cfd-harness | STAR-CCM+ | Fluent | OpenFOAM vanilla |
|---|---|---|---|---|
| CAD/几何 ingest | 6 | 9 | 8 | 3 |
| 网格生成 | 6 | 9 | 8 | 5 |
| 物理模型覆盖 | 7 | 10 | 10 | 9 |
| 求解器健壮性 | 6 | 9 | 9 | 6 |
| 后处理质量 | 7 | 9 | 8 | 5 |
| CLI/自动化 | 9 | 5 | 4 | 9 |
| AI 智能辅助 | 8 | 2 | 1 | 0 |
| 可重现/审计 | 9 | 6 | 5 | 7 |

---

## 评分依据

### 1. CAD/几何 ingest — cfd-harness: 6

- **已有**：A1 (canonicalizer) · A7 (`step_canonicalizer.py`) 处理 STEP `FILE_NAME` 时间戳字节确定性 · 14 个工业 case 走通 STEP/STL pipeline · V20 unit detection · 中文 PRODUCT mojibake 处理 (cad-step-stl-prep skill)
- **缺**：CATIA / NX / Creo 原生格式必须经 STEP 中转 · 复杂 BREP 修复仍 fragile (V1/V2) · 自动 cleanup 规则少
- **STAR-CCM+ 9**：工业 native CAD plugin，直接读 CATIA Part / NX / Creo；wrap / repair / decimate 强
- **Fluent 8**：Workbench 集成强，但 SpaceClaim 是独立工具链
- **OpenFOAM vanilla 3**：没有 native CAD tool，全靠 third-party

### 2. 网格生成 — cfd-harness: 6

- **已有**：sHM wrapped + cfMesh wrapped · 943k cells production 验证 · A2-v2 gap detection (DEC-V61-198-sub-A2v2) · A8 `shm_dict_validator.py` candidate · refinementBox + 3-layer prism 模板
- **缺**：mesh debug 仍 manual loop（V73-V78 七轮） · 无 polyhedral mesh（OpenFOAM 限制）· 自适应 mesh refinement 弱
- **STAR-CCM+ 9**：polyhedral + prism + wrapped meshing 工业 gold standard · 自动 mesh adaptation
- **Fluent 8**：Fluent Meshing 现代化但相对新
- **OpenFOAM vanilla 5**：sHM 是 OK 但不如商业 wrapped meshing；用户自己调

### 3. 物理模型覆盖 — cfd-harness: 7

- **已有**：跨 10 个 numerics class（compressible-buoyant-RANS · CHT · incompressible-RANS · MRF · compressible-shock-density · multiphase-VOF · incompressible-RANS-Lagrangian · reacting-low-Mach · incompressible-LES · compressible-DES-acoustic + chtMR LES）· OpenFOAM 全部 solver 可用
- **缺**：每类只 1-2 case，覆盖度浅 · 辐射模型未集成 · DEM/DPM 实操经验少
- **STAR-CCM+ 10**：几乎所有物理（DEM/DPM/EHD/n-phase/chemistry/FW-H/acoustics/...）
- **Fluent 10**：类似 STAR-CCM+，反应流强项
- **OpenFOAM vanilla 9**：solver 库很大，但 user 需自己选/调

### 4. 求解器健壮性 — cfd-harness: 6

- **已有**：V-series 沉淀 13+ 类死法对策（S1-S24 playbook） · case_002a 2689 SIMPLE iters 跑通 · V84 production-tuned schemes 验证
- **缺**：本质上是 OpenFOAM solver，固有 robustness 有限 · buoyantSimpleFoam 5 次发散记录 (V5/V6/V7) · 商业级 convergence acceleration 无
- **STAR-CCM+ 9**：商业级 robust，自动 under-relaxation 调整
- **Fluent 9**：类似
- **OpenFOAM vanilla 6**：robustness 参差，user 需懂

### 5. 后处理质量 — cfd-harness: 7

- **已有**：ParaView HD 报告（4-tier 22MB HTML embedded）· 8 张 3200×2000 PNG 模板 · 多种 v6N 渲染脚本（`v6N_paraview_HD_*.py`）· trame WebGL 实时查看路径
- **缺**：不是 GUI-driven，调参慢 · 工程报告自动生成弱
- **STAR-CCM+ 9**：built-in scenes / plots / reports，工业向但不 web-shareable
- **Fluent 8**：CFD-Post 良好
- **OpenFOAM vanilla 5**：ParaView 外部，user 需懂

### 6. CLI/自动化 — cfd-harness: 9

- **已有**：Claude Code session 端到端驱动（case_002a F4b 10.4h 全程无 GUI）· 完整 Python/Bash pipeline · 30 patches frozen 在 naming.yaml SSOT · `dogfood_loop.py` smoke · uv venv reproducible
- **缺**：跟 OpenFOAM vanilla 并列 9，但更结构化
- **STAR-CCM+ 5**：Java/Python macro 可脚本化，但 GUI-first，CLI 是 second-class
- **Fluent 4**：TUI script + Python，GUI-first
- **OpenFOAM vanilla 9**：100% CLI，但缺标准化

### 7. AI 智能辅助 — cfd-harness: 8

- **已有**：corpus_loader.py 离线运行 · V-series 84 行 + S-series 24 行项目自有 corpus · advisor stack A1/A2-v2/A3/A7 landed · `/ai-review` `/ai-diagnose` route · 4 问门控（LLM 离线/artifacts/TrustGate/advisory-only）· DEC-V61-199 Anthropic agent canon adoption
- **缺**：仍依赖 Claude Code session 作 advisor（M6 charter 实证化）· A4-A8 部分还 drafted
- **STAR-CCM+ 2**：Design Manager / template assistant 算 mild assist，不算真 AI
- **Fluent 1**：几乎没有 AI advisor
- **OpenFOAM vanilla 0**：完全无

### 8. 可重现/审计 — cfd-harness: 9

- **已有**：V-series + DEC 链 + Codex relay reports + corpus sync + 四问门控 + naming.yaml SSOT + Surface-scan trailer + 100% git tracked + frontmatter `notion_sync_status` · DEC-V61-088 pre-implementation surface scan
- **缺**：暂无自动 drift-prevention hook（刚提议但未 land）
- **STAR-CCM+ 6**：sim 文件保存可复现，但跨 case 知识沉淀靠 user 手动 doc
- **Fluent 5**：case 文件 reproducible，跨 case sediment 无 first-class
- **OpenFOAM vanilla 7**：case 文件 git-trackable，但缺标准化 workflow / sediment 系统

---

## 形状解读

- **cfd-harness 的优势在右半轴**：CLI/AI/审计 — 这是商业 CAE 系统性弱点
- **商业 CAE 优势在左半轴**：CAD/网格/物理/求解器/后处理 — 几十年工程团队 + 客户反馈累积
- **形状互补 not 重合**：项目不是要替代 STAR-CCM+，而是给 OpenFOAM 用户提供商业级 workflow 但保留 OSS 透明性 + 加上 AI 顾问 + 跨 case 知识 sediment

---

## 评分会怎么变

- **左半 5/6/7 → 8** = 需要 12-24 个月 / 多个新工业 case sediment / advisor stack 全 land
- **右半 9 → 10** = 几乎不可能（没有 10 分项目，10 留给"还未出现的能力"）
- **STAR-CCM+ AI 2 → 5+** = 大概率 24 个月内发生（Siemens Industrial Copilot 在做）→ 项目的 AI 优势窗口在收窄

---

## 维度选择说明

8 维度是 CFD workflow 经验筛选。**未画但显著的维度**：

- **HPC 扩展性** — 商业 9 / 项目 4（ARM 4-core only，无 cluster experience）· 故意不画因为不是核心差异化轴
- **学习曲线** — 商业 GUI 6 / OpenFOAM 3 / cfd-harness 5 · 故意不画因为 audience-dependent
- **多场耦合（FSI/multi-physics chain）** — 商业 9 / 项目 3 · 故意不画因为单值低分容易误导

如果用户认为这 3 个轴更重要可以补画第二张图。

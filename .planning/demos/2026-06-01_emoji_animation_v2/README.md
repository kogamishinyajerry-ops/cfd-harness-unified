# cfd-harness-unified 科普动画 Demo v3 · README

> **★ 推荐使用 v3 版**：单文件 HTML · 7 步· 逐步引导式 · 教学级别
> v2 (9 幕多角色工作台) 见 `scenes/ALL.html` (保留但不再推荐)

---

## 🎬 v3 成片 (final deliverable)

| 项 | 值 |
|---|---|
| **路径** | `scenes/ALL_v3.html` (单文件) |
| **大小** | 21 KB |
| **时长** | 41 s · 7 步连续 |
| **分辨率** | 1920 × 1080 |
| **依赖** | 仅一个 HTML 文件 + assets/ 目录的图 |
| **打开** | 浏览器直接 `file://` 或 `http://localhost:8766/scenes/ALL_v3.html` |
| **设计理念** | **逐步引导式** · 每步只有 1 主角 + 1 问题 + 1 工具 + 1 产物 |

> **v3 vs v2 差异**：v2 是对 9 个独立场景切换（工作台风格，信息多）→ v3 是**同一画面上逐步推演**，每步只看 1 个焦点，像老师一步步教学生。

---

## 🧭 v3 7 步节奏 (逐步引导式)

| # | 标题 | 时长 | 💭 问题 | 🛠️ 工具 | ✅ 产物 |
|---|---|---|---|---|---|
| **S0** | 开篇 | 6 s | solver 第 6 天发散 | 终端 NaN log | 共情钩子 |
| **S1** | ① 几何 | 7 s | STEP 标签全丢 | `Import.insert` (V1 fix) | `naming.yaml` 30 patches ✓ |
| **S2** | ② 网格 | 7 s | max_skew 6.87 能跑吗？ | V84 smoke test lesson | 50-iter → p_rgh 1.8e-5 ✓ |
| **S3** | ③ 求解 | 7 s | 10.4h 能跑完？ | residuals.png 真实曲线 | 0 FATAL ✓ |
| **S4** | ④ 审计 | 7 s | \|U\| 对但 T 偏低 30% | editor V85.md | V85 沉淀(字符打字) ✓ |
| **S5** | 收尾 | 5 s | 工作台永远能跑 | 4-pillar 4 卡片 | ✅ ✅ ✅ ✅ |
| **S6** | End card | 4 s | — | — | 项目名 + 数据行 |

合计 **41 s** · 每步单一焦点 · 只展示 1 主角 + 1 问题 + 1 工具 + 1 产物

---

## 📁 目录结构

```
2026-06-01_emoji_animation_v2/
├── README.md                            ← 本文件
├── 99_PLAN.md                           ← 总规划执行摘要
├── 00-05 规划文档                       6 份 (concept / design / storyboard / assets / pipeline / dialogue)
├── 06_prototype/                        早期 E6 prototype
│   ├── prototype.html
│   └── README.md
├── assets/                              真实素材
│   ├── chamber_iso.png                  E5 3D 几何 1280×720
│   ├── mesh_envelope.png                E6 网格 1280×720
│   ├── residuals.png                    E7 残差 1920×500
│   ├── p_rgh_panel.png                  E7 局部
│   ├── run10_trajectory.png             备用
│   └── thumbs/                          E8 8 HD 缩略 240×150
├── scenes/                              ★ 9 幕自包含 HTML + ALL.html
│   ├── ALL.html                         ★★ 合并版 (单文件, 79KB)
│   ├── E0.html  E1.html  ...  E9.html  (各幕独立)
│   └── E10.html
└── build/                               制作脚本
    ├── _base_style.css                  共享 CSS (~400 行)
    ├── build_scene.py                   生成 9 幕独立 HTML
    ├── build_all.py                     ★★ 生成 ALL.html (单文件合并版)
    └── preprocess_assets.py             资产预处理 PIL
```

---

## 🎨 视觉特征

### 角色
- 🧑‍💻 工程师 (贯穿 9 幕)
- 👷 工程师工业态 (E0 痛点 + E5 几何)
- 🤖📋 Advisor (E4 出现后贯穿)
- 📚 知识库 (E4 / E6 / E8)
- 🖥️ Solver (E7)
- 🎨 CAD (E5) · 🕸️ Mesh (E6) · 📈 Plot (E7) · 📦 Audit (E8)

### 注释
- 🟡 黄圈聚光 (脉冲 0.8 Hz)
- 🔴 红箭头 + 红叉 (痛点)
- 🟢 绿框 + 角标 (收敛 / 通过)
- ① ② ③ ④ 数字徽章 (warm orange, mono)
- ✨ 闪烁高亮 (1.2 Hz 文字下黄底)
- 💭 思考气泡 (黄) / 💬 说话气泡 (白)
- 📌 4-pillar 角注 (左下)
- 🏷️ footer (右下, E-tag 随幕切换)

### 镜头 (CSS 实现)
- 推近 / 拉远 (transition 0.4s)
- 摇移 (transform translateX)
- 焦平面拉 (filter blur, 全局 .scene opacity)
- 高光扫 (.light-sweep animation)
- 字符打字 (JS)
- 数字滚动 (JS requestAnimationFrame)

---

## 📊 真实内容引用 (peer 可验证)

- **5 个 V-row 真实文本**：V1 (`:56-67`) / V3 (`:81-92`) / V8 / **V84 (完整 lesson, 1.6KB)** + 新 V85 (字符打字)
- **6+ 张真实工程截图**：V8_sceneE_envelope (E6 网格) / CHT_role_iso (E5 几何) / residuals (E7 曲线) / 8 HD ParaView thumbs (E8 4×2 grid) / p_rgh_panel / run10_trajectory
- **3 个真实配置**：`naming.yaml` (30 patches 节选) / `02_domain_subtract.py:102` (Import.insert) / `industrial_solver_findings_v_series.md` (V84 完整 lesson)
- **2 个真实 log**：`sHM_v2_tight.log` (6.875 / 943,289 cells) / `pimple_v2_plateau.log` (p_rgh 1.8e-5 @ t=0.213)
- **1 段真实工程 README**：`reports/v6N/ENGINEERING_CAVEAT.md` (30% 偏低 3 根因)
- **1 段真实 narrative**：V85 (新沉淀的 30% 数值耗散)

---

## 🔄 怎么重新生成

```bash
cd /Users/Zhuanz/Desktop/cfd-harness-unified/.planning/demos/2026-06-01_emoji_animation_v2

# 1. (可选) 重新预处理资产
python3 build/preprocess_assets.py

# 2. 重新生成 9 幕独立 HTML
python3 build/build_scene.py all

# 3. 重新生成单文件 ALL.html ★
python3 build/build_all.py

# 4. 启动本地 server + 打开
python3 -m http.server 8766 --bind 127.0.0.1 &
open http://127.0.0.1:8766/scenes/ALL.html
```

---

## 🐛 已知 minor 问题

1. **E6 来自 prototype.html**，build_all.py 用 BeautifulSoup 提取 DOM (修过 div 不平衡 bug)。
2. **E6 数字 stats** (cells/runtime) 不会自动跑 (因为 E6 timeline 没用 clock-fast/clock-end 事件)，仅显示初始 0。
3. **ALL.html 跳幕菜单** (右上「▼ 跳幕」按钮) 可点击跳转任意幕。
4. **Replay 按钮** 重启整片循环。

---

## 📜 许可 & 信用

- 真实工程数据来自 `~/Desktop/cfd-harness-unified/_industrial_substrates/apu-bay-ventilation-cht` (v6N B+ 算例)
- V-series corpus 来自 `docs/openfoam_corpus/industrial_solver_findings_v_series.md` (84 V-rows)
- 4-pillar 治理见 `~/Desktop/cfd-harness-unified/CLAUDE.md` v2.3 · DEC-V61-133
- 制作：Claude Code Opus 4.7 session · 2026-06-01

---

**全程 0 MP4 · 0 ffmpeg · 0 录屏** — 纯 HTML+CSS+JS 动画，浏览器打开即看。
